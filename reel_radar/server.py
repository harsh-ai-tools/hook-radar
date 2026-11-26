"""Local-only dashboard server (127.0.0.1). Serves out/, the dashboard, and videos from library/ only."""
import mimetypes, threading, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path.cwd().resolve()
ALLOWED = [ROOT / "out", ROOT / "library"]
DASH = Path(__file__).with_name("dashboard.html")


def _inside(p, roots):
    try:
        rp = p.resolve()
    except OSError:
        return False
    return any(rp == r or r in rp.parents for r in roots)


class H(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send_file(self, p):
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
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
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print(f"Dashboard: {url}")
    if open_browser:
        webbrowser.open(url)
    return srv
