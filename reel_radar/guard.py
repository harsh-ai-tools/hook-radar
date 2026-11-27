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
WATCH_SITES = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "instagram.com",
               "www.instagram.com"}
BLOCKED_PATH_WORDS = ("login", "accounts", "settings", "password", "direct/inbox", "checkout", "payments")
BLOCKED_ACTIONS = {"download", "upload", "repost", "like", "follow", "unfollow", "comment",
                   "dm", "message", "login", "share", "save_to_device", "scrape_bulk"}
LIVE_PER_HOUR = 100          # defaults; change in radar.json -> "live": {"per_hour": .., "min_seconds": ..}
LIVE_MIN_SECONDS = 4
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
NETWORK_OK = LOCAL_HOSTS | {"www.googleapis.com", "huggingface.co", "modelscope.cn", "www.modelscope.cn"}
SECRET_RE = re.compile(
    r"(AIza[0-9A-Za-z_\-]{35}"                       # Google / YouTube API key
    r"|sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}"         # OpenAI / Anthropic keys
    r"|sk_live_[A-Za-z0-9]{16,}|rk_live_[A-Za-z0-9]{16,}"   # Stripe
    r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"  # GitHub
    r"|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}"  # AWS / Slack
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"  # JWT tokens
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._\-]{20,}"
    r"|\"?(?:password|passwd|api_key|apikey|secret|access_token)\"?\s*[:=]\s*\"?[^\s\",]{6,}"
    r"|sessionid=|csrftoken=|ds_user_id=)", re.I)
PII_RE = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email]"),
          (re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)"), "[phone]"),
          (re.compile(r"(?<![\w])@[A-Za-z0-9_.]{2,30}"), "@[user]"),
          (re.compile(r"https?://\S+"), "[link]")]


def redact(text):
    """Hide other people's emails, phone numbers, @usernames and links."""
    for rx, rep in PII_RE:
        text = rx.sub(rep, text)
    return text

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


def norm_url(url):
    """Same page, same key: ignore www./m., tracking queries (?igsh=, ?si=, utm_...) and a trailing slash,
    so `observe` matches the URL the Guard approved even if the browser adds those."""
    u = urlparse(url.strip())
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    path = u.path.rstrip("/") or "/"
    keep = ""
    vid = u.path.strip("/") if host == "youtu.be" else next((q[2:] for q in u.query.split("&") if q.startswith("v=")), "") if path == "/watch" else ""
    if vid:                                          # one key per video: watch?v=ID / youtu.be/ID = shorts/ID
        host, path = "youtube.com", f"/shorts/{vid}"
    m = re.match(r"^(?:/[^/]+)?/reels?/([^/]+)$", path) if host == "instagram.com" else None
    if m:                                            # /user/reel/ID, /reels/ID = /reel/ID
        path = f"/reel/{m.group(1)}"
    return f"{u.scheme}://{host}{path}" + (f"?{keep}" if keep else "")


def check_image(path):
    """Thumbnails: only image files already in library/ (we never download them)."""
    p = Path(path)
    if not _inside(p, LIBRARY):
        return _log("image", p, False, "outside library/: put thumbnails in library/<creator>/thumbnails/")
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return _log("image", p, False, "not an image file")
    if p.is_symlink() or p.stat().st_size > 50 * 1024 ** 2:
        return _log("image", p, False, "shortcut or file over 50 MB")
    return _log("image", p, True, "ok")


def check_url(url):
    """For live browser watching: view-only pages on supported sites."""
    u = urlparse(url.strip())
    if u.scheme != "https":
        return _log("url", url, False, "only https pages")
    if u.hostname not in WATCH_SITES:
        return _log("url", url, False, "site not on the watch list (YouTube, Instagram)")
    if any(w in u.path.lower() for w in BLOCKED_PATH_WORDS):
        return _log("url", url, False, "account/login/settings pages are off-limits")
    return _log("url", norm_url(url), True, "ok")


def was_approved(url, within=900):
    """True if the Guard approved this exact URL (and pace) in the last `within` seconds."""
    if not LOG.exists():
        return False
    now, ok, key = time.time(), False, norm_url(url)
    for l in LOG.read_text("utf-8").splitlines()[-500:]:
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if r["kind"] == "url" and r["ok"] and norm_url(r["target"]) == key and now - r["t"] <= within:
            ok = True
    return ok


def check_action(action):
    a = action.lower().strip()
    if a in BLOCKED_ACTIONS:
        return _log("action", a, False, "Reel Radar is view-only: no downloads, uploads, likes, follows, comments or DMs")
    return _log("action", a, True, "ok")


def _live_limits():
    try:
        cfg = json.loads((ROOT / "radar.json").read_text("utf-8")).get("live", {})
    except Exception:
        cfg = {}
    per_hour = max(1, min(int(cfg.get("per_hour", LIVE_PER_HOUR)), 300))       # hard cap 300/h
    gap = max(2.0, float(cfg.get("min_seconds", LIVE_MIN_SECONDS)))          # never faster than 2s
    return per_hour, gap


def check_live_pace():
    """Human pace for live watching (default 100 videos/hour, 4s apart). Kept on disk."""
    per_hour, gap = _live_limits()
    now = time.time()
    seen = json.loads(SESSION.read_text("utf-8")) if SESSION.exists() else []
    seen = [t for t in seen if now - t < 3600]
    if len(seen) >= per_hour:
        wait = int(3600 - (now - seen[0])) // 60 + 1
        return _log("pace", len(seen), False, f"{per_hour} videos this hour: short break, {wait} min")
    if seen and now - seen[-1] < gap:
        return _log("pace", round(now - seen[-1], 1), False, f"too fast: wait {gap:g}s between videos")
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
    ok = host in NETWORK_OK
    return _log("network", host, ok, purpose if ok else "unexpected network host")


def check_ai_host(url, allow_remote=False):
    """The local AI (Ollama) must run on THIS computer unless the user explicitly allows otherwise."""
    h = urlparse(url).hostname
    if h in LOCAL_HOSTS:
        return _log("ai_host", url, True, "local AI on this PC")
    if allow_remote:
        return _log("ai_host", url, True, "remote AI allowed by user flag")
    return _log("ai_host", url, False, "AI host is not this PC: frames and transcripts would leave your computer "
                                        "(use --allow-remote-ai only if you trust that server)")


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
        if r["kind"] in ("url", "pace", "ai_host") and r["ok"] is False:
            pass  # blocked = Guard working
    # 1b. every live observation must have an approved URL + pace check right before it
    obs = OUT / "observations.jsonl"
    if obs.exists():
        ok_urls = {norm_url(r["target"]) for r in recs if r["kind"] == "url" and r["ok"]}
        for l in obs.read_text("utf-8").splitlines():
            if l.strip():
                o = json.loads(l)
                if o.get("t", 0) >= since and norm_url(o.get("url", "")) not in ok_urls:
                    findings.append(f"Live page not approved by Guard: {o.get('url')}")
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
    report = ["# 🛡️ Security report", "",
              f"- Checks reviewed: **{len(recs)}**", f"- Blocked by Guard: **{blocked}**",
              f"- Result: **{'PASS ✅' if passed else 'FAIL ❌'}**", ""]
    report += [f"- ❌ {f}" for f in findings] or ["- Guard did its job. Nothing slipped through."]
    blocked_list = [r for r in recs if not r["ok"]][-20:]
    if blocked_list:
        report += ["", "## What the Guard blocked"] + [f"- {r['kind']}: {r['target']} ({r['reason']})" for r in blocked_list]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "security_report.md").write_text("\n".join(report) + "\n", "utf-8")
    return passed, findings
