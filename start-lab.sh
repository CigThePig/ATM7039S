#!/bin/sh
# ATM7039S hardware test lab (Linux). Run: ./start-lab.sh
# macOS: follow device/V3-STEP-BY-STEP.md instead.
cd "$(dirname "$0")" || exit 1
PYTHONUTF8=1 exec python3 tools/lab_launch.py "$@"
