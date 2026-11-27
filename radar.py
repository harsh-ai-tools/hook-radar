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
import argparse, re, csv, json, os, shutil, sys, time
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)          # work from the tool folder wherever it's launched
for _s in (sys.stdout, sys.stderr):                  # Windows consoles: never crash on emoji/unicode names
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from reel_radar import engine, guard, live, mastermind, profile, report, server, studio

OUT = Path("out")


def need(tool):
    if not shutil.which(tool):
        sys.exit(f"[!] '{tool}' is missing. Fix: double-click INSTALL_WINDOWS.bat (Windows) or INSTALL_MAC.command (Mac).")


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
    w.add_argument("--allow-remote-ai", action="store_true", help="allow an AI host that is not this PC (sends frames/transcripts there)")
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
    for st in reversed(report.load_studies(OUT)):     # show earlier videos in "Watched so far"
        live.watched(engine.watch_item(st))
    idx = OUT / "study_index.jsonl"
    done = set()
    if idx.exists():                                   # cache: skip videos whose content was already analysed
        rows = [json.loads(l) for l in idx.read_text("utf-8").splitlines() if l.strip()]
        done = {r.get("hash") or r["file"] for r in rows}     # old rows (no hash) match by path
    todo = [j for j in jobs() if j[1].as_posix() not in done and engine.file_hash(j[1]) not in done]
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
                f.write(json.dumps({"id": s["id"], "creator": creator, "file": v.as_posix(), "hash": engine.file_hash(v), "t": time.time()}) + "\n")
            live.log(f"[{n}/{len(todo)}] {v.name} analysed in {time.time() - t0:.0f}s")
            failed = OUT / "_failed.jsonl"
            if failed.exists():                         # forget old failures of this video
                keep = [l for l in failed.read_text("utf-8").splitlines() if l.strip() and json.loads(l).get("file") != v.as_posix()]
                failed.write_text("".join(k + "\n" for k in keep), "utf-8")
        except Exception as e:
            live.log(f"[x] {v.name} failed: {e}")
            with open(OUT / "_failed.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"file": v.as_posix(), "error": str(e)}) + "\n")
    live.progress(len(todo), len(todo), "done")
    report.build(OUT)
    mastermind.patterns(OUT)
    passed, findings = guard.head_audit(run_start)
    live.log(f"[security] security audit: {'PASS' if passed else 'FAIL'}"
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


def cmd_check_url(a):
    """Live Watcher MUST call this before opening every page. Exit code 0 = allowed."""
    ok, why = guard.check_url(a.url)
    if ok:
        ok, why = guard.check_live_pace()
    if not ok:
        print(f"BLOCKED: {why}")
        sys.exit(2)
    print("ALLOWED: open it (view only)")


def parse_lines(text):
    """'0:02 words…' lines (captions the page already shows) -> [[seconds, words], ...]"""
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"\s*(?:(\d+):)?(\d+):(\d+)\s+(.*)", line)
        if m:
            h, mi, s, w = m.groups()
            out.append([int(h or 0) * 3600 + int(mi) * 60 + int(s), w.strip()])
    return out


def cmd_observe(a):
    """Called by Claude after viewing a Guard-approved page (view-only)."""
    if not guard.was_approved(a.url):
        guard._log("url", a.url, False, "observed without Guard approval")
        sys.exit("[guard] blocked: run `python radar.py check-url URL` before opening a page")
    rec = {"t": time.time(), "url": guard.norm_url(a.url), "creator": a.creator, "platform": a.platform,
           "hook_spoken": a.hook, "hook_text": a.text_hook, "visual_hook": a.visual,
           "views": a.views, "notes": a.notes, "transcript": parse_lines(a.transcript)}
    p = profile.load()
    mine = {x.lstrip("@").lower() for x in [p["me"]["name"], *p["me"].get("handles", {}).values()] if x}
    rec["mine"] = bool(a.mine) or a.creator.lstrip("@").lower() in mine
    ok, why = guard.check_secrets(json.dumps(rec), "observation")
    if not ok:
        sys.exit(f"[guard] {why}")
    OUT.mkdir(exist_ok=True)
    with open(OUT / "observations.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    live.set_out(OUT); live.load()
    live.web(rec)
    live.log(f"[live] {a.creator}: \"{a.hook or a.text_hook}\" ({a.platform})")
    print("saved observation")


def cmd_hear(a):
    """Optional Instagram hearing: record the speaker output while a reel plays, transcribe, keep only text.
    Audio stays in memory and is never written to disk. Off by default."""
    p = profile.load()
    if a.toggle:
        p["hearing"] = a.toggle == "on"; profile.save(p)
        print(f"Instagram hearing {'ON' if p['hearing'] else 'OFF'}")
        return
    if not p.get("hearing"):
        sys.exit("Instagram hearing is OFF. Turn it on once with: python radar.py hear on")
    if not a.url or not guard.was_approved(a.url):
        sys.exit("[guard] blocked: run `python radar.py check-url URL` first, then hear --url URL")
    try:
        import warnings
        import soundcard as sc
        warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)
    except ImportError:
        sys.exit("Install the recorder once: pip install soundcard")
    mic = sc.get_microphone(str(sc.default_speaker().name), include_loopback=True)
    print(f"[ears] listening to speakers for {a.seconds}s - play the reel now", flush=True)
    audio = mic.record(samplerate=16000, numframes=int(16000 * a.seconds)).mean(axis=1).astype("float32")
    if float(abs(audio).max()) < 1e-4:
        sys.exit("Heard silence: is the reel playing with sound (not muted)?")
    import contextlib
    with contextlib.redirect_stdout(sys.stderr):     # keep stdout = transcript lines only
        r = engine.transcribe(audio, a.model, gpu=a.gpu, language=a.language or p.get("language"))
    del audio
    t0 = r["words"][0]["s"] if r["words"] else 0     # recording starts before play: 0:00 = first word
    for w in _lines([{**w, "s": w["s"] - t0} for w in r["words"]]):
        print(w)


def _lines(words, gap=2.0):
    """words -> '0:02 words' lines (the format observe --transcript reads)."""
    out, cur, t0 = [], [], 0.0
    for w in words:
        if cur and w["s"] - t0 >= gap:
            out.append(f"{int(t0)//60}:{int(t0)%60:02d} " + " ".join(cur)); cur = []
        if not cur:
            t0 = w["s"]
        cur.append(w["w"])
    if cur:
        out.append(f"{int(t0)//60}:{int(t0)%60:02d} " + " ".join(cur))
    return out


def cmd_retention(a):
    """Import an Audience-retention export from YouTube Studio (CSV or the downloaded .zip)."""
    if not Path(a.export).exists():
        sys.exit(f"File not found: {a.export}")
    try:
        s, name, linked = studio.import_retention(OUT, a.export, a.video, a.creator, a.duration)
    except ValueError as e:
        sys.exit(f"Couldn't read that export: {e}")
    print(f"📈 Retention ({s['source']}, {s['duration_s']:.0f}s): 3-second hold {s['hook_hold_3s_pct']}% · "
          f"halfway {s['at_50_pct']}% · end {s['end_pct']}% · average {s['avg_pct']}%")
    for f in s["fixes"]:
        print(" -", f)
    print(f"Saved out/retention/{name}.json" + (" and linked it to the video's study." if linked else
          " (tip: add --video library/me/FILE.mp4 after analysing it to see what was on screen at each drop)"))
    if linked:
        report.build(OUT)


def cmd_thumbs(a):
    """Score thumbnails already in library/<creator>/thumbnails/ (or the files given)."""
    res, vs = studio.thumbnails(OUT, [Path(f) for f in a.files] or None)
    if not res:
        sys.exit("No thumbnails found. Put images in library/me/thumbnails/ and library/<competitor>/thumbnails/")
    for r in sorted(res, key=lambda r: -r["score"]):
        print(f"{r['score']:>3}/100  {r['creator']:<14} {Path(r['file']).name}: {r['fixes'][0]}")
    print("Full report: out/thumbnails.html")


def cmd_forget(a):
    """Delete Reel Radar's analysis data (your videos in library/ are never touched)."""
    target = "ALL analysis data" if a.all else f"all analysis data for '{a.creator}'"
    if not a.yes and input(f"Delete {target}? This can't be undone. Type yes: ").strip().lower() != "yes":
        print("Cancelled."); return
    removed = 0
    if a.all:
        for name in ("study", "precheck", "briefs"):
            if (OUT / name).exists():
                shutil.rmtree(OUT / name); removed += 1
        keep = {"security_log.jsonl", "live_session.json"}     # audit trail + pace limits survive
        for f in list(OUT.glob("*.json*")) + list(OUT.glob("*.md")) + list(OUT.glob("*.html")):
            if f.name not in keep:
                f.unlink(); removed += 1
    else:
        for f in (OUT / "study").glob("*.json"):
            if json.loads(f.read_text("utf-8")).get("creator") == a.creator:
                shutil.rmtree(OUT / "study" / f.stem, ignore_errors=True)
                f.unlink(); removed += 1
        for name in ("study_index.jsonl", "observations.jsonl"):
            f = OUT / name
            if f.exists():
                keep = [l for l in f.read_text("utf-8").splitlines() if l.strip() and json.loads(l).get("creator") != a.creator]
                f.write_text("".join(k + "\n" for k in keep), "utf-8")
        p = profile.load()
        p["competitors"] = [c for c in p["competitors"] if c["name"] != a.creator]
        profile.save(p)
        report.build(OUT)
    guard._log("forget", target, True, f"user deleted {removed} items")
    print(f"Deleted {removed} items. Videos in library/ were not touched.")


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
    if not p.get("niche"):
        sys.exit("Set your niche first: python radar.py init")
    import urllib.error, urllib.parse, urllib.request
    guard.log_network("www.googleapis.com", "YouTube Data API (official, read-only)")

    def api(endpoint, **params):
        q = urllib.parse.urlencode(params | {"key": key})
        try:
            with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{endpoint}?{q}", timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read())["error"]["message"]
            except Exception:
                msg = str(e)
            sys.exit(f"YouTube API said no ({e.code}): {guard.redact(msg)[:200]}\n"
                     "Check the key is a YouTube Data API v3 key and today's free quota isn't used up.")
        except urllib.error.URLError as e:
            sys.exit(f"Could not reach YouTube ({e.reason}). Check your internet connection.")
    items = api("search", part="snippet", q=p["niche"] + " shorts", type="channel", maxResults=25).get("items", [])
    ids = ",".join(i["snippet"]["channelId"] for i in items)
    if not ids:
        print(f"No channels found for '{p['niche']}'. Try a broader niche in radar.json."); return
    # quota: search = 100 units + channels = 1 unit of the free 10,000/day
    chans = api("channels", part="snippet,statistics", id=ids).get("items", [])
    have = {c["name"].lower() for c in p["competitors"]} | {s["name"].lower() for s in p["suggested"]}
    chans.sort(key=lambda c: -int(c["statistics"].get("viewCount", 0)) / max(int(c["statistics"].get("videoCount", 1)), 1))
    for c in chans:
        st = c["statistics"]
        if int(st.get("subscriberCount", 0)) < 1000 and not st.get("hiddenSubscriberCount"):
            continue                                 # skip tiny/new channels: nothing to learn yet
        views_per_video = int(st.get("viewCount", 0)) / max(int(st.get("videoCount", 1)), 1)
        name = c["snippet"]["title"]
        if name.lower() not in have and int(st.get("videoCount", 0)) > 0:
            have.add(name.lower())
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
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", pick[0]["name"]).strip(" .") or "competitor"   # Windows-safe folder
    p["competitors"].append(pick[0] | {"name": safe, "approved": True})
    profile.save(p)
    folder = profile.LIBRARY / safe
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
        text = sk.read_text("utf-8").replace("(the one with `radar.py`)", f"(`{here}`)")
        d = dest / f"reel-radar-{sk.parent.name}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text.replace(f"name: {sk.parent.name}", f"name: reel-radar-{sk.parent.name}", 1), "utf-8")
        n += 1
    print(f"Connected {n} team members to Claude in {dest}")
    print("Restart Claude, then just ask: \"Reel Radar, analyse my competitors\"")


def cmd_doctor():
    """Plain-English health check. One line per item; a fix for anything missing."""
    import importlib.util as iu
    ok = True
    def row(good, name, fix="", optional=False):
        nonlocal ok
        ok = ok and (good or optional)
        print(("✅ " if good else ("➖ " if optional else "❌ ")) + name + ("" if good else f"  →  {fix}"))
    inst = "double-click INSTALL_WINDOWS.bat (Windows) or INSTALL_MAC.command (Mac)"
    row((3, 10) <= sys.version_info[:2] <= (3, 13), f"Python {sys.version.split()[0]}", "install Python 3.12 from python.org, then run the installer again")
    row(sys.prefix != sys.base_prefix or Path(".venv").is_dir(), "Reel Radar environment (.venv)", inst)
    row(bool(shutil.which("ffmpeg")), "ffmpeg (reads videos)", inst)
    row(bool(shutil.which("ffprobe")), "ffprobe (video info)", inst)
    for mod, name in (("faster_whisper", "Whisper (speech to text)"), ("numpy", "numpy"), ("PIL", "Pillow (images)")):
        row(iu.find_spec(mod) is not None, name, inst)
    row(bool(iu.find_spec("rapidocr") or iu.find_spec("rapidocr_onnxruntime")), "OCR (on-screen text)",
        "optional: Claude can read text from the contact sheets instead", optional=True)
    row(Path("radar.json").exists(), "Your profile (radar.json)", "ask Claude 'start' or run: python radar.py init", optional=True)
    n = len(videos_in(profile.LIBRARY / "me")) if (profile.LIBRARY / "me").is_dir() else 0
    row(n > 0, f"Your videos in library/me/ ({n})", "drop a few of your videos into library/me/", optional=True)
    print("All good! Next: python radar.py watch" if ok else "Fix the ❌ lines above, then run doctor again.")
    return ok


def cmd_demo(a):
    """Make 3 tiny sample clips (no download, no AI model needed) and run the full pipeline on them."""
    need("ffmpeg"); need("ffprobe")
    d = profile.LIBRARY / "demo_rival"
    d.mkdir(parents=True, exist_ok=True)
    clips = [("demo_fast_cuts.mp4", "testsrc2", 120000), ("demo_slow.mp4", "smptebars", 8000), ("demo_mid.mp4", "rgbtestsrc", 15000)]
    for name, src, _ in clips:
        if not (d / name).exists():
            parts = [f"{src}=size=360x640:rate=24:duration=2", "color=c=orange:size=360x640:rate=24:duration=2",
                     f"{src}=size=360x640:rate=24:duration=2"]
            cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y"]
            for s in parts:
                cmd += ["-f", "lavfi", "-i", s]
            cmd += ["-filter_complex", "[0][1][2]concat=n=3:v=1", "-pix_fmt", "yuv420p", str(d / name)]
            engine.run(cmd)
    (d / "stats.csv").write_text("file,views\n" + "".join(f"{n},{v}\n" for n, _, v in clips), "utf-8")
    print("Demo clips are in library/demo_rival/. Remove them later with: python radar.py forget demo_rival")
    a.whisper, a.gpu, a.ollama, a.ollama_host, a.allow_remote_ai, a.scene, a.no_ocr = "tiny", False, None, "", False, 0.3, True
    a.port = 8765
    cmd_watch(a)


def main():
    ap = argparse.ArgumentParser(description="📡 Reel Radar: local creator intelligence (Made by Harsh Rajput)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ini = sub.add_parser("init", help="set niche, platforms, handles, competitors")
    ini.add_argument("--niche"); ini.add_argument("--language"); ini.add_argument("--platforms")
    sub.add_parser("doctor", help="check that everything is installed, with one-line fixes")
    dm = sub.add_parser("demo", help="15-second demo with sample clips (dashboard + playbook)")
    dm.add_argument("--no-dashboard", action="store_true")
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
    cu = sub.add_parser("check-url", help="(used by Claude) Guard approval before opening a page")
    cu.add_argument("url")
    fg = sub.add_parser("forget", help="delete analysis data for one creator or everything")
    fg.add_argument("creator", nargs="?"); fg.add_argument("--all", action="store_true"); fg.add_argument("--yes", action="store_true")
    ob = sub.add_parser("observe", help="(used by Claude) log a live, view-only browser observation")
    for x in ("--url", "--creator"):
        ob.add_argument(x, required=True)
    for x in ("--platform", "--hook", "--text-hook", "--visual", "--views", "--notes", "--transcript"):
        ob.add_argument(x, default="")
    ob.add_argument("--mine", action="store_true", help="this reel is yours (for You vs Them)")
    he = sub.add_parser("hear", help="(optional, off by default) hear an Instagram reel via your speakers -> text only")
    he.add_argument("toggle", nargs="?", choices=["on", "off"]); he.add_argument("--url")
    he.add_argument("--seconds", type=float, default=75); he.add_argument("--model", default="small")
    he.add_argument("--language"); he.add_argument("--gpu", action="store_true")
    rt = sub.add_parser("retention", help="import a YouTube Studio audience-retention export (CSV/ZIP)")
    rt.add_argument("export"); rt.add_argument("--video", help="the video it belongs to, e.g. library/me/my_video.mp4")
    rt.add_argument("--creator", default="me"); rt.add_argument("--duration", type=float, help="video length in seconds")
    th = sub.add_parser("thumbs", help="score thumbnails in library/<creator>/thumbnails/ (yours vs competitors)")
    th.add_argument("files", nargs="*")
    sub.add_parser("scout", help="find competitors (YouTube API key or Claude)")
    sg = sub.add_parser("suggest", help="(used by Claude) add a competitor suggestion")
    sg.add_argument("--name", required=True); sg.add_argument("--platform", default="unknown")
    sg.add_argument("--handle", default=""); sg.add_argument("--why", default="")
    apv = sub.add_parser("approve", help="approve a suggested competitor"); apv.add_argument("name")
    sub.add_parser("stats-template", help="create stats.csv rows to fill in views")
    for c, h in (("report", "rebuild playbook"), ("patterns", "what winners do"), ("trends", "rising words in your niche"),
                 ("ideas", "video ideas from pasted comments"), ("audit", "security audit: PASS or FAIL"),
                 ("weekly", "everything in one weekly report")):
        sub.add_parser(c, help=h)
    cn = sub.add_parser("connect", help="install the AI team into Claude as skills")
    cn.add_argument("--to", help="skills folder (default ~/.claude/skills)")
    d = sub.add_parser("dashboard", help="open the live dashboard"); d.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()

    if a.cmd == "init": profile.init(a.niche, a.language, a.platforms)
    elif a.cmd == "doctor": sys.exit(0 if cmd_doctor() else 1)
    elif a.cmd == "demo": cmd_demo(a)
    elif a.cmd == "watch": cmd_watch(a)
    elif a.cmd == "precheck": cmd_precheck(a)
    elif a.cmd == "originality": cmd_originality(a)
    elif a.cmd == "brief": print("Brief saved:", mastermind.brief(OUT, a.topic))
    elif a.cmd == "observe": cmd_observe(a)
    elif a.cmd == "check-url": cmd_check_url(a)
    elif a.cmd == "forget":
        if not a.all and not a.creator:
            sys.exit("Say which creator, or --all")
        cmd_forget(a)
    elif a.cmd == "hear": cmd_hear(a)
    elif a.cmd == "retention": cmd_retention(a)
    elif a.cmd == "thumbs": cmd_thumbs(a)
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


def friendly(e):
    if isinstance(e, ModuleNotFoundError):
        return f"A part of Reel Radar is missing ({e.name}). Fix: run the installer again (INSTALL_WINDOWS.bat / INSTALL_MAC.command)."
    if isinstance(e, PermissionError):
        return f"Can't open {e.filename}: close it in other programs (or check folder permissions) and try again."
    if isinstance(e, FileNotFoundError):
        return f"File not found: {e.filename}. Check the name and that it's inside library/."
    if isinstance(e, MemoryError):
        return "Not enough memory. Close other apps or use --whisper base."
    return f"{type(e).__name__}: {e}"


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:                      # no raw tracebacks for beginners; full details go to a log
        import traceback
        OUT.mkdir(exist_ok=True)
        (OUT / "error.log").write_text(traceback.format_exc(), "utf-8")
        sys.exit(f"[!] {friendly(e)}\n    Details: out/error.log · Health check: python radar.py doctor")
