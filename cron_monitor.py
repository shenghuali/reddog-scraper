import json
import os

STATUS_FILE = 'status.json'
JOBS_FILE = '/etc/cron.d/nba-jobs'

print("### NBA 爬虫流水线状态 ###")
if os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, 'r') as f:
        status = json.load(f)
        print(f"当前状态: {status.get('status')}")
        print(f"最后运行: {status.get('last_run', 'N/A')}")
        print(f"上次开始: {status.get('start_time', 'N/A')}")

print("\n### 调度队列 (Jobs) ###")
if os.path.exists(JOBS_FILE):
    with open(JOBS_FILE, 'r') as f:
        print(f.read())
