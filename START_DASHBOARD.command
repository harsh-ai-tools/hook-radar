#!/usr/bin/env bash
# Double-click me to start HookRadar (Mac / Linux).
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run INSTALL_MAC.command first."; read -r; exit 1; }
[ -f radar.json ] || .venv/bin/python radar.py init
FLAG=""; [ -f .venv/gpu.flag ] && FLAG="--gpu"
.venv/bin/python radar.py watch $FLAG "$@"
