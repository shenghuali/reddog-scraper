import csv
import os
import subprocess
import requests
from datetime import datetime

# Paths
BASE_DIR = '/data/reddog-scraper'
INJURY_CSV = os.path.join(BASE_DIR, 'nba-injury-latest.csv')
LOG_FILE = os.path.join(BASE_DIR, 'injury_changes.log')
DOTENV_PATH = '/home/node/.openclaw/workspace/.env'

def get_memos_config():
    config = {}
    if os.path.exists(DOTENV_PATH):
        with open(DOTENV_PATH, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    config[k] = v
    return config

def post_to_memos(content, visibility="PRIVATE"):
    cfg = get_memos_config()
    token = cfg.get('MEMOS_ACCESS_TOKEN')
    if not token:
        return
    url = 'http://localhost:5230/api/v1/memos'
    try:
        requests.post(url, 
                      headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                      json={'content': content, 'visibility': visibility},
                      timeout=5)
    except:
        pass

def get_injury_data():
    if not os.path.exists(INJURY_CSV):
        return []
    with open(INJURY_CSV, 'r', encoding='utf-8-sig') as f:
        return list(csv.reader(f))

def format_row(row):
    return f"{row[0]} | {row[1]} | {row[4]} ({row[3]})"

def track_changes():
    # 1. Capture old state
    old_rows = get_injury_data()
    old_map = { (r[0], r[1]): r for r in old_rows[1:] } if old_rows else {}

    # 2. Run the original scraper
    PYTHON_BIN = os.path.join(BASE_DIR, 'venv/bin/python')
    SCRIP_PATH = os.path.join(BASE_DIR, 'nba-injury.py')
    subprocess.run([PYTHON_BIN, SCRIP_PATH], cwd=BASE_DIR)

    # 3. Capture new state
    new_rows = get_injury_data()
    new_map = { (r[0], r[1]): r for r in new_rows[1:] } if new_rows else {}

    # 4. Compare
    changes = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check for new or changed
    for key, new_row in new_map.items():
        if key not in old_map:
            changes.append(f"[NEW] {format_row(new_row)}")
        else:
            old_row = old_map[key]
            if old_row[4] != new_row[4] or old_row[3] != new_row[3]:
                changes.append(f"[UPDATE] {key[0]} {key[1]}: {old_row[4]} -> {new_row[4]}")

    # Check for removals
    for key in old_map:
        if key not in new_map:
            changes.append(f"[CLEARED] {key[0]} {key[1]} is off the report")

    # 5. Log and Post
    if changes:
        log_entry = f"\n--- {timestamp} ---\n" + "\n".join(changes)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
        
        # Post to Memos as PUBLIC
        memo_content = f"# NBA 伤病名单更新 [{timestamp}]\n\n" + "\n".join([f"- {c}" for c in changes])
        post_to_memos(memo_content, visibility="PUBLIC")
        print(f"[{timestamp}] Posted {len(changes)} changes to Memos.")
    else:
        print(f"[{timestamp}] No injury changes detected.")

if __name__ == "__main__":
    track_changes()
