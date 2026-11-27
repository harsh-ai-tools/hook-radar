"""Reel Radar Security Hook: blocks unsafe tool calls inside a Reel Radar folder. Runs locally, 0 tokens.
Exit 2 = blocked (Claude sees the reason). Outside a Reel Radar folder it does nothing."""
import json, os, re, sys
from pathlib import Path
from urllib.parse import urlparse

DOWNLOADERS = re.compile(r"\b(yt-dlp|youtube-dl|gallery-dl|instaloader|you-get|streamlink)\b"
                         r"|\b(curl|wget|ffmpeg)\b[^|;&]*(youtube\.com|youtu\.be|instagram\.com)", re.I)


def main():
    try:
        raw = sys.stdin.buffer.read()
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "ignore")
        d = json.loads(text.strip("\x00 \r\n"))
        root = Path(d.get("cwd") or ".")
        if not (root / "reel_radar" / "guard.py").is_file():
            return 0
        sys.path.insert(0, str(root))
        from reel_radar import guard
        i = d.get("tool_input") or {}
        if d.get("tool_name") == "Bash":
            if DOWNLOADERS.search(i.get("command", "")):
                guard.check_action("download")
                return block("Reel Radar is view-only: downloading videos is blocked. Use videos already in library/.")
            return 0
        url = str(i.get("url") or "")
        if not url.startswith("http") or urlparse(url).hostname in guard.LOCAL_HOSTS:
            return 0
        ok, why = guard.check_url(url)
        return 0 if ok else block(f"Security Guard blocked {url}: {why}")
    except Exception as e:
        if os.environ.get("RR_HOOK_DEBUG"):
            print(f"hook error: {e!r}", file=sys.stderr)
        return 0          # never break Claude because of the hook itself


def block(msg):
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
