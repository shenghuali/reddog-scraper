#!/usr/bin/env python3
"""SBR NBA赔率抓取 - requests版（提取 opener/bet365 的 spread、total 与 spread odds）"""
import csv
import json
import os
import re
from datetime import datetime, timedelta

import requests

# 按墨尔本本机时间决定抓取日期：
# - 晚上 6 点前：抓前一天（通常对应美国当天比赛日）
# - 晚上 6 点及以后：抓当天
override_date = os.environ.get("ODDS_DATE", "").strip()
if override_date:
    us_date = override_date
else:
    aus_now = datetime.now()
    if aus_now.hour >= 18:
        us_date = aus_now.strftime("%Y-%m-%d")
    else:
        us_date = (aus_now - timedelta(days=1)).strftime("%Y-%m-%d")

headers = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def load_game_rows(market: str):
    target_url = f"https://www.sportsbookreview.com/betting-odds/nba-basketball/{market}/full-game/?date={us_date}"
    print(f"Fetching: {target_url}")
    html = requests.get(target_url, headers=headers, timeout=30).text
    print(f"Got HTML: {len(html)} chars")

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, flags=re.S)
    if not match:
        raise Exception(f"Could not find __NEXT_DATA__ for {market}")

    data = json.loads(match.group(1))

    def find_game_rows(obj):
        if isinstance(obj, dict):
            if "gameRows" in obj:
                return obj["gameRows"]
            for v in obj.values():
                res = find_game_rows(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_game_rows(item)
                if res:
                    return res
        return []

    rows = find_game_rows(data)
    print(f"Found {len(rows)} games for {market}")
    return rows


spread_rows = load_game_rows("pointspread")
total_rows = load_game_rows("totals")

def get_sportsbook_name(odds_view):
    sportsbook = odds_view.get("sportsbook")
    if isinstance(sportsbook, dict):
        return (sportsbook.get("name") or "").lower()
    if isinstance(sportsbook, str):
        return sportsbook.lower()
    return ""


def normalize_total_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        cleaned = re.sub(r"^[OU]\s*", "", cleaned, flags=re.I)
        return cleaned
    return value


def format_wager_percent(value):
    if value is None:
        return ""
    return f"{round(value)}%"


def american_to_decimal(odds):
    if odds is None or odds == "":
        return None
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return None

    if odds > 0:
        decimal_odds = 1 + odds / 100
    elif odds < 0:
        decimal_odds = 1 + 100 / abs(odds)
    else:
        return None

    return f"{decimal_odds:.2f}"


def get_home_spread_lines(row):
    opener_spread = None
    bet365_spread = None
    home_spread_odds = None
    away_spread_odds = None

    for ov in row.get("oddsViews", []):
        sportsbook = get_sportsbook_name(ov)

        if opener_spread is None:
            opener_line = ov.get("openingLine") or {}
            opener_spread = opener_line.get("homeSpread")

        if sportsbook == "bet365":
            current_line = ov.get("currentLine") or {}
            bet365_spread = current_line.get("homeSpread")
            home_spread_odds = american_to_decimal(current_line.get("homeOdds"))
            away_spread_odds = american_to_decimal(current_line.get("awayOdds"))

        if opener_spread is not None and bet365_spread is not None and home_spread_odds is not None and away_spread_odds is not None:
            break

    return opener_spread, bet365_spread, home_spread_odds, away_spread_odds


def get_total_lines(row):
    opener_total = None
    bet365_total = None

    for ov in row.get("oddsViews", []):
        sportsbook = get_sportsbook_name(ov)

        if opener_total is None:
            opener_line = ov.get("openingLine") or {}
            opener_total = normalize_total_value(opener_line.get("total"))

        if sportsbook == "bet365":
            current_line = ov.get("currentLine") or {}
            bet365_total = normalize_total_value(current_line.get("total"))

        if opener_total is not None and bet365_total is not None:
            break

    return opener_total, bet365_total


total_map = {}
for r in total_rows:
    gv = r.get("gameView", {})
    game_id = gv.get("gameId")
    opener_total, bet365_total = get_total_lines(r)
    total_map[game_id] = (opener_total, bet365_total)

out = []
for r in spread_rows:
    gv = r.get("gameView", {})
    game_id = gv.get("gameId")
    ht = gv.get("homeTeam", {}).get("shortName", "")
    at = gv.get("awayTeam", {}).get("shortName", "")
    home_score = gv.get("homeTeamScore")
    away_score = gv.get("awayTeamScore")
    consensus = gv.get("consensus") or {}
    home_wager = consensus.get("homeSpreadPickPercent")
    away_wager = consensus.get("awaySpreadPickPercent")

    opener_spread, spread, home_spread_odds, away_spread_odds = get_home_spread_lines(r)

    opener_total, total = total_map.get(game_id, (None, None))

    out.append([
        game_id,
        ht,
        at,
        us_date,
        str(home_score) if home_score is not None else "",
        str(away_score) if away_score is not None else "",
        format_wager_percent(home_wager),
        format_wager_percent(away_wager),
        str(opener_spread) if opener_spread is not None else "",
        str(spread) if spread is not None else "",
        str(opener_total) if opener_total is not None else "",
        str(total) if total is not None else "",
        home_spread_odds or "",
        away_spread_odds or "",
    ])

# csv_path = "/Users/shenghuali/reddog-scraper/nba-latest-odds.csv"
csv_path = "/Users/shenghuali/reddog-scraper/nba-latest-odds.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["game_id", "home", "away", "date", "Home Score", "Away Score", "home wager", "away wager", "opener_spread", "spread", "opener_total", "total", "home_spread_odds", "away_spread_odds"])
    w.writerows(out)

print(f"\n✅ 抓取完成: {len(out)} 场比赛")
for row in out:
    home_score_str = row[4] if row[4] else ""
    away_score_str = row[5] if row[5] else ""
    home_wager_str = row[6] if row[6] else "N/A"
    away_wager_str = row[7] if row[7] else "N/A"
    opener_str = row[8] if row[8] else "N/A"
    spread_str = row[9] if row[9] else "N/A"
    opener_total_str = row[10] if row[10] else "N/A"
    total_str = row[11] if row[11] else "N/A"
    home_spread_odds_str = row[12] if row[12] else "N/A"
    away_spread_odds_str = row[13] if row[13] else "N/A"
    score_str = f"{away_score_str}-{home_score_str}" if home_score_str and away_score_str else "未开赛"
    print(
        f"  {row[2]} @ {row[1]}: score={score_str}, home_wager={home_wager_str}, away_wager={away_wager_str}, opener_spread={opener_str}, spread={spread_str}, "
        f"opener_total={opener_total_str}, total={total_str}, home_spread_odds={home_spread_odds_str}, away_spread_odds={away_spread_odds_str}"
    )
