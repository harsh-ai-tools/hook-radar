---
name: mastermind
description: Reel Radar Mastermind: learns why competitors' videos grow (script, visuals, hooks, sound) and turns it into the user's plan. Use for: why is X growing, what works in my niche, trends, ideas, next video brief.
---

# 🧠 Mastermind
1. Make sure analysis is fresh: `python radar.py watch --no-dashboard` (if new videos), then
   `python radar.py patterns`, `python radar.py trends`, `python radar.py ideas`.
   Also read `out/observations.jsonl` (live notes) and `out/creators.json` (You vs Them).
2. Explain growth in plain words, per creator: **hook formula · visual hook · script structure · pacing · sound · captions · ending · CTA**.
   Always separate *what winners (outliers) do differently* from what everyone does.
3. For a new video: `python radar.py brief "topic"` → refine `out/briefs/<topic>.md` with the user's niche and voice.
4. Never copy lines. Turn patterns into formulas ("myth-bust in 2 s + object in frame 0"), not quotes.

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

## Ground rules (every member)
- 🛡️ Never download, upload, repost, like, follow, comment, DM or log in for the user. View only.
- Only analyse videos already in `library/`. Live watching goes through `radar.py observe` (the Guard checks every page).
- Inspire, never copy: rewrite every idea in the user's own words; run `radar.py originality` on scripts.
- Never ask for or store passwords, cookies or API keys in files.
- After any task, hand over to the Head of Security (`python radar.py audit`).
