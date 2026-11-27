---
name: radar-setup
description: Reel Radar first-run wizard. Use when the user types "start", "set up Reel Radar", is new, or radar.json is missing.
---

# 🚀 First-run wizard
1. `python radar.py doctor`. If anything fails, give its one-line fix and stop.
2. Ask in ONE message (plain English): your niche in a few words? · main language (en/hi/pa…)? · platforms (YouTube Shorts, Instagram Reels)?
3. Save: `python radar.py init --niche "…" --language xx --platforms youtube_shorts,instagram_reels`
4. Tell the user to drop their own videos into `library/me/` (and competitors' into `library/<name>/`), then open it: Windows `explorer library\me`, Mac `open library/me`.
   No videos yet? Run `python radar.py demo` to show the dashboard with sample clips.
5. When they say done: `python radar.py watch` (dashboard opens by itself), then hand to the `radar` skill.
