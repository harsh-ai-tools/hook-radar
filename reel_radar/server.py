"""Local-only dashboard server (127.0.0.1). Serves out/, the dashboard, and videos from library/ only."""
import mimetypes, secrets, threading, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = [ROOT / "out", ROOT / "library"]
DASH = Path(__file__).with_name("dashboard.html")
TOKEN = secrets.token_urlsafe(18)      # new private key every time the dashboard starts
PORT = [8765]


def _inside(p, roots):
    try:
        rp = p.resolve()
    except OSError:
        return False
    return any(rp == r or r in rp.parents for r in roots)


class H(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def _send_file(self, p):
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        data = None
        for _ in range(10):
            try:
                data = p.read_bytes()
                break
            except OSError:          # file being replaced right now (Windows)
                import time; time.sleep(0.03)
        if data is None:
            return self.send_error(503, "busy, retry")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self, u):
        # 1) only this PC's address (stops DNS-rebinding tricks)
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"127.0.0.1:{PORT[0]}", f"localhost:{PORT[0]}"):
            return False, "bad host"
        # 2) no other website may read the dashboard
        if self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return False, "cross-site request blocked"
        # 3) private key: in the link once, then in a strict cookie
        cookie = self.headers.get("Cookie") or ""
        key = parse_qs(u.query).get("k", [""])[0]
        has_cookie = any(c.strip() == f"rr_k={TOKEN}" for c in cookie.split(";"))
        if secrets.compare_digest(key, TOKEN):
            return True, "key from link"            # always redirect so the key leaves the URL
        if has_cookie:
            return True, "ok"
        return False, "missing private key: open the link printed in the terminal"

    def do_GET(self):
        u = urlparse(self.path)
        ok, why = self._allowed(u)
        if not ok:
            return self.send_error(403, why)
        if why == "key from link":
            self.send_response(302)
            self.send_header("Set-Cookie", f"rr_k={TOKEN}; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Location", u.path or "/")
            self.end_headers()
            return
        if u.path in ("/", "/index.html"):
            return self._send_file(DASH)
        if u.path == "/file":
            p = Path(parse_qs(u.query).get("p", [""])[0])
            p = p if p.is_absolute() else ROOT / p
            if _inside(p, [ROOT / "library"]) and p.is_file():
                return self._send_file(p)
            return self.send_error(403, "Only videos inside library/ are served")
        p = ROOT / u.path.lstrip("/")
        if _inside(p, ALLOWED) and p.is_file():
            return self._send_file(p)
        self.send_error(404)


def start(port=8765, open_browser=True):
    for p in range(port, port + 20):                 # port busy? try the next one
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), H)
            port = p
            PORT[0] = p
            break
        except OSError:
            continue
    else:
        raise SystemExit("[!] No free port for the dashboard (8765-8784).")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/?k={TOKEN}"
    print(f"Dashboard (private link, don't share): {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    return srv
