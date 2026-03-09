import argparse
import time
import re
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def seasons_last_n(n):
    today = datetime.today()
    if today.month < 10:
        end = today.year - 1
    else:
        end = today.year
    seasons = []
    for i in range(n):
        s = end - i
        seasons.append(f"{s}-{s+1}")
    return list(reversed(seasons))

def normalize(text):
    return (text or "").strip().replace("\xa0", " ")

def extract_match_id_from_row(tr):
    for a in tr.select("a[href]"):
        href = a.get("href") or ""
        m = re.search(r"matchid=(\d+)", href, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"/analysis/(\d+)\.htm", href, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"/oddslist/(\d+)\.htm", href, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""

def parse_sche_tab(html, season, match_type, year):
    soup = BeautifulSoup(html, "lxml")
    tab = soup.select_one("table#scheTab")
    if tab is None:
        return []
    trs = tab.select("tr")
    if not trs:
        return []
    header_tr = None
    for tr in trs[:5]:
        if "主队" in tr.get_text() and "客队" in tr.get_text():
            header_tr = tr
            break
    if header_tr is None:
        header_tr = trs[0]
    headers = [normalize(td.get_text()) for td in header_tr.find_all(["th", "td"])]
    idx = {}
    for i, h in enumerate(headers):
        if h in ["时间", "Time"]:
            idx["time"] = i
        elif h in ["主队", "主场", "Home"]:
            idx["home"] = i
        elif h in ["客队", "客场", "Away"]:
            idx["away"] = i
        elif h in ["比分", "全场", "Score"]:
            idx["score"] = i
        elif h in ["让分", "盘口", "Spread", "Handicap"]:
            idx["handicap"] = i
        elif h in ["总分", "大小", "Total", "O/U"]:
            idx["total"] = i
        elif h in ["半场", "Half"]:
            idx["halftime"] = i
    required = {"home", "away", "score"}
    if not required.issubset(idx.keys()):
        return []
    records = []
    current_date = ""
    started = False
    for tr in trs:
        if tr == header_tr:
            started = True
            continue
        if not started:
            continue
        tds = tr.find_all("td")
        if not tds:
            continue
        if len(tds) == 1 or (tds[0].get("colspan") is not None):
            text = normalize(tr.get_text())
            m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
            if m:
                current_date = m.group(1)
            continue
        if len(tds) < max(idx.values()) + 1:
            continue
        def cell(k):
            i = idx.get(k)
            if i is None:
                return ""
            return normalize(tds[i].get_text())
        match_id = extract_match_id_from_row(tr)
        time_text = cell("time")
        date_text = current_date
        if not date_text:
            m = re.search(r"(20\d{2}-\d{2}-\d{2})", time_text)
            if m:
                date_text = m.group(1)
        if not date_text:
            m = re.search(r"(\d{2})-(\d{2})", time_text)
            if m and year:
                date_text = f"{year}-{m.group(1)}-{m.group(2)}"
        records.append({
            "season": season,
            "match_type": match_type,
            "date": date_text,
            "time": time_text,
            "home_team": cell("home"),
            "away_team": cell("away"),
            "score": cell("score"),
            "handicap": cell("handicap"),
            "total": cell("total"),
            "halftime": cell("halftime"),
            "_match_id": match_id,
        })
    return records

def get_month_cells(page):
    cells = page.locator("table[id^='yearmonthTable'] td[year]")
    res = []
    seen = set()
    for i in range(cells.count()):
        td = cells.nth(i)
        month = normalize(td.inner_text())
        if not re.fullmatch(r"\d{1,2}", month):
            continue
        year = td.get_attribute("year") or ""
        key = (year, month)
        if key in seen:
            continue
        seen.add(key)
        res.append({"year": year, "month": month})
    return res

def click_match_kind(page, kind_id):
    page.locator(f"#matchKindList li#{kind_id}").click()
    try:
        page.wait_for_selector("#scheTab", state="attached", timeout=60000)
    except:
        pass
    page.wait_for_timeout(800)

def click_month(page, year, month):
    locs = page.locator(f"table[id^='yearmonthTable'] td[year='{year}']", has_text=month)
    clicked = False
    for i in range(locs.count()):
        td = locs.nth(i)
        if td.get_attribute("onclick"):
            td.click(timeout=10000)
            clicked = True
            break
    try:
        page.wait_for_selector("#scheTab", state="attached", timeout=60000)
    except:
        pass
    if clicked:
        page.wait_for_timeout(800)

def click_playoffs_option(page, onclick_value):
    page.locator(f"[onclick='{onclick_value}']").first.click()
    try:
        page.wait_for_selector("#scheTab", state="attached", timeout=60000)
    except:
        pass
    page.wait_for_timeout(800)

def scrape_season(page, season):
    url = f"https://nba.titan007.com/cn/normal.aspx?SclassID=1&MatchSeason={season}"
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(800)
    kinds = [("menu3", "季前赛"), ("menu1", "常规赛"), ("menu2", "季后赛")]
    all_records = []
    for kind_id, kind_name in kinds:
        click_match_kind(page, kind_id)
        if kind_id == "menu2":
            all_records.extend(parse_sche_tab(page.content(), season, kind_name, ""))
            opts = page.locator("[onclick^='changePlayoffs']")
            onclicks = []
            for i in range(opts.count()):
                v = opts.nth(i).get_attribute("onclick") or ""
                if v and v not in onclicks:
                    onclicks.append(v)
            for v in onclicks:
                click_playoffs_option(page, v)
                all_records.extend(parse_sche_tab(page.content(), season, kind_name, ""))
                time.sleep(0.4)
        else:
            months = get_month_cells(page)
            if not months:
                all_records.extend(parse_sche_tab(page.content(), season, kind_name, ""))
            for m in months:
                click_month(page, m["year"], m["month"])
                all_records.extend(parse_sche_tab(page.content(), season, kind_name, m["year"]))
                time.sleep(0.4)
    return all_records

def scrape_seasons(output, seasons):
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    all_records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        for s in seasons:
            print(f"抓取赛季: {s}")
            recs = scrape_season(page, s)
            print(f"赛季{s}解析到{len(recs)}场")
            all_records.extend(recs)
            time.sleep(1)
        browser.close()
    df = pd.DataFrame(all_records)
    if not df.empty:
        if "_match_id" in df.columns:
            df = df.sort_values(["season", "match_type", "date", "time"])
            non_empty = df[df["_match_id"] != ""].drop_duplicates(subset=["_match_id"], keep="first")
            empty = df[df["_match_id"] == ""].drop_duplicates(
                subset=["season", "match_type", "date", "time", "home_team", "away_team", "score"],
                keep="first",
            )
            df = pd.concat([non_empty, empty], ignore_index=True)
        df = df.drop(columns=[c for c in ["_match_id"] if c in df.columns])
    df.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"已输出CSV: {output} 共{len(df)}行")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="titan007_nba_5y.csv")
    parser.add_argument("--seasons", type=int, default=5)
    parser.add_argument("--season", default="")
    args = parser.parse_args()
    seasons = [args.season] if args.season else seasons_last_n(args.seasons)
    scrape_seasons(args.output, seasons)

if __name__ == "__main__":
    main()
