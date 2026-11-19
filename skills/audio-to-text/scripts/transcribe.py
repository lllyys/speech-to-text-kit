#!/usr/bin/env python3
"""Transcribe audio/video files locally with mlx-whisper (Apple Silicon). Nothing leaves the machine.

Run through uv so mlx-whisper does not need to be installed globally:
    uv run --quiet --with mlx-whisper python transcribe.py INPUT [INPUT ...] [options]

INPUT can be files or folders (folders are searched for audio/video, not recursively unless -r).
For each input X.m4a it writes X.txt next to it (or into --out-dir), one line per segment:
    [mm:ss] text          ([h:mm:ss] past one hour)
With --srt it also writes X.srt subtitles. Files whose transcript already exists are skipped
unless --force. The first run downloads the model (~1.6 GB for large-v3-turbo).
"""
import argparse, os, re, shutil, sys, time
from collections import Counter

MEDIA = (".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus", ".mp4", ".mov", ".webm", ".mkv")

# A short prompt in the target script steers Whisper toward simplified characters and punctuation;
# without it Mandarin often comes out in traditional characters with no punctuation.
DEFAULT_PROMPTS = {
    "zh": "以下是普通话的演讲，使用简体中文，带标点符号。",
}

# Characters that only appear in traditional Chinese; a high share means the prompt didn't take.
TRAD = set("們這個來說會為與對時從後們還經過問開關頭點車東門長見話認讓書買聽學實發現電氣愛當變間應")

def ts(s, srt=False):
    h, m, sec = int(s // 3600), int(s % 3600 // 60), s % 60
    if srt:
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int(sec % 1 * 1000):03d}"
    return f"{h}:{m:02d}:{int(sec):02d}" if h else f"{m:02d}:{int(sec):02d}"

def find_inputs(paths, recursive):
    out = []
    for p in paths:
        if os.path.isdir(p):
            walker = os.walk(p) if recursive else [(p, [], os.listdir(p))]
            for root, _, names in walker:
                out += [os.path.join(root, n) for n in sorted(names)
                        if n.lower().endswith(MEDIA) and not n.startswith(".")]
        elif os.path.isfile(p):
            out.append(p)
        else:
            print(f"! not found: {p}", file=sys.stderr)
    return out

def quality(segments):
    """Cheap warnings a human should hear about: Whisper loops and wrong script."""
    texts = [s["text"].strip() for s in segments if s["text"].strip()]
    warn = []
    if texts:
        top, n = Counter(texts).most_common(1)[0]
        if n >= 8 and len(top) > 6:   # long line repeated many times = hallucination loop
            warn.append(f"line repeated {n}x (possible Whisper loop): {top[:30]}")
        joined = "".join(texts)
        han = len(re.findall(r"[一-鿿]", joined))
        if han > 200 and sum(c in TRAD for c in joined) / han > 0.02:
            warn.append("looks like traditional Chinese; rerun with --lang zh")
    return warn

# ---------- model download ----------
# Approximate download sizes, shown before a first download so nobody is surprised.
MODEL_SIZES = {
    "mlx-community/whisper-large-v3-turbo": 1.6,
    "mlx-community/whisper-large-v3-mlx": 3.1,
    "mlx-community/whisper-medium-mlx": 1.5,
    "mlx-community/whisper-small-mlx": 0.5,
}
MIRROR = "https://hf-mirror.com"

def hf_cache():
    return os.environ.get("HF_HUB_CACHE") or os.path.join(
        os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface")), "hub")

def complete(path):
    """A usable snapshot has weights. An interrupted download can leave a folder that
    exists but holds no weights; treat that as missing, not as installed."""
    try:
        return any(n.endswith((".safetensors", ".npz")) and os.path.getsize(os.path.join(path, n)) > 1_000_000
                   for n in os.listdir(path))
    except OSError:
        return False

def ensure_model(repo, quiet=False):
    """Return a local path to the model, downloading it once if needed.
    Doing this up front (instead of letting transcribe() fetch it mid-run) means a slow or
    failed download is reported as what it is, and batches never stall on file 1."""
    if os.path.isdir(repo):          # already a local folder
        return repo
    from huggingface_hub import snapshot_download
    try:
        path = snapshot_download(repo, local_files_only=True)
        if complete(path):
            if not quiet: print(f"model: {repo} (cached)")
            return path
    except Exception:
        pass
    size = MODEL_SIZES.get(repo)
    need = (size or 3.5) * 1.3
    free = shutil.disk_usage(os.path.dirname(hf_cache()) if not os.path.isdir(hf_cache()) else hf_cache()).free / 1e9
    if free < need:
        sys.exit(f"Not enough disk space for {repo}: needs ~{need:.1f} GB, {free:.1f} GB free.")
    print(f"model: {repo} is not on this machine yet. Downloading it once "
          f"({'~%.1f GB' % size if size else 'size unknown'}) into {hf_cache()} from "
          f"{os.environ.get('HF_ENDPOINT', 'https://huggingface.co')}. Later runs reuse it.", flush=True)
    t = time.time()
    try:
        path = snapshot_download(repo)   # resumes a partial download if one exists
    except Exception as e:
        hint = ("" if os.environ.get("HF_ENDPOINT") else
                f"\nIf huggingface.co is slow or blocked from here, retry with --mirror (uses {MIRROR}).")
        sys.exit(f"Model download failed: {type(e).__name__}: {str(e)[:200]}"
                 f"\nRe-running resumes where it stopped.{hint}")
    if not complete(path):
        sys.exit(f"Model download finished but no weights found in {path}; re-run to resume.")
    print(f"model: downloaded in {time.time() - t:.0f}s", flush=True)
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--out-dir", default=None, help="write transcripts here instead of next to each file")
    ap.add_argument("--out", default=None, help="exact output path (single input only)")
    ap.add_argument("--lang", default=None, help="language code, e.g. zh, en (default: auto-detect)")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    ap.add_argument("--prompt", default=None, help="initial prompt: vocabulary, names, script; defaults per language")
    ap.add_argument("--srt", action="store_true", help="also write .srt subtitles")
    ap.add_argument("-r", "--recursive", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-transcribe even if the .txt exists")
    ap.add_argument("--model-status", action="store_true", help="say whether the model is downloaded, then exit")
    ap.add_argument("--download-model", action="store_true", help="download the model now (no transcription), then exit")
    ap.add_argument("--mirror", nargs="?", const=MIRROR, default=None,
                    help=f"download through a Hugging Face mirror (default {MIRROR}) when huggingface.co is slow/blocked")
    a = ap.parse_args()

    if a.mirror:   # must be set before huggingface_hub is imported
        os.environ["HF_ENDPOINT"] = a.mirror

    if a.model_status:
        from huggingface_hub import snapshot_download
        try:
            p = snapshot_download(a.model, local_files_only=True)
            ok = complete(p)
        except Exception:
            ok = False
        size = MODEL_SIZES.get(a.model)
        print(f"{a.model}: " + ("downloaded" if ok else
              f"NOT downloaded ({'~%.1f GB' % size if size else 'size unknown'} on first use)"))
        sys.exit(0 if ok else 2)
    if a.download_model:
        ensure_model(a.model)
        sys.exit(0)
    if not a.inputs:
        ap.error("give at least one audio/video file or folder")

    files = find_inputs(a.inputs, a.recursive)
    if a.out and len(files) != 1:
        sys.exit("--out needs exactly one input")
    if not files:
        sys.exit("no audio/video files found")

    def out_path(src):
        stem = os.path.splitext(os.path.basename(src))[0]
        return a.out or os.path.join(a.out_dir or os.path.dirname(src), stem + ".txt")

    def already_done(out):
        return not a.force and os.path.exists(out) and os.path.getsize(out) > 0

    # Only fetch the model if there is actually something to transcribe.
    todo = [f for f in files if not already_done(out_path(f))]
    model_path = ensure_model(a.model) if todo else a.model

    import mlx_whisper
    prompt = a.prompt or DEFAULT_PROMPTS.get(a.lang or "")
    done = skipped = failed = 0
    for i, src in enumerate(files, 1):
        out = out_path(src)
        tag = f"[{i}/{len(files)}] {os.path.basename(src)}"
        if already_done(out):
            print(f"{tag}: exists, skipped"); skipped += 1; continue
        t = time.time()
        try:
            r = mlx_whisper.transcribe(
                src, path_or_hf_repo=model_path, language=a.lang, initial_prompt=prompt,
                # Off: otherwise one mis-heard stretch can make Whisper repeat a line dozens of times.
                condition_on_previous_text=False,
            )
        except Exception as e:   # one bad file must not stop a batch
            print(f"{tag}: FAILED ({type(e).__name__}: {str(e)[:120]})"); failed += 1; continue
        segs = [s for s in r["segments"] if s["text"].strip()]
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out + ".part", "w") as f:
            for s in segs:
                f.write(f"[{ts(s['start'])}] {s['text'].strip()}\n")
        os.replace(out + ".part", out)
        if a.srt:
            with open(os.path.splitext(out)[0] + ".srt", "w") as f:
                for k, s in enumerate(segs, 1):
                    f.write(f"{k}\n{ts(s['start'], True)} --> {ts(s['end'], True)}\n{s['text'].strip()}\n\n")
        length = ts(segs[-1]["end"]) if segs else "0:00"
        print(f"{tag}: {length} audio, {len(segs)} lines, {time.time() - t:.0f}s, lang={r.get('language')} -> {out}")
        for w in quality(segs):
            print(f"   ! {w}")
        done += 1
    print(f"\n{done} transcribed, {skipped} skipped, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
