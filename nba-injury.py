import sys; sys.path.insert(0, "/Users/shenghuali/.local/lib/python3.12/site-packages")
import csv
import re
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

CBS_TEAM_CODE_MAP = {
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
    "PHO": "PHX",
}

TEAM_MAP = {
    "Atlanta": "ATL",
    "Boston": "BOS",
    "Brooklyn": "BKN",
    "Charlotte": "CHA",
    "Chicago": "CHI",
    "Cleveland": "CLE",
    "Dallas": "DAL",
    "Denver": "DEN",
    "Detroit": "DET",
    "Golden State": "GSW",
    "Houston": "HOU",
    "Indiana": "IND",
    "LA Clippers": "LAC",
    "LA Lakers": "LAL",
    "Memphis": "MEM",
    "Miami": "MIA",
    "Milwaukee": "MIL",
    "Minnesota": "MIN",
    "New Orleans": "NOP",
    "New York": "NYK",
    "Oklahoma City": "OKC",
    "Orlando": "ORL",
    "Philadelphia": "PHI",
    "Phoenix": "PHX",
    "Portland": "POR",
    "Sacramento": "SAC",
    "San Antonio": "SAS",
    "Toronto": "TOR",
    "Utah": "UTA",
    "Washington": "WAS",
}

URL = "https://www.cbssports.com/nba/injuries/"

def norm(s):
    return (s or "").strip().replace("\xa0", " ")

def normalize_team_code(code):
    c = (code or "").strip().upper()
    if not c:
        return ""
    return CBS_TEAM_CODE_MAP.get(c, c)

def fetch_html():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    response = requests.get(URL, headers=headers)
    return response.text

def extract_team_code_from_wrapper(wrapper):
    for a in wrapper.select("a[href]"):
        href = a.get("href") or ""
        m = re.match(r"^/nba/teams/([A-Z]{2,3})/", href)
        if m:
            return normalize_team_code(m.group(1))
    name = wrapper.select_one("span.TeamName a")
    if name:
        return TEAM_MAP.get(norm(name.get_text()), "")
    return ""

def parse(html):
    soup = BeautifulSoup(html, "lxml")
    results = []
    for wrapper in soup.select("div.TableBaseWrapper"):
        table = wrapper.select_one("table.TableBase-table")
        if table is None:
            continue
        team = extract_team_code_from_wrapper(wrapper)
        if not team:
            continue
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            ptexts = [norm(x) for x in tds[0].stripped_strings]
            player = ptexts[-1] if ptexts else ""
            updated = norm(tds[2].get_text()) if len(tds) > 2 else ""
            injury = norm(tds[3].get_text()) if len(tds) > 3 else ""
            status = norm(tds[4].get_text()) if len(tds) > 4 else ""
            if not player:
                continue
            results.append({
                "team": team,
                "player": player,
                "updated": updated,
                "injury": injury,
                "status": status,
            })
    return results

def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["team", "player", "updated", "injury", "status"])
        for r in rows:
            writer.writerow([r["team"], r["player"], r["updated"], r["injury"], r["status"]])

def cleanup_old_files(out_dir, today_output_name):
    removed = []
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            if name == today_output_name:
                continue
            if name.startswith("nba-injury_") and name.endswith(".csv"):
                try:
                    os.remove(os.path.join(out_dir, name))
                    removed.append(os.path.join(out_dir, name))
                except:
                    pass
    for name in os.listdir("."):
        if name.startswith("nba-injury_") and name.endswith(".csv"):
            try:
                os.remove(name)
                removed.append(name)
            except:
                pass
    return removed

def main():
    us_date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    out_dir = "nba injury"
    os.makedirs(out_dir, exist_ok=True)
    output_name = f"nba-injury_{us_date}.csv"
    output_path = os.path.join(out_dir, output_name)
    latest_path = "nba-injury-latest.csv"
    html = fetch_html()
    rows = parse(html)
    write_csv(output_path, rows)
    write_csv(latest_path, rows)
    removed = cleanup_old_files(out_dir, output_name)
    print(f"已输出: {output_path} 共{len(rows)}行")
    print(f"已输出: {latest_path} 共{len(rows)}行")
    if removed:
        print(f"已删除旧文件: {len(removed)}个")

if __name__ == "__main__":
    main()