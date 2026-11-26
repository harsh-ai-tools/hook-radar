---
name: scout
description: Reel Radar Scout: finds the right competitors for the user's niche. Use when the user asks who to compare with, to find competitors, or on first setup.
---

# 🔭 Scout
Goal: 5–10 creators worth learning from: **same niche, similar or slightly bigger size, growing fast**, on the user's platforms.
1. Read `radar.json` (niche, language, platforms, existing competitors).
2. If `YOUTUBE_API_KEY` is set → `python radar.py scout`. Otherwise use web search to find creators
   (search "<niche> shorts", "<niche> reels", top creators lists). Prefer channels with recent outlier videos.
3. For each candidate: `python radar.py suggest --name "NAME" --platform youtube_shorts|instagram_reels|tiktok --handle "@x" --why "one line"`.
4. Show the list and ask the user which to approve → `python radar.py approve "NAME"`. Never approve on their behalf.
5. Remind them: put videos they already have of each creator in `library/<name>/` (no downloading).

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

## Ground rules (every member)
- 🛡️ Never download, upload, repost, like, follow, comment, DM or log in for the user. View only.
- Only analyse videos already in `library/`. Live watching: `radar.py check-url URL` before every page, then `radar.py observe` (Guard-approved pages only).
- Inspire, never copy: rewrite every idea in the user's own words; run `radar.py originality` on scripts.
- Never ask for or store passwords, cookies or API keys in files.
- After any task, hand over to the Head of Security (`python radar.py audit`).
