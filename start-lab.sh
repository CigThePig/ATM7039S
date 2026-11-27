#!/bin/sh
# ATM7039S hardware test lab (Linux/macOS). Run: ./start-lab.sh
cd "$(dirname "$0")" || exit 1
PYTHONUTF8=1 exec python3 tools/lab_launch.py "$@"
