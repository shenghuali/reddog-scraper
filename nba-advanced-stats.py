import sys; sys.path.insert(0, "/Users/shenghuali/reddog-scraper/venv/lib/python3.11/site-packages")
import csv
import re
import urllib.request
from bs4 import BeautifulSoup, Comment

URL = "https://www.basketball-reference.com/leagues/NBA_2026.html"

TEAM_CODE_MAP = {
    "BRK": "BKN",
    "CHO": "CHA",
    "PHO": "PHX",
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
}

def normalize_team_code(code):
    c = (code or "").strip().upper()
    return TEAM_CODE_MAP.get(c, c)

def fetch_raw_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")

def extract_table_from_comments(soup, table_id):
    container = soup.select_one(f"#all_{table_id}")
    if container is not None:
        for c in container.find_all(string=lambda t: isinstance(t, Comment)):
            if table_id in c and "<table" in c:
                frag = BeautifulSoup(str(c), "lxml")
                t = frag.select_one(f"table#{table_id}")
                if t is not None:
                    return t
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if table_id in c and "<table" in c:
            frag = BeautifulSoup(str(c), "lxml")
            t = frag.select_one(f"table#{table_id}")
            if t is not None:
                return t
    return None

def get_table(html, table_id):
    soup = BeautifulSoup(html, "lxml")
    t = soup.select_one(f"table#{table_id}")
    if t is not None:
        return t
    t = extract_table_from_comments(soup, table_id)
    if t is not None:
        return t
    return None

def parse_advanced_team_stats(table):
    rows = []
    tbody = table.select_one("tbody")
    if tbody is None:
        return rows
    for tr in tbody.select("tr"):
        if "class" in tr.attrs and "thead" in tr.attrs["class"]:
            continue
        team_td = tr.select_one('td[data-stat="team"]')
        if team_td is None:
            continue
        a = team_td.select_one("a[href]")
        if a is None:
            continue
        href = a.get("href") or ""
        m = re.match(r"^/teams/([A-Z]{2,3})/", href)
        if not m:
            continue
        team = normalize_team_code(m.group(1))
        def cell(stat):
            el = tr.select_one(f'td[data-stat="{stat}"]')
            return el.get_text(strip=True) if el is not None else ""
        rows.append(
            {
                "team": team,
                "pace": cell("pace"),
                "ortg": cell("off_rtg"),
                "drtg": cell("def_rtg"),
                "nrtg": cell("net_rtg"),
                "o-eFG%": cell("efg_pct"),
                "o-TOV%": cell("tov_pct"),
                "o-ORB%": cell("orb_pct"),
                "o-FT/FGA": cell("ft_rate"),
                "d-eFG%": cell("opp_efg_pct"),
                "d-TOV%": cell("opp_tov_pct"),
                "d-DRB%": cell("drb_pct"),
                "d-FT/FGA": cell("opp_ft_rate"),
            }
        )
    return rows

def write_csv(path, rows):
    if not rows:
        return
    fieldnames = ["team", "pace", "ortg", "drtg", "nrtg", "o-eFG%", "o-TOV%", "o-ORB%", "o-FT/FGA", "d-eFG%", "d-TOV%", "d-DRB%", "d-FT/FGA"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    html = fetch_raw_html(URL)
    table = get_table(html, "advanced-team")
    if table is None:
        print("未找到 table: advanced-team")
        return
    rows = parse_advanced_team_stats(table)
    write_csv("/Users/shenghuali/reddog-scraper/nba-advanced-stats.csv", rows)
    print(f"已更新: nba-advanced-stats.csv 共{len(rows)}行")

if __name__ == "__main__":
    main()
