#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$DIR/benchmark/compatibility/validate_stack.py"
python3 "$DIR/benchmark/compatibility/validate_optimizations.py"
python3 "$DIR/benchmark/monitoring/audit_logs.py"
