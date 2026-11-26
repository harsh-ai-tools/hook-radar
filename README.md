# 🎬 Reel Radar

**A free, local AI tool that watches Shorts / Reels / TikToks and turns them into a playbook of hooks, pacing and formats.**
Runs on **Windows, Linux and Mac**. No paid APIs, no account needed.

> Made by **Harsh Rajput** · part of [harsh-ai-tools](https://github.com/harsh-ai-tools): free tools for Claude & creators.

## What it gives you for every video
| Field | What it means |
|---|---|
| Hook line (first 3 s) | Exactly what's said in the opening |
| Cuts, cuts in first 3 s, avg shot length | How fast the edit moves |
| Words per minute, first word at | Voice pacing |
| On-screen text | Captions/titles read by OCR |
| Giveaways | "Comment X", "link in bio", "part 2" style CTAs |
| AI verdict *(optional)* | Hook type, format, story beats, why it works, an idea to steal |
| Views / likes / comments | From the video page |

Everything rolls into **`out/playbook.html`**, a sortable, searchable table with hook thumbnails.

## Install (Windows, one time)
1. Install **Python 3.10+** (tick "Add to PATH").
2. Install **ffmpeg**: `winget install Gyan.FFmpeg`, then reopen the terminal.
3. In this folder: `pip install -r requirements.txt`
4. *Optional AI verdict:* install [Ollama](https://ollama.com), then `ollama pull qwen2.5vl:7b` (8 GB+ VRAM; use `qwen2.5vl:3b` on smaller GPUs).
5. *Optional NVIDIA speed-up:* `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`

## Use
Put links in `urls.txt`, one per line (YouTube Shorts, Instagram Reels or TikTok), then:

```bash
python reel_radar.py --urls urls.txt                         # analyse
python reel_radar.py --urls urls.txt --ollama qwen2.5vl:7b   # + AI verdict
python reel_radar.py --local D:\clips                        # your own .mp4 files, offline
python reel_radar.py --playbook-only                         # rebuild the HTML only
```

## Output
- `out/study/<id>.json`: full analysis (metrics, cut times, on-screen text, transcript with word timing, giveaways, AI verdict)
- `out/study/<id>/hook.jpg` and `contact_sheet.jpg`
- `out/study_index.jsonl`: one summary line per video
- `out/_failed.jsonl`: failures (videos already done are skipped on re-run)

## How it works
`yt-dlp` download → `ffmpeg` scene cuts + key frames → `RapidOCR` on-screen text → `faster-whisper` transcript → pacing metrics → optional local vision model via `Ollama` → JSON + HTML playbook.

## Notes
- AI output is a **draft**: check names, dates and quotes before using them.
- For **study only**. Don't re-upload other creators' videos, and credit them. Downloading may go against platform terms.

## Credits
Inspired by [jakeb144/reel-watcher](https://github.com/jakeb144/reel-watcher) (MIT, Mac-only, uses Apify). Reel Radar is a from-scratch rewrite that is free, cross-platform and adds pacing metrics.

## License
MIT © 2026 Harsh Rajput
