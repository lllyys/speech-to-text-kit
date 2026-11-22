# Speech-to-Text Kit

A Claude Code plugin that turns recordings — lectures, talks, podcasts, voice memos — into text, entirely on your own Mac.

| Skill | What it does |
|---|---|
| **audio-to-text** | Audio/video → time-stamped raw transcript (`[mm:ss] …`), optionally `.srt` subtitles. Local Whisper via [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper); nothing is uploaded. Batches whole folders and skips files already done. |
| **transcript-readable** | Raw transcript → readable Markdown article: paragraphs and section headings, fillers and ASR repeats removed, the speaker's own wording kept. The body shows corrected wording without inline notes by default. Unclear spots are flagged `[?]`, and the final correction table preserves the original wording and timestamps. Inline notes are available on request. |

Tuned for Mandarin (simplified Chinese with punctuation); works for English and other languages Whisper supports.

## Install

```
/plugin marketplace add lllyys/speech-to-text-kit
/plugin install speech-to-text-kit@speech-to-text-kit
```

Then just ask, for example:

- "extract the text from `lecture.m4a`" / "把这个录音转成文字" → **audio-to-text**
- "make this transcript easier to read" / "整理成文字稿" → **transcript-readable** (give it audio and it transcribes first)

## Requirements

- Apple Silicon Mac (mlx-whisper runs on the Apple GPU)
- [`uv`](https://docs.astral.sh/uv/) — the script runs with `uv run --with mlx-whisper`, so nothing is installed globally
- `ffmpeg` (mlx-whisper uses it to read audio)
- Disk space for the model: **~1.6 GB** for the default `whisper-large-v3-turbo`, downloaded once into `~/.cache/huggingface`

## The model download

The model is fetched the first time it's needed. The skill checks for it first and tells you the size before downloading anything:

```bash
python transcribe.py --model-status      # downloaded / NOT downloaded (~1.6 GB on first use)
python transcribe.py --download-model    # fetch it now, without transcribing
python transcribe.py --download-model --mirror   # via https://hf-mirror.com if huggingface.co is slow or blocked
```

Interrupted downloads resume on re-run, free disk space is checked first, and a half-downloaded model folder is detected rather than mistaken for a working one.

| Model | Download | Note |
|---|---|---|
| `mlx-community/whisper-large-v3-turbo` (default) | ~1.6 GB | best speed/accuracy balance |
| `mlx-community/whisper-large-v3-mlx` | ~3.1 GB | a bit more accurate, ~2× slower |
| `mlx-community/whisper-small-mlx` | ~0.5 GB | fast, noticeably weaker on Mandarin |

Speed on an M5 with the default model: a 21-minute lecture transcribes in about 37 seconds.

## Using the script directly

```bash
uv run --with mlx-whisper python skills/audio-to-text/scripts/transcribe.py \
    talk.m4a recordings/ --lang zh --srt --prompt "Claude, Codex, 贝叶斯"
```

`python transcribe.py --help` lists every option.

## License

MIT
