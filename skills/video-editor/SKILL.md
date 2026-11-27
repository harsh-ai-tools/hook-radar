---
name: video-editor
description: HookRadar Video Editor: turns a script into an edit plan (cuts, captions, sound, visuals) matching what winning videos do. Use when the user asks how to edit, or before exporting.
---

# ✂️ Video Editor
Use the brief targets (cuts per 10 s, shot length, caption words, voice-over-music level) and output a timecoded plan:
| time | visual | on-screen text | sound |
Rules: something moves in frame 0 · first cut within 1 s · visual reset every 2–3 s · captions 2–4 words in the safe zone (middle-lower third) · voice ~10 dB above music · music drop or 0.3 s silence before each re-hook · no fade to black, no long outro.
After export: `python radar.py precheck final.mp4` and fix every 🔧 before posting.

_Run from the HookRadar folder (the one with `radar.py`): `python radar.py <cmd>` (`py` on Windows). Rules: see the `radar` skill._
