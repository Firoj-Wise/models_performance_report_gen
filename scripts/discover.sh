#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$DIR/benchmark/discovery/system_info.py"
python3 "$DIR/benchmark/discovery/inspect_images.py"
