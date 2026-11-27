#!/usr/bin/env bash
# HookRadar installer for macOS / Linux (made by Harsh Rajput)
set -e
cd "$(dirname "$0")"
echo "== HookRadar installer: free and local, nothing is uploaded =="
command -v python3 >/dev/null || { echo "Please install Python 3.10-3.13 first."; exit 1; }
python3 -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' \
  || { echo "HookRadar needs Python 3.10 to 3.13 (you have $(python3 -V))."; exit 1; }
if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg not found."
  if command -v brew >/dev/null; then read -p "Install with Homebrew? [y/N] " y; [ "$y" = y ] && brew install ffmpeg
  elif [ "$(uname)" = Darwin ]; then echo "Install Homebrew from https://brew.sh, then run this again (it installs ffmpeg)."; exit 1
  elif command -v apt >/dev/null; then read -p "Install with apt (needs sudo)? [y/N] " y; [ "$y" = y ] && sudo apt install -y ffmpeg
  else echo "Install ffmpeg, then run again."; exit 1; fi
  command -v ffmpeg >/dev/null || { echo "ffmpeg is still missing. Install it, then run again."; exit 1; }
fi
python3 -m venv .venv || { echo "Could not create a virtual environment (on Ubuntu/Debian: sudo apt install python3-venv)"; exit 1; }
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt
GPUFLAG=""
if command -v nvidia-smi >/dev/null && [ "$(uname)" = Linux ]; then
  if [ "$1" = "--gpu" ]; then y=y; else read -p "NVIDIA GPU found. Install GPU speed-up for speech-to-text (~1 GB)? [y/N] " y; fi
  if [ "$y" = y ] && .venv/bin/python -m pip install -r requirements-gpu.txt; then GPUFLAG=" --gpu"; fi
fi
.venv/bin/python radar.py connect
mkdir -p library/me
[ -n "$GPUFLAG" ] && echo gpu > .venv/gpu.flag || rm -f .venv/gpu.flag
.venv/bin/python radar.py doctor || true
echo "Done! Double-click START_DASHBOARD.command (Mac) or run ./START_DASHBOARD.command to start."
