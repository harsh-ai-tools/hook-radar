---
name: live-watcher
description: Reel Radar Live Watcher: watches competitor Reels/Shorts live in the user's browser, view-only, so the user can see what the AI sees. Use when the user asks to watch Instagram/YouTube/TikTok live or study videos without files.
---

# 👀 Live Watcher (eyes in the browser)
1. Start the dashboard so the user can follow along: `python radar.py dashboard`.
2. Open the creator's public page in the user's browser (view only). Do not log in, like, follow, comment or download.
3. For each video (max 30 per 3 hours, human pace):
   - note the **visual hook** (frame 0), **text hook**, **spoken hook** (first 3 s), length, caption style, views if shown;
   - log it: `python radar.py observe --url URL --creator NAME --platform instagram_reels --hook "..." --text-hook "..." --visual "..." --views 12000 --notes "pacing, music, ending"`.
   - If the Guard blocks a URL or says "too fast", obey it.
4. Hand the observations to the Mastermind.

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

## Ground rules (every member)
- 🛡️ Never download, upload, repost, like, follow, comment, DM or log in for the user. View only.
- Only analyse videos already in `library/`. Live watching goes through `radar.py observe` (the Guard checks every page).
- Inspire, never copy: rewrite every idea in the user's own words; run `radar.py originality` on scripts.
- Never ask for or store passwords, cookies or API keys in files.
- After any task, hand over to the Head of Security (`python radar.py audit`).
