#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="/data/reddog-scraper"
VENV_DIR="$BASE_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
LOG_DIR="$BASE_DIR/logs"
LOCK_FILE="/tmp/nba-daily-odds.lock"

mkdir -p "$LOG_DIR"
cd "$BASE_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Missing venv python at $PYTHON_BIN" >&2
  exit 1
fi

exec flock -n "$LOCK_FILE" "$PYTHON_BIN" "$BASE_DIR/nba-daily-odds.py" >> "$LOG_DIR/nba-daily-odds.log" 2>&1
