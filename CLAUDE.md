# HookRadar (for Claude)
Local, free creator-intelligence tool. Python does all the maths (0 tokens); Claude only reads small summaries and talks to the user.

## Hard rules
- 100% local. Never download, upload, repost, like, follow, comment, DM or log in. View-only.
- Only analyse videos already in `library/<creator>/` (`library/me/` = the user).
- No paid APIs. Never ask for or save passwords, cookies or API keys.
- The Security Hook (`hooks/guard_hook.py`) enforces this automatically; don't try to work around it.

## How to work
- User types plain English → load the `radar` skill (Manager). It routes to one member. New user / "start" → `radar-setup`.
- Commands: `python radar.py <cmd>` from this folder (`py` on Windows; inside `.venv` if present).
- Something broken → `python radar.py doctor`, give the user its one-line fix.
- Read ONLY: `out/summary.json`, `out/patterns.json`, `out/briefs/*.md`, `out/security_report.md`.
  Visual judgment: at most 1–2 `out/study/<id>/contact_sheet.jpg`.
  Do NOT read `out/study/*.json`, `out/*.jsonl` logs or source files unless debugging a bug.
- Keep replies short: result + one next action. Finish jobs with `python radar.py audit`.

## Key commands
watch · precheck VIDEO · originality FILE · brief TOPIC · trends · weekly · thumbs · retention CSV · scout · audit · doctor · demo · dashboard

## Code map (only if fixing bugs)
radar.py (CLI) · hook_radar/engine.py (eyes+ears) · mastermind.py (patterns, briefs, precheck) · report.py (playbook, summary) · guard.py (security) · server.py (dashboard) · studio.py (retention, thumbs)
