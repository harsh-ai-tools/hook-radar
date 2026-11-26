#!/usr/bin/env python3
"""
📡 Reel Radar: free, local creator intelligence. Made by Harsh Rajput · MIT.
Watches videos ALREADY on your PC (never downloads), learns from competitors,
and tells you exactly what to improve.

SETUP      init · scout · suggest · approve · stats-template
WATCH      watch · observe (live browser notes) · dashboard
LEARN      report · patterns · trends · ideas
CREATE     brief "topic" · precheck my_draft.mp4 · originality my_script.txt
SAFETY     audit
EVERYTHING weekly
Run `python radar.py <command> -h` for details.
"""
import argparse, csv, json, os, shutil, sys, time
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)          # work from the tool folder wherever it's launched
for _s in (sys.stdout, sys.stderr):                  # Windows consoles: never crash on emoji/unicode names
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from reel_radar import engine, guard, live, mastermind, profile, report, server

OUT = Path("out")


def need(tool):
    if not shutil.which(tool):
        sys.exit(f"[!] '{tool}' not found. Run install.bat (Windows) or install.sh first.")


def load_stats(folder):
    f = folder / "stats.csv"
    if not f.exists():
        return {}
    with open(f, encoding="utf-8-sig") as fh:
        return {r["file"]: {k: v for k, v in r.items() if k != "file" and v} for r in csv.DictReader(fh) if r.get("file")}


def platform_of(p, creator):
    for c in p["competitors"]:
        if c["name"] == creator:
            return c.get("platform", "unknown")
    return "mine" if creator == p["me"]["name"] else "unknown"


def videos_in(folder):
    return [v for v in sorted(folder.rglob("*")) if v.suffix.lower() in engine.VIDEO_EXT and not v.name.startswith(".")]


def jobs():
    out = []
    for folder in sorted(profile.LIBRARY.glob("*")):
        if folder.is_dir() and not folder.name.startswith("_"):
            stats = load_stats(folder)
            out += [(folder.name, v, stats) for v in videos_in(folder)]
    return out


def add_watch_args(w):
    w.add_argument("--whisper", default="small", help="tiny/base/small/medium/large-v3")
    w.add_argument("--gpu", action="store_true", help="use NVIDIA GPU for speech-to-text (needs CUDA)")
    w.add_argument("--ollama", help="local vision model for AI verdict, e.g. qwen2.5vl:7b")
    w.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    w.add_argument("--scene", type=float, default=0.3, help="cut sensitivity (lower = more cuts)")
    w.add_argument("--no-ocr", action="store_true")


# ------------------------------------------------------------------ commands
def cmd_watch(a):
    need("ffmpeg"); need("ffprobe")
    p = profile.load()
    a.language = p.get("language")
    run_start = time.time()
    live.set_out(OUT)
    if not a.no_dashboard:
        server.start(a.port)
    live.settings(brain=a.ollama or "rules only", device=("GPU" if a.gpu else "CPU") + " · local · no downloads")
    idx = OUT / "study_index.jsonl"
    done = set()
    if idx.exists():
        done = {json.loads(l)["file"] for l in idx.read_text("utf-8").splitlines() if l.strip()}
    todo = [j for j in jobs() if j[1].as_posix() not in done]
    if not todo:
        live.log("[radar] nothing new in library/. Add videos to library/<creator>/")
    for n, (creator, v, stats) in enumerate(todo, 1):
        live.progress(n - 1, len(todo))
        ok, why = guard.check_video(v)
        if not ok:
            live.log(f"[guard] blocked {v.name}: {why}")
            continue
        a.stats = stats
        t0 = time.time()
        try:
            s = engine.analyse(v, creator, platform_of(p, creator), OUT, a)
            with open(idx, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": s["id"], "creator": creator, "file": v.as_posix(), "t": time.time()}) + "\n")
            live.log(f"[{n}/{len(todo)}] {v.name} analysed in {time.time() - t0:.0f}s")
        except Exception as e:
            live.log(f"[x] {v.name} failed: {e}")
            with open(OUT / "_failed.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"file": v.as_posix(), "error": str(e)}) + "\n")
    live.progress(len(todo), len(todo), "done")
    report.build(OUT)
    mastermind.patterns(OUT)
    passed, findings = guard.head_audit(run_start)
    live.log(f"[security] Head of Security: {'PASS' if passed else 'FAIL'}"
             + ("" if passed else " · " + "; ".join(findings[:3])))
    live.log("[done] playbook -> out/playbook.html")
    if not a.no_dashboard:
        print("Dashboard stays open. Press Ctrl+C to quit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def cmd_precheck(a):
    need("ffmpeg"); need("ffprobe")
    src = Path(a.video)
    if not src.is_file():
        sys.exit(f"[!] not found: {src}")
    drafts = profile.LIBRARY / "_drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    dst = drafts / src.name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)                          # local copy only: drafts never leave your PC
    ok, why = guard.check_video(dst)
    if not ok:
        sys.exit(f"[guard] {why}")
    a.language = profile.load().get("language"); a.stats = {}
    live.set_out(OUT)
    s = engine.analyse(dst, "_drafts", "draft", OUT, a)
    r = mastermind.precheck(s, OUT)
    print(f"\nScore: {r['score']}/100 (vs {r['compared_with']} winning videos)")
    for f in r["fixes"]:
        print(" 🔧", f)
    print(f"Saved: out/precheck/{s['id']}.md")


def cmd_originality(a):
    text = Path(a.script).read_text("utf-8", errors="ignore")
    trs = {s["id"]: s.get("transcript", "") for s in report.load_studies(OUT) if s["creator"] not in ("me", "_drafts")}
    (ok, why), overlap = guard.check_originality(text, trs)
    print(("✅ Original enough. " if ok else "⛔ ") + why + (f" (max overlap {overlap:.0%})" if overlap is not None else ""))


def cmd_observe(a):
    """Called by Claude while it views a video live in your browser (view-only)."""
    ok, why = guard.check_url(a.url)
    if ok:
        ok, why = guard.check_live_pace()
    if not ok:
        sys.exit(f"[guard] blocked: {why}")
    rec = {"t": time.time(), "url": a.url, "creator": a.creator, "platform": a.platform,
           "hook_spoken": a.hook, "hook_text": a.text_hook, "visual_hook": a.visual,
           "views": a.views, "notes": a.notes}
    ok, why = guard.check_secrets(json.dumps(rec), "observation")
    if not ok:
        sys.exit(f"[guard] {why}")
    OUT.mkdir(exist_ok=True)
    with open(OUT / "observations.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    live.set_out(OUT)
    live.log(f"[live] {a.creator}: \"{a.hook or a.text_hook}\" ({a.platform})")
    print("saved observation")


def print_suggested(p):
    if not p["suggested"]:
        print("No suggestions waiting."); return
    print("\nSuggested competitors (approve with: python radar.py approve \"NAME\"):")
    for s in p["suggested"]:
        print(f" - {s['name']} [{s['platform']}] {s['handle']}: {s['why']}")


def cmd_scout(a):
    p = profile.load()
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        print("No YOUTUBE_API_KEY set. Two options:\n"
              " 1) Ask Claude: 'scout competitors for my niche' (it searches and calls `radar.py suggest`)\n"
              " 2) Get a free YouTube Data API key, set YOUTUBE_API_KEY, then run scout again.")
        return
    import urllib.parse, urllib.request
    guard.log_network("www.googleapis.com", "YouTube Data API (official, read-only)")
    q = urllib.parse.urlencode({"part": "snippet", "q": p["niche"] + " shorts", "type": "channel",
                                "maxResults": 15, "key": key})
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/search?{q}", timeout=30) as r:
        items = json.loads(r.read()).get("items", [])
    ids = ",".join(i["snippet"]["channelId"] for i in items)
    q = urllib.parse.urlencode({"part": "snippet,statistics", "id": ids, "key": key})
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/channels?{q}", timeout=30) as r:
        chans = json.loads(r.read()).get("items", [])
    have = {c["name"].lower() for c in p["competitors"]} | {s["name"].lower() for s in p["suggested"]}
    for c in chans:
        st = c["statistics"]
        views_per_video = int(st.get("viewCount", 0)) / max(int(st.get("videoCount", 1)), 1)
        name = c["snippet"]["title"]
        if name.lower() not in have:
            p["suggested"].append({"name": name, "platform": "youtube_shorts",
                                   "handle": c["snippet"].get("customUrl", c["id"]),
                                   "why": f"{int(st.get('subscriberCount', 0)):,} subs · {views_per_video:,.0f} views/video"})
    profile.save(p)
    print_suggested(p)


def cmd_suggest(a):
    p = profile.load()
    p["suggested"].append({"name": a.name, "platform": a.platform, "handle": a.handle, "why": a.why})
    profile.save(p); print_suggested(p)


def cmd_approve(a):
    p = profile.load()
    pick = [s for s in p["suggested"] if s["name"].lower() == a.name.lower()]
    if not pick:
        sys.exit("Not in suggestions. Run `python radar.py scout` or `suggest` first.")
    p["suggested"] = [s for s in p["suggested"] if s not in pick]
    p["competitors"].append(pick[0] | {"approved": True})
    profile.save(p)
    folder = profile.LIBRARY / pick[0]["name"]
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Approved {pick[0]['name']}. Put their videos (already on your PC) in {folder}/")


def cmd_stats_template(a):
    for folder in sorted(profile.LIBRARY.glob("*")):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        f = folder / "stats.csv"
        have = load_stats(folder)
        missing = [v.name for v in videos_in(folder) if v.name not in have]
        if not missing:
            continue
        new = not f.exists()
        with open(f, "a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["file", "views", "likes", "comments", "posted"])
            for m in missing:
                w.writerow([m, "", "", "", ""])
        print(f"{f}: added {len(missing)} rows. Fill in views (posted = YYYY-MM-DD)")


def cmd_connect(a):
    """Install the AI team as Claude skills (Claude Code / Claude desktop) pointing at this folder."""
    here = Path.cwd().resolve()
    dest = Path(a.to).expanduser() if a.to else Path.home() / ".claude" / "skills"
    n = 0
    for sk in sorted(Path("skills").glob("*/SKILL.md")):
        text = sk.read_text("utf-8").replace(
            "The Reel Radar folder is the one containing `radar.py` (two folders up from this skill file).",
            f"The Reel Radar folder is: `{here}`")
        d = dest / f"reel-radar-{sk.parent.name}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text.replace(f"name: {sk.parent.name}", f"name: reel-radar-{sk.parent.name}", 1), "utf-8")
        n += 1
    print(f"Connected {n} team members to Claude in {dest}")
    print("Restart Claude, then just ask: \"Reel Radar, analyse my competitors\"")


def main():
    ap = argparse.ArgumentParser(description="📡 Reel Radar: local creator intelligence (Made by Harsh Rajput)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="set niche, platforms, handles, competitors")
    w = sub.add_parser("watch", help="analyse new videos in library/ with the live dashboard")
    add_watch_args(w)
    w.add_argument("--no-dashboard", action="store_true")
    w.add_argument("--port", type=int, default=8765)
    pc = sub.add_parser("precheck", help="grade a draft video before you post it")
    pc.add_argument("video"); add_watch_args(pc)
    og = sub.add_parser("originality", help="check your script isn't copied from a competitor")
    og.add_argument("script")
    br = sub.add_parser("brief", help="next-video brief built from winning competitor videos")
    br.add_argument("topic")
    ob = sub.add_parser("observe", help="(used by Claude) log a live, view-only browser observation")
    for x in ("--url", "--creator"):
        ob.add_argument(x, required=True)
    for x in ("--platform", "--hook", "--text-hook", "--visual", "--views", "--notes"):
        ob.add_argument(x, default="")
    sub.add_parser("scout", help="find competitors (YouTube API key or Claude)")
    sg = sub.add_parser("suggest", help="(used by Claude) add a competitor suggestion")
    sg.add_argument("--name", required=True); sg.add_argument("--platform", default="unknown")
    sg.add_argument("--handle", default=""); sg.add_argument("--why", default="")
    apv = sub.add_parser("approve", help="approve a suggested competitor"); apv.add_argument("name")
    sub.add_parser("stats-template", help="create stats.csv rows to fill in views")
    for c, h in (("report", "rebuild playbook"), ("patterns", "what winners do"), ("trends", "rising words in your niche"),
                 ("ideas", "video ideas from pasted comments"), ("audit", "Head of Security audit"),
                 ("weekly", "everything in one weekly report")):
        sub.add_parser(c, help=h)
    cn = sub.add_parser("connect", help="install the AI team into Claude as skills")
    cn.add_argument("--to", help="skills folder (default ~/.claude/skills)")
    d = sub.add_parser("dashboard", help="open the live dashboard"); d.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()

    if a.cmd == "init": profile.init()
    elif a.cmd == "watch": cmd_watch(a)
    elif a.cmd == "precheck": cmd_precheck(a)
    elif a.cmd == "originality": cmd_originality(a)
    elif a.cmd == "brief": print("Brief saved:", mastermind.brief(OUT, a.topic))
    elif a.cmd == "observe": cmd_observe(a)
    elif a.cmd == "scout": cmd_scout(a)
    elif a.cmd == "suggest": cmd_suggest(a)
    elif a.cmd == "approve": cmd_approve(a)
    elif a.cmd == "stats-template": cmd_stats_template(a)
    elif a.cmd == "report": print(report.build(OUT))
    elif a.cmd == "patterns": print(json.dumps(mastermind.patterns(OUT), ensure_ascii=False, indent=2))
    elif a.cmd == "trends":
        for t in mastermind.trends(OUT):
            print(f"{t['score']:>7}  {t['term']}")
    elif a.cmd == "ideas":
        for i in mastermind.comment_ideas(profile.LIBRARY, OUT):
            print(f"{i['times']}x {i['idea']}")
    elif a.cmd == "audit":
        ok, f = guard.head_audit()
        print("PASS ✅" if ok else "FAIL ❌", *f, "Report: out/security_report.md", sep="\n")
    elif a.cmd == "connect": cmd_connect(a)
    elif a.cmd == "weekly": print("Weekly report:", mastermind.weekly(OUT, profile.LIBRARY))
    elif a.cmd == "dashboard":
        server.start(a.port)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
