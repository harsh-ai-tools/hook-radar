#!/usr/bin/env bash
# Double-click me on a Mac. (First time: right-click > Open.)
cd "$(dirname "$0")"
bash install.sh "$@"
read -r -p "Press Enter to close this window..."
