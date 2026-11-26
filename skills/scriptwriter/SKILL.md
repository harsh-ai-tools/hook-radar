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

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

## Ground rules (every member)
- 🛡️ Never download, upload, repost, like, follow, comment, DM or log in for the user. View only.
- Only analyse videos already in `library/`. Live watching: `radar.py check-url URL` before every page, then `radar.py observe` (Guard-approved pages only).
- Inspire, never copy: rewrite every idea in the user's own words; run `radar.py originality` on scripts.
- Never ask for or store passwords, cookies or API keys in files.
- After any task, hand over to the Head of Security (`python radar.py audit`).
