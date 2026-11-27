---
name: scout
description: Reel Radar Scout: finds the right competitors for the user's niche. Use when the user asks who to compare with, to find competitors, or on first setup.
---

# 🔭 Scout
Goal: 5–10 creators worth learning from: **same niche, similar or slightly bigger size, growing fast**, on the user's platforms.
1. Read `radar.json` (niche, language, platforms, existing competitors).
2. Run `python radar.py scout`. If it says there's no key, don't ask for the key in chat: tell the user they can double-click `SET_YOUTUBE_KEY.bat` (Windows) / `SET_YOUTUBE_KEY.command` (Mac) later (README → Scout setup), and meanwhile use web search to find creators
   (search "<niche> shorts", "<niche> reels", top creators lists). Prefer channels with recent outlier videos.
3. For each candidate: `python radar.py suggest --name "NAME" --platform youtube_shorts|instagram_reels --handle "@x" --why "one line"`.
4. Show the list and ask the user which to approve → `python radar.py approve "NAME"`. Never approve on their behalf.
5. Remind them: put videos they already have of each creator in `library/<name>/` (no downloading).

_Run from the Reel Radar folder (the one with `radar.py`): `python radar.py <cmd>` (`py` on Windows). Rules: see the `radar` skill._
