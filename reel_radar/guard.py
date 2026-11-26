"""
🛡️ Security Guard + 👮 Head of Security.

Guard: checks every action BEFORE it happens and logs the decision.
Head:  audits the Guard's log AFTER every run and fails the run if anything slipped.
Made by Harsh Rajput · MIT
"""
import json, re, time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "library"
OUT = ROOT / "out"
LOG = OUT / "security_log.jsonl"

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
MAX_VIDEO_BYTES = 2 * 1024 ** 3
WATCH_SITES = {"youtube.com", "www.youtube.com", "m.youtube.com", "instagram.com",
               "www.instagram.com", "tiktok.com", "www.tiktok.com"}
BLOCKED_PATH_WORDS = ("login", "accounts", "settings", "password", "direct/inbox", "checkout", "payments")
BLOCKED_ACTIONS = {"download", "upload", "repost", "like", "follow", "unfollow", "comment",
                   "dm", "message", "login", "share", "save_to_device", "scrape_bulk"}
LIVE_MAX_PER_SESSION = 30
LIVE_MIN_SECONDS = 8
SECRET_RE = re.compile(r"(AIza[0-9A-Za-z_\-]{35}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|"
                       r"\"password\"\s*:|sessionid=|csrftoken=)", re.I)

SESSION = OUT / "live_session.json"


def _log(kind, target, ok, reason):
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"t": round(time.time(), 2), "kind": kind, "target": str(target)[:300], "ok": ok, "reason": reason}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return ok, reason


def _inside(p, root):
    try:
        rp, rr = Path(p).resolve(), root.resolve()
        return rp == rr or rr in rp.parents
    except OSError:
        return False


# ------------------------------------------------------------------ Guard
def check_video(path):
    p = Path(path)
    if not _inside(p, LIBRARY):
        return _log("video", p, False, "outside library/: only videos already in your library are allowed")
    if p.suffix.lower() not in VIDEO_EXT:
        return _log("video", p, False, "not a video file")
    if p.is_symlink():
        return _log("video", p, False, "shortcuts/symlinks are not allowed")
    if p.stat().st_size > MAX_VIDEO_BYTES:
        return _log("video", p, False, "file over 2 GB")
    return _log("video", p, True, "ok")


def check_url(url):
    """For live browser watching: view-only pages on supported sites."""
    u = urlparse(url)
    if u.scheme != "https":
        return _log("url", url, False, "only https pages")
    if u.hostname not in WATCH_SITES:
        return _log("url", url, False, "site not on the watch list (YouTube, Instagram, TikTok)")
    if any(w in u.path.lower() for w in BLOCKED_PATH_WORDS):
        return _log("url", url, False, "account/login/settings pages are off-limits")
    return _log("url", url, True, "ok")


def check_action(action):
    a = action.lower().strip()
    if a in BLOCKED_ACTIONS:
        return _log("action", a, False, "Reel Radar is view-only: no downloads, uploads, likes, follows, comments or DMs")
    return _log("action", a, True, "ok")


def check_live_pace():
    """Human pace for live watching: max 30 videos per 3 hours, 8s apart (kept on disk)."""
    now = time.time()
    seen = json.loads(SESSION.read_text("utf-8")) if SESSION.exists() else []
    seen = [t for t in seen if now - t < 3 * 3600]
    if len(seen) >= LIVE_MAX_PER_SESSION:
        return _log("pace", len(seen), False, f"limit of {LIVE_MAX_PER_SESSION} videos per 3 hours reached: take a break")
    if seen and now - seen[-1] < LIVE_MIN_SECONDS:
        return _log("pace", round(now - seen[-1], 1), False, f"too fast: wait {LIVE_MIN_SECONDS}s between videos")
    OUT.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(seen + [now]), "utf-8")
    return _log("pace", len(seen) + 1, True, "ok")


def check_secrets(text, where):
    if SECRET_RE.search(text or ""):
        return _log("secret", where, False, "looks like a password/API key/cookie: not saved")
    return _log("secret", where, True, "ok")


def ngrams(text, n=5):
    w = re.findall(r"[a-z0-9ऀ-෿']+", (text or "").lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def check_originality(script, transcripts, limit=0.25):
    """Blocks scripts that copy a competitor word-for-word (5-word sequences)."""
    mine = ngrams(script)
    if not mine:
        return _log("originality", "script", True, "empty"), None
    worst, who = 0.0, None
    for name, t in transcripts.items():
        overlap = len(mine & ngrams(t)) / len(mine)
        if overlap > worst:
            worst, who = overlap, name
    ok = worst <= limit
    reason = "ok" if ok else f"{worst:.0%} copied from {who}: rewrite in your own words"
    return _log("originality", f"script vs {who}", ok, reason), round(worst, 3)


def log_network(host, purpose):
    local = host in ("127.0.0.1", "localhost", "::1")
    return _log("network", host, local or host in ("www.googleapis.com",),
                f"{purpose}" if local or host == "www.googleapis.com" else "unexpected network host")


# ------------------------------------------------------------------ Head of Security
def head_audit(since=0.0):
    """Reviews the Guard's log + the project state. Returns (passed, findings)."""
    findings = []
    recs = []
    if LOG.exists():
        recs = [json.loads(l) for l in LOG.read_text("utf-8").splitlines() if l.strip()]
    recs = [r for r in recs if r["t"] >= since]
    # 1. Guard must have checked every analysed video
    idx = OUT / "study_index.jsonl"
    checked = {Path(r["target"]).resolve() for r in recs if r["kind"] == "video" and r["ok"]}
    if idx.exists():
        for l in idx.read_text("utf-8").splitlines():
            if not l.strip():
                continue
            j = json.loads(l)
            if j.get("t", 0) >= since and Path(ROOT / j["file"]).resolve() not in checked:
                findings.append(f"Guard skipped a check: {j['file']}")
    # 2. No blocked action may have gone through
    for r in recs:
        if r["kind"] == "action" and r["ok"] and r["target"] in BLOCKED_ACTIONS:
            findings.append(f"Blocked action was allowed: {r['target']}")
        if r["kind"] == "network" and not r["ok"]:
            findings.append(f"Unexpected network use: {r['target']}")
    # 3. No video files outside library/ (we never download)
    for p in OUT.rglob("*"):
        if p.suffix.lower() in VIDEO_EXT:
            findings.append(f"Video file found outside library/: {p.relative_to(ROOT)}")
    # 4. No secrets in saved files
    for p in [ROOT / "radar.json", *OUT.glob("*.json"), *OUT.glob("*.md")]:
        if p.exists() and p.stat().st_size < 5_000_000 and SECRET_RE.search(p.read_text("utf-8", errors="ignore")):
            findings.append(f"Possible secret saved in {p.name}")
    blocked = sum(1 for r in recs if not r["ok"])
    passed = not findings
    report = ["# 👮 Head of Security report", "",
              f"- Checks reviewed: **{len(recs)}**", f"- Blocked by Guard: **{blocked}**",
              f"- Result: **{'PASS ✅' if passed else 'FAIL ❌'}**", ""]
    report += [f"- ❌ {f}" for f in findings] or ["- Guard did its job. Nothing slipped through."]
    blocked_list = [r for r in recs if not r["ok"]][-20:]
    if blocked_list:
        report += ["", "## What the Guard blocked"] + [f"- {r['kind']}: {r['target']} ({r['reason']})" for r in blocked_list]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "security_report.md").write_text("\n".join(report) + "\n", "utf-8")
    return passed, findings
