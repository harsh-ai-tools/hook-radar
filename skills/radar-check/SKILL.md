---
name: radar-check
description: HookRadar pre-post check. Use when the user has a draft video or script and asks "is this ready?", "check my video", "is my script copied?".
---

# ✅ Pre-post check
- Draft video: `python radar.py precheck PATH` (add `--gpu` if they have NVIDIA). Show the score + top 3 fixes.
- Script: save as `script.txt`, run `python radar.py originality script.txt`. Over 25% copied → rewrite those lines in the user's words.
- Thumbnail: put it in `library/me/thumbnails/`, run `python radar.py thumbs`.
Report in ≤5 lines: verdict, score, fixes.

_Run from the HookRadar folder (the one with `radar.py`): `python radar.py <cmd>` (`py` on Windows)._
