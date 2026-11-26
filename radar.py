#!/usr/bin/env python3
"""
Reel Radar: free, local creator intelligence. Made by Harsh Rajput · MIT.
Watches videos ALREADY on your PC (never downloads), learns from competitors,
and shows you exactly what to improve.

  python radar.py init        # set niche, platforms, handles, competitors
  python radar.py watch       # analyse new videos in library/ with the live dashboard
  python radar.py report      # rebuild out/playbook.html (You vs Them, creators, videos)
  python radar.py dashboard   # just open the dashboard
"""
import argparse, csv, json, shutil, sys, time
from pathlib import Path

from reel_radar import engine, live, profile, report, server

OUT = Path("out")


def need(tool):
    if not shutil.which(tool):
        sys.exit(f"[!] '{tool}' not found. Run install.bat (Windows) or install.sh first.")


def load_stats(folder):
    f = folder / "stats.csv"
    if not f.exists():
        return {}
    with open(f, encoding="utf-8") as fh:
        return {r["file"]: {k: v for k, v in r.items() if k != "file" and v} for r in csv.DictReader(fh)}


def platform_of(p, creator):
    for c in p["competitors"]:
        if c["name"] == creator:
            return c.get("platform", "unknown")
    return "mine" if creator == p["me"]["name"] else "unknown"


def jobs(p):
    out = []
    for folder in sorted(profile.LIBRARY.glob("*")):
        if not folder.is_dir():
            continue
        stats = load_stats(folder)
        for v in sorted(folder.rglob("*")):
            if v.suffix.lower() in engine.VIDEO_EXT:
                out.append((folder.name, v, stats))
    return out


def cmd_watch(a):
    need("ffmpeg"); need("ffprobe")
    p = profile.load()
    live.set_out(OUT)
    if not a.no_dashboard:
        server.start(a.port)
    live.settings(brain=a.ollama or "rules only", device="local · no downloads")
    done = set()
    idx = OUT / "study_index.jsonl"
    if idx.exists():
        done = {json.loads(l)["file"] for l in idx.read_text("utf-8").splitlines() if l.strip()}
    todo = [j for j in jobs(p) if str(j[1]) not in done]
    if not todo:
        live.progress(0, 0, "idle")
        live.log("[radar] nothing new in library/. Add videos to library/<creator>/")
    for n, (creator, v, stats) in enumerate(todo, 1):
        live.progress(n - 1, len(todo))
        a.stats = stats
        t0 = time.time()
        try:
            s = engine.analyse(v, creator, platform_of(p, creator), OUT, a)
            with open(idx, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": s["id"], "creator": creator, "file": str(v)}) + "\n")
            live.log(f"[{n}/{len(todo)}] {v.name} analysed in {time.time() - t0:.0f}s")
        except Exception as e:
            live.log(f"[x] {v.name} failed: {e}")
            with open(OUT / "_failed.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"file": str(v), "error": str(e)}) + "\n")
    live.progress(len(todo), len(todo), "done")
    path = report.build(OUT)
    live.log(f"[done] playbook -> {path}")
    if not a.no_dashboard:
        print("Dashboard stays open. Press Ctrl+C to quit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def main():
    ap = argparse.ArgumentParser(description="Reel Radar: local creator intelligence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    w = sub.add_parser("watch")
    w.add_argument("--whisper", default="small", help="tiny/base/small/medium/large-v3")
    w.add_argument("--ollama", help="local vision model for AI verdict, e.g. qwen2.5vl:7b")
    w.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    w.add_argument("--scene", type=float, default=0.3, help="cut sensitivity (lower = more cuts)")
    w.add_argument("--no-ocr", action="store_true")
    w.add_argument("--no-dashboard", action="store_true")
    w.add_argument("--port", type=int, default=8765)
    sub.add_parser("report")
    d = sub.add_parser("dashboard"); d.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    if a.cmd == "init":
        profile.init()
    elif a.cmd == "watch":
        cmd_watch(a)
    elif a.cmd == "report":
        print(report.build(OUT))
    elif a.cmd == "dashboard":
        server.start(a.port)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
