---
name: audio-to-text
description: Extract the spoken text from audio or video files (m4a, mp3, wav, mp4, mov, …) as a time-stamped transcript, transcribed locally on this Mac with Whisper so nothing is uploaded. Handles one file or a whole folder of recordings, skips ones already done, can also write .srt subtitles, and is tuned for Mandarin lectures (simplified Chinese with punctuation) as well as English and other languages. Use this whenever the user wants the words out of a recording — "extract the text", "transcribe this", "语音转文字", "把录音转成文字", "get me subtitles", a downloaded lecture replay or podcast or voice memo they want as text — even if they don't say "transcribe". For turning an existing transcript into a cleaned-up readable article, use transcript-readable instead (it calls this first when given audio).
---

# audio-to-text

Get an accurate, time-stamped raw transcript out of recordings, on the user's own machine.

The output is deliberately *raw*: one line per spoken segment, exactly as Whisper heard it, with a timestamp so any line can be checked against the audio. Don't clean it up here — the raw file is the evidence that later editing (e.g. the `transcript-readable` skill) is checked against. If the user wants something pleasant to read, finish this, then offer `transcript-readable`.

## Run it

```bash
uv run --quiet --with mlx-whisper python "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" \
    <file-or-folder> [more ...] --lang zh
```

(`${CLAUDE_SKILL_DIR}` is this skill's folder; Claude Code fills it in.)

| Option | Use |
|---|---|
| `--lang zh` / `en` / … | The speaker's language. Set it whenever you know it — auto-detect sometimes picks the wrong language on a quiet or music-heavy opening. For Mandarin it also applies a prompt that gives simplified characters with punctuation. |
| `--out PATH` | Exact output file (single input). Default is `<audio name>.txt` next to the audio. |
| `--out-dir DIR` | Put all transcripts in one folder. |
| `--prompt "…"` | Vocabulary hint: names, jargon, products the speaker uses (e.g. `"Claude, Codex, 贝叶斯, 递归"`). Helps a lot with proper nouns. Write it in the target script. |
| `--srt` | Also write `.srt` subtitles. |
| `-r` | Search folders recursively. |
| `--force` | Redo files whose transcript already exists (they're skipped by default, so re-running a batch is safe). |
| `--model` | Default `mlx-community/whisper-large-v3-turbo`. See the model table below; switch only if turbo output is poor. |
| `--model-status` / `--download-model` | Check for / fetch the model without transcribing. |
| `--mirror` | Download the model via `https://hf-mirror.com` when huggingface.co is slow or blocked. |

Choose where output goes by what fits the user's existing layout. For a recording that already has its own folder (e.g. `<title>/` next to `<title>.m4a`), write `--out "<title>/transcript.txt"` so it sits with the lecture.

## Before you start

- **Requirements:** Apple Silicon Mac and `uv`. If either is missing, say so and ask how they'd like to proceed. Don't fall back to an online transcription service on your own: recordings can be private, and uploading them is the user's call.
- **The model must be on the machine.** Check first, then tell the user what will happen before anything big downloads:

  ```bash
  uv run --quiet --with mlx-whisper python "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" --model-status
  ```

  - `downloaded` → go ahead.
  - `NOT downloaded (~1.6 GB …)` → tell the user the size and that it's a one-time download into `~/.cache/huggingface`, then fetch it on its own, in the background, before transcribing:
    `... transcribe.py --download-model` (add `--model …` if using a non-default one).
    Downloading separately keeps a slow download from looking like a hung transcription, and a batch never stalls on file 1.
  - The script also downloads automatically when you transcribe, but announces it first; it checks free disk space, and an interrupted download resumes on re-run.
  - **Slow or failing download** (common behind a proxy or from mainland China): retry with `--mirror`, which downloads through `https://hf-mirror.com`. Don't switch to the mirror without saying so.
  - A `models--…` folder of a few KB in the cache is a leftover from an interrupted download, not a model; `--model-status` reports it as not downloaded, and `--download-model` repairs it.

  | Model | Download | Note |
  |---|---|---|
  | `mlx-community/whisper-large-v3-turbo` (default) | ~1.6 GB | best speed/accuracy balance |
  | `mlx-community/whisper-large-v3-mlx` | ~3.1 GB | a bit more accurate, ~2× slower |
  | `mlx-community/whisper-small-mlx` | ~0.5 GB | fast, noticeably weaker on Mandarin |

- **Timing:** with turbo on an M5, about 40 seconds per 20 minutes of audio (measured: 12 min → 23 s, 21 min → 37 s), plus the one-time download. For long batches or the first run, run the command in the background and wait for it to finish instead of polling.
- Video files work directly; the audio track is used.

## Check the result

The script prints one summary line per file and warnings for the two failures worth catching:
- **`line repeated Nx (possible Whisper loop)`** — Whisper got stuck repeating a phrase. Look at that stretch; re-running with `--force` and a `--prompt`, or with the larger model, usually fixes it.
- **`looks like traditional Chinese`** — rerun with `--lang zh`.

Also look at the file yourself before reporting:
- Does the last timestamp roughly match the audio length? A transcript that stops early means a failed or truncated pass.
- Read the first ~20 and last ~10 lines. Is it the right language, with punctuation, and does it make sense?

## Report to the user

Give the output path(s) in full, the audio length, line count, and two or three opening lines as a sample. Be honest that it's raw machine output: point out a couple of mis-heard words you noticed (names and English terms are the usual ones). Then offer the readable version via `transcript-readable` — don't produce it unasked.
