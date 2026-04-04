import csv
import os
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LATEST_ODDS_CSV = os.path.join(BASE_DIR, 'nba-latest-odds.csv')
INJURY_CSV = os.path.join(BASE_DIR, 'nba-injury-latest.csv')
ADVANCED_STATS_CSV = os.path.join(BASE_DIR, 'nba-advanced-stats.csv')
ROSTER_CSV = os.path.join(BASE_DIR, 'nba-roster.csv')

MEMOS_TOKEN = os.getenv('MEMOS_ACCESS_TOKEN', 'memos_pat_ElBqw9IlIZaYSG3jdmm6o1I8HrEsOSOU')
MEMOS_API_URL = 'http://memos:5230/api/v1/memos'

def post_to_memos(content, visibility="PUBLIC"):
    headers = {'Authorization': f'Bearer {MEMOS_TOKEN}', 'Content-Type': 'application/json'}
    data = {'content': content, 'visibility': visibility}
    try:
        r = requests.post(MEMOS_API_URL, headers=headers, json=data, timeout=10)
        return r.status_code
    except:
        return None

def get_data(path):
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def get_roster_core(team):
    roster = get_data(ROSTER_CSV)
    return [r['player'] for r in roster if r['team'] == team and r.get('core', '0') == '1']

def generate_picks():
    odds = get_data(LATEST_ODDS_CSV)
    adv_stats = get_data(ADVANCED_STATS_CSV)
    injury_data = get_data(INJURY_CSV)
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    picks_content = ""
    
    for game in odds:
        home, away = game.get('home'), game.get('away')
        spread = float(game.get('close_spread') or 0)
        
        h_stat = next((s for s in adv_stats if s['team'] == home), None)
        a_stat = next((s for s in adv_stats if s['team'] == away), None)
        
        if h_stat and a_stat:
            h_nrtg = float(h_stat['nrtg'])
            a_nrtg = float(a_stat['nrtg'])
            
            h_core = get_roster_core(home)
            a_core = get_roster_core(away)
            
            for inj in injury_data:
                if inj['team'] == home and inj['player'] in h_core and inj['status'] != 'Healthy':
                    h_nrtg -= 5
                if inj['team'] == away and inj['player'] in a_core and inj['status'] != 'Healthy':
                    a_nrtg -= 5
                    
            model_spread = (a_nrtg - h_nrtg) / 2.0
            edge = model_spread - spread
            
            rec = "⚖️ 双方实力均衡，无明显博弈价值。"
            if edge > 3: rec = f"🔮 庄家诱盘: 市场低估 {home} 净效率，推荐 {home} 赢盘。"
            elif edge < -3: rec = f"🔮 庄家诱盘: 市场高估 {home} 净效率，推荐 {away} 赢盘。"
            
            picks_content += f"**🏀 {away} @ {home}**\n💰 策略: {rec}\n📊 模型预期: {model_spread:.1f} | 市场盘: {spread}\n\n"

    if picks_content:
        final_content = f"🔥 **[红狗高阶智投] {timestamp} 伤病加权盘口分析** 🔥\n\n{picks_content}"
        post_to_memos(final_content, visibility="PUBLIC")
        print("Picks posted.")

if __name__ == "__main__":
    generate_picks()
