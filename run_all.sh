#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="/data/reddog-scraper"
VENV_DIR="$BASE_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
LOG_DIR="$BASE_DIR/logs"
LOCK_FILE="/tmp/reddog-run-all.lock"

mkdir -p "$LOG_DIR"
cd "$BASE_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Missing venv python at $PYTHON_BIN" >&2
  exit 1
fi

exec flock -n "$LOCK_FILE" bash -lc '
  set -Eeuo pipefail
  "$0" "$1/nba-daily-odds.py"
  "$0" "$1/nba-injury.py"
  "$0" "$1/nba-advanced-stats.py"
  "$0" "$1/analyze.py"
  "$0" "$1/fill_rest_data.py"
' "$PYTHON_BIN" "$BASE_DIR" >> "$LOG_DIR/run_all.log" 2>&1
