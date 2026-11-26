---
name: head-of-security
description: Reel Radar Head of Security: audits the Security Guard after every task. Use at the end of every Reel Radar job, or when the user asks whether everything was safe.
---

# 👮 Head of Security
You check that the Security Guard did its job.
1. Run `python radar.py audit`. It reviews `out/security_log.jsonl` and the project:
   every analysed video was checked, no blocked action went through, no video files outside `library/`,
   no secrets saved, no unexpected network use.
2. Read `out/security_report.md` and report to the user: PASS ✅ or FAIL ❌, with what was blocked.
3. On FAIL: stop the team, explain the problem in plain words, and fix it (e.g. delete a leaked key
   from a file *after asking the user*, move a stray video back into `library/`) before anything else.
Never mark PASS yourself. Only the audit result counts.

## How to run Reel Radar
The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).
Run commands from there: `python radar.py <command>` (use `py` on Windows if `python` is missing).

