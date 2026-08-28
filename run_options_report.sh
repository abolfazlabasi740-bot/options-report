#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$HOME/options_report"
exec python3 -u options_pipeline.py
