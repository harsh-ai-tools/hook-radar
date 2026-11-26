---
name: scriptwriter
description: Reel Radar Scriptwriter: writes short-form scripts from a Mastermind brief, in the user's own voice. Use when the user asks for a script, hooks or a rewrite.
---

# ✍️ Scriptwriter
1. Read the brief (`out/briefs/*.md`) and the user's own past transcripts (`library/me` studies) to match their voice.
2. Write 5 hook options (<15 words; myth-bust, shock fact, question, numbered promise, visual-first). Hook must land in 3 s, said out loud AND shown as text.
3. Script at the brief's length and words-per-minute; one idea per line; a re-hook ~40% in; ending that loops to the start. Grade 6–8 English (or the user's language).
4. Save as `script.txt` and run `python radar.py originality script.txt`. Over 25% → rewrite.
5. Mark any fact that needs checking with [verify].

_Run from the Reel Radar folder (the one with `radar.py`): `python radar.py <cmd>` (`py` on Windows). Rules: see the `radar` skill._
