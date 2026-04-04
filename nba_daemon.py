import subprocess
import time
import os

VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'bin', 'python')

def run_script(script_name):
    print(f"DEBUG: Running {script_name}...")
    subprocess.run([VENV_PYTHON, script_name], capture_output=True, text=True)

while True:
    try:
        # 抓取原始数据
        run_script("nba-daily-odds.py")
        run_script("nba-injury.py")
        run_script("nba-advanced-stats.py")
        
        # 数据入表
        run_script("sync_odds.py")
        
        # 数据分析/Enrich
        run_script("analyze.py")
        
        # 补全 rest 数据
        run_script("fill_rest_data.py")
            
        print("Cycle complete, sleeping 1 hour.")
        time.sleep(3600)
    except Exception as e:
        print(f"Fatal error in daemon loop: {e}")
        time.sleep(60)
