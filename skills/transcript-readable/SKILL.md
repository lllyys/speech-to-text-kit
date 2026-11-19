---
name: transcript-readable
description: Turn a raw speech-to-text transcript (or an audio recording) of a talk, lecture, podcast or meeting into an easy-to-read Markdown version — paragraphs under section headings, filler words and ASR repeats removed, the speaker's own wording kept, mis-heard words corrected inline with visible markers, unclear spots flagged, and a correction list with timestamps at the end. Use this whenever the user wants a transcript cleaned up, made readable, or turned into an article or notes they can read — including Whisper / 语音转文字 output, time-stamped [mm:ss] lines, downloaded lecture replays, and requests like "make it easier to read", "整理成文字稿", "transcript_readable", even if they don't say "transcript". Not for summarizing or translating — the result keeps what the speaker said. For just getting the raw text out of audio, use audio-to-text.
---

# transcript-readable

Produce a faithful, readable written version of a spoken recording. The reader should be able to read it like an article, while still being able to trust that every sentence is something the speaker actually said — and to see exactly where you changed a word.

The two failure modes to avoid pull in opposite directions:
- **Too raw**: one fragment per line, 对吧 every other sentence, obvious mis-hearings left in. Unreadable.
- **Too polished**: you rewrote, summarized, or "improved" the argument. Now it's your text, not theirs, and the reader can't tell. This is worse, because it is silent.

So: restructure and remove noise freely, but change *words* only where the transcription is wrong — and mark every such change.

## Step 1 — Get a raw transcript

- **Input is already text** (e.g. `transcript.txt` with `[mm:ss] ...` lines): use it.
- **Input is audio/video** (`.m4a .mp3 .wav .mp4 ...`): transcribe it locally first with the `audio-to-text` skill (read its SKILL.md for options and checks). The usual call:

  ```bash
  uv run --quiet --with mlx-whisper python "${CLAUDE_SKILL_DIR}/../audio-to-text/scripts/transcribe.py" \
      "<audio>" --out "<folder>/transcript.txt" --lang zh
  ```

  (`audio-to-text` sits next to this skill, so `${CLAUDE_SKILL_DIR}/../audio-to-text` finds it whether the two are installed as a plugin or as personal skills. Check `--model-status` first, as that skill describes.)

Never modify the raw transcript — it's the evidence your corrections are checked against.

## Step 2 — Read the whole transcript before writing

Read it end to end first. You need the whole talk to:
- see its real structure (where the speaker changes topic, what the through-line is);
- resolve mis-hearings from context — a garbled word at minute 18 is often said clearly at minute 2 (e.g. 地规 → 递归 once he says "递归" plainly elsewhere);
- recognise recurring names and terms so you spell them the same way everywhere.

Note who the speaker is if the context tells you (course name, how they refer to themselves) — it helps fix the speaker's own name when ASR garbles it (e.g. a host introduced as "Jon Smith" transcribed as "John Smyth" later on).

## Step 3 — Write the readable version

**Structure**
- Merge fragments into normal paragraphs, one idea per paragraph.
- Add section headings (`##`) where the speaker actually shifts topic — usually 4–8 for a 20-minute talk. Headings are your labels, so keep them short and descriptive; don't put claims in them the speaker didn't make.
- When the speaker enumerates something with parallel attributes (roles in a team, steps, options), a table can be much clearer than prose. Use one only when the content really is a list of like items.
- Bold the handful of sentences that carry the talk's main points — sparingly.

**What to remove**
- Fillers and tics: 对吧、然后呢、那么、这个这个、好了、OK、嗯、啊, "you know", "like", "so yeah".
- ASR duplicates: Whisper often emits the same sentence twice in a row. Keep one. (A deliberate repeat for emphasis, mid-flow, can stay.)
- False starts and self-corrections — keep the corrected version ("再让去，再让这个AI帮我去判断" → "再让 AI 帮我判断").

**What to keep**
- The speaker's own words, phrasing, examples, asides and tone. If they said it colloquially, keep it colloquial.
- Their order of ideas, even when it wanders.
- Opinions and claims exactly as stated, even ones you think are wrong.
- English terms the speaker used in English (agent team, thinking effort, token).

Do not summarize, compress, add transitions that introduce new ideas, or add your own explanations into the body.

**Corrections — mark every one**
When a word is clearly mis-transcribed and context tells you what was said, write the correct word followed by a marker with the original:

> 贝叶斯推理〔原转写为“BIS推理”〕

Use the marker language of the transcript (for English: `[transcribed as "..."]`). Typical ASR errors worth fixing (transcribed → meant):
- Homophones / near-homophones: 地规→递归, 心而上→形而上, 平坦标准→评判标准, 遍例→遍历.
- English product and model names: Cloud→Claude, DeepSick→DeepSeek, mark-文件→Markdown 文件.
- People's names: 黄人熊→黄仁勋, 黄书俊→黄舒骏; inconsistent spellings of the same person (Cesar/Ceaser → Caesar).
- Titles of works: VVendant → 《V字仇杀队》(*V for Vendetta*).

Correcting a name's spelling to its standard form everywhere is fine; list it once in the correction table rather than marking every occurrence.

**When you're not sure, don't guess** — keep the transcribed text and add **[?]**, optionally with your best guess: `Grokbot [?]〔原转写为“Glockbot”〕`. A wrong confident correction is worse than an honest [?], because the reader will trust it.

## Step 4 — Output file

Save as `transcript_readable.md` next to the raw transcript (or next to the audio). Never overwrite `transcript.txt`.

Use this layout, with labels in the transcript's language:

```markdown
# <talk title>

<course/source> · <date> · 约 <N> 分钟

> 由录音自动转写（<model>），再整理成段落：删去口头禅和重复句，原话的意思和用词尽量保留。
> **〔方括号〕** 里是对听错词的更正；**[?]** 表示听不清、无法确定。完整更正清单见文末。
> 原始逐句转写（带时间码）：`transcript.txt`

---

## 一、<section>
...

---

## 更正清单

**较有把握的更正**

| 原转写 | 更正为 | 位置 |
|---|---|---|
| BIS推理 | 贝叶斯推理 | 00:49 |

**无法确定的地方**（标为 [?]，建议对照录音）

| 原转写 | 可能是 | 位置 |
|---|---|---|
| Glockbot | 可能是 Grok 的某个 bot 产品 | 06:17, 07:40 |
```

Take timestamps from the raw transcript lines so the user can jump to the spot in the audio.

## Step 5 — Check before handing over

Skim the raw transcript against your version once more:
- Did any section of the talk go missing? (Check the last raw timestamp appears in the flow — endings get dropped.)
- Is every changed word either marked inline or covered by a name-spelling row in the table?
- Did you add anything the speaker didn't say? Remove it.

Then tell the user where the file is, what you changed in a sentence or two, and point out the [?] spots — those are where their ear is needed.
