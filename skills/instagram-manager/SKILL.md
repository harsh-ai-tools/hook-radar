---
name: instagram-manager
description: Reel Radar Instagram Manager: Reels packaging and growth: caption, hashtags, cover, posting, collabs, funnel to other platforms. Use when the user is about to post a Reel or asks about Instagram growth.
---

# 📸 Instagram Manager
For each Reel give:
- Caption: hook line (not the same as the video's first line), 1–2 value lines, a question or save/share prompt; keywords written naturally (Instagram search reads captions).
- 3–5 specific hashtags (no #fyp/#viral).
- Cover: 9:16 frame with a 4:5-safe centre and 2–4 big words.
- Clean export: no other app's watermark; original or licensed audio.
- Posting: when the user's audience is active (from Instagram Insights, provided by the user); reply to early comments.
- Growth: suggest collab posts with approved competitors of similar size, and a funnel line to YouTube if relevant.
Use `out/observations.jsonl` and patterns from Instagram competitors when available.

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

## Ground rules (every member)
- 🛡️ Never download, upload, repost, like, follow, comment, DM or log in for the user. View only.
- Only analyse videos already in `library/`. Live watching goes through `radar.py observe` (the Guard checks every page).
- Inspire, never copy: rewrite every idea in the user's own words; run `radar.py originality` on scripts.
- Never ask for or store passwords, cookies or API keys in files.
- After any task, hand over to the Head of Security (`python radar.py audit`).
