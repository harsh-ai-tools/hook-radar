---
name: live-watcher
description: Reel Radar Live Watcher: watches competitor Reels/Shorts live in the user's browser, view-only, so the user can see what the AI sees. Use when the user asks to watch Instagram/YouTube/TikTok live or study videos without files.
---

# 👀 Live Watcher (eyes in the browser)
1. Start the dashboard so the user can follow along: `python radar.py dashboard`.
2. Open the creator's public page in the user's browser (view only). Do not log in, like, follow, comment or download.
3. **Before opening ANY page**, ask the Guard: `python radar.py check-url "URL"`.
   - `ALLOWED` → open it. `BLOCKED` → do not open it; tell the user why (wrong site, login page, or a short break).
4. For each video (default max 100 per hour, 4 s apart; set in `radar.json` → `"live"`):
   - note the **visual hook** (frame 0), **text hook**, **spoken hook** (first 3 s), length, caption style, views if shown;
   - log it: `python radar.py observe --url URL --creator NAME --platform instagram_reels --hook "..." --text-hook "..." --visual "..." --views 12000 --notes "pacing, music, ending"`.
   - `observe` refuses pages the Guard didn't approve.
5. Hand the observations to the Mastermind.

_Run from the Reel Radar folder (the one with `radar.py`): `python radar.py <cmd>` (`py` on Windows). Rules: see the `radar` skill._
