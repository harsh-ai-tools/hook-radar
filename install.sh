#!/usr/bin/env bash
# Reel Radar installer for macOS / Linux (made by Harsh Rajput)
set -e
cd "$(dirname "$0")"
echo "== Reel Radar installer: free and local, nothing is uploaded =="
command -v python3 >/dev/null || { echo "Please install Python 3.10-3.13 first."; exit 1; }
if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg not found."
  if command -v brew >/dev/null; then read -p "Install with Homebrew? [y/N] " y; [ "$y" = y ] && brew install ffmpeg
  elif command -v apt >/dev/null; then read -p "Install with apt (needs sudo)? [y/N] " y; [ "$y" = y ] && sudo apt install -y ffmpeg
  else echo "Install ffmpeg, then run again."; exit 1; fi
fi
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python radar.py connect
cat > reel-radar.sh <<'X'
#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f radar.json ] || .venv/bin/python radar.py init
.venv/bin/python radar.py watch "$@"
X
chmod +x reel-radar.sh
echo "Done! Run ./reel-radar.sh to start."
