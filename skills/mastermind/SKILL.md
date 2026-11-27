---
name: mastermind
description: HookRadar Mastermind: learns why competitors' videos grow (script, visuals, hooks, sound) and turns it into the user's plan. Use for: why is X growing, what works in my niche, trends, ideas, next video brief.
---

# 🧠 Mastermind
1. Make sure analysis is fresh: `python radar.py watch --no-dashboard` (if new videos), then
   `python radar.py patterns`, `python radar.py trends`, `python radar.py ideas`.
   Also read `out/observations.jsonl` (live notes) and `out/creators.json` (You vs Them).
2. Explain growth in plain words, per creator: **hook formula · visual hook · script structure · pacing · sound · captions · ending · CTA**.
   Always separate *what winners (outliers) do differently* from what everyone does.
3. For a new video: `python radar.py brief "topic"` → refine `out/briefs/<topic>.md` with the user's niche and voice.
4. Never copy lines. Turn patterns into formulas ("myth-bust in 2 s + object in frame 0"), not quotes.

_Run from the HookRadar folder (the one with `radar.py`): `python radar.py <cmd>` (`py` on Windows). Rules: see the `radar` skill._
