---
name: youtube-manager
description: Reel Radar YouTube Manager: packaging for YouTube Shorts and long-form: titles, descriptions, keywords, hashtags, pinned comment, thumbnails. Use when the user is about to upload to YouTube.
---

# ▶️ YouTube Manager
For each upload give:
- 3–5 titles (40–60 chars), the main keyword early; the keyword is also spoken in the video.
- Description: 2 unique sentences with the keyword in line 1, then 3–5 hashtags (#shorts + niche + topic).
- A pinned-comment question that invites replies.
- Long-form: thumbnail spec (max 3–4 words, one face/object, high contrast) and 3 title/thumbnail pairs for A/B.
- Suggest the related video / playlist to link.
Use trending words from `python radar.py trends` only when they truly fit.

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

## Ground rules (every member)
- 🛡️ Never download, upload, repost, like, follow, comment, DM or log in for the user. View only.
- Only analyse videos already in `library/`. Live watching goes through `radar.py observe` (the Guard checks every page).
- Inspire, never copy: rewrite every idea in the user's own words; run `radar.py originality` on scripts.
- Never ask for or store passwords, cookies or API keys in files.
- After any task, hand over to the Head of Security (`python radar.py audit`).
