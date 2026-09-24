#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$DIR/benchmark/analysis/plot_charts.py"
python3 "$DIR/benchmark/analysis/plot_png_charts.py"
python3 "$DIR/benchmark/analysis/generate_reports.py"
python3 "$DIR/benchmark/analysis/generate_docx_reports.py"
