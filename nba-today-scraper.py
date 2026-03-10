import argparse
import csv
import os
import re
import time
from datetime import datetime, timedelta

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from zoneinfo import ZoneInfo

# 中文队名 -> 英文缩写
TEAM_MAP = {
    "丹佛掘金": "DEN",
    "洛杉矶湖人": "LAL",
    "金州勇士": "GSW",
    "菲尼克斯太阳": "PHX",
    "明尼苏达森林狼": "MIN",
    "达拉斯独行侠": "DAL",
    "俄克拉荷马城雷霆": "OKC",
    "费城76人": "PHI",
    "孟菲斯灰熊": "MEM",
    "洛杉矶快船": "LAC",
    "底特律活塞": "DET",
    "布鲁克林篮网": "BKN",
    "亚特兰大老鹰": "ATL",
    "密尔沃基雄鹿": "MIL",
    "犹他爵士": "UTA",
    "迈阿密热火": "MIA",
    "休斯顿火箭": "HOU",
    "纽约尼克斯": "NYK",
    "波士顿凯尔特人": "BOS",
    "新奥尔良鹈鹕": "NOP",
    "多伦多猛龙": "TOR",
    "华盛顿奇才": "WAS",
    "夏洛特黄蜂": "CHA",
    "圣安东尼奥马刺": "SAS",
    "萨克拉门托国王": "SAC",
    "芝加哥公牛": "CHI",
    "克里夫兰骑士": "CLE",
    "印第安纳步行者": "IND",
    "波特兰开拓者": "POR",
    "奥兰多魔术": "ORL",
}

def normalize(text):
    return (text or "").strip().replace("\xa0", " ")

def season_from_date(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if d.month >= 10:
        start = d.year
        end = d.year + 1
    else:
        start = d.year - 1
        end = d.year
    return f"{start}-{end}"

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

def parse_sche_tab(html, season, match_type, year_hint):
    soup = BeautifulSoup(html, "lxml")
    tab = soup.select_one("table#scheTab")
    if tab is None:
        return []
    trs = tab.select("tr")
    if not trs:
        return []
    header_tr = None
    for tr in trs[:8]:
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
            if m and year_hint:
                date_text = f"{year_hint}-{m.group(1)}-{m.group(2)}"
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

def click_match_kind(page, kind_id):
    try:
        page.wait_for_selector(f"#matchKindList li#{kind_id}", state="attached", timeout=15000)
    except:
        return False
    try:
        page.locator(f"#matchKindList li#{kind_id}").click(timeout=15000)
    except:
        return False
    try:
        page.wait_for_selector("#scheTab", state="attached", timeout=60000)
    except:
        pass
    page.wait_for_timeout(800)
    return True

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
        res.append({"year": year, "month": month, "onclick": td.get_attribute("onclick") or ""})
    return res

def click_month(page, year, month):
    locs = page.locator(f"table[id^='yearmonthTable'] td[year='{year}']", has_text=str(int(month)))
    for i in range(locs.count()):
        td = locs.nth(i)
        if td.get_attribute("onclick"):
            td.click(timeout=15000)
            try:
                page.wait_for_selector("#scheTab", state="attached", timeout=60000)
            except:
                pass
            page.wait_for_timeout(800)
            return True
    return False

def click_playoffs_option(page, onclick_value):
    page.locator(f"[onclick='{onclick_value}']").first.click()
    try:
        page.wait_for_selector("#scheTab", state="attached", timeout=60000)
    except:
        pass
    page.wait_for_timeout(800)

def detect_csv_encoding(file_path):
    with open(file_path, "rb") as f:
        head = f.read(4096)
    for enc in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            head.decode(enc)
            return enc
        except:
            continue
    return "utf-8"

def get_enriched_fieldnames(enriched_path):
    default_fields = [
        "season","match_type","date","time","home_team","away_team","score","handicap","total","halftime",
        "home_score","away_score","ats_diff","ats_result","total_score","ou_result","home_rest","away_rest","home_b2b","away_b2b",
    ]
    if not os.path.exists(enriched_path):
        return default_fields, "utf-8-sig"
    enc = detect_csv_encoding(enriched_path)
    with open(enriched_path, "r", encoding=enc, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    fields = [h.strip() for h in header if h.strip()]
    return (fields or default_fields), enc

def load_existing_keys_for_date(enriched_path, encoding, target_date):
    keys = set()
    if not os.path.exists(enriched_path):
        return keys
    with open(enriched_path, "r", encoding=encoding, newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("date") or "").strip() != target_date:
                continue
            date = (row.get("date") or "").strip()
            time_ = (row.get("time") or "").strip()
            home = (row.get("home_team") or "").strip()
            away = (row.get("away_team") or "").strip()
            keys.add((date, time_, home, away))
            keys.add((date, time_, TEAM_MAP.get(home, home), TEAM_MAP.get(away, away)))
    return keys

def normalize_time_only(s):
    t = (s or "").strip()
    if not t:
        return ""
    m = re.search(r"(\d{1,2}):(\d{2})", t)
    if not m:
        return t
    hh = int(m.group(1))
    mm = m.group(2)
    if "PM" in t.upper() and hh < 12:
        hh += 12
    if "AM" in t.upper() and hh == 12:
        hh = 0
    return f"{hh:02d}:{mm}"

def parse_date_ymd(value):
    s = (value or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        return None

def parse_float(value):
    s = (value or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except:
        return None

def parse_score(value):
    s = (value or "").strip()
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

def fmt_num(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    try:
        f = float(value)
    except:
        return str(value)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    s = f"{f:.4f}".rstrip("0").rstrip(".")
    return s

def append_to_enriched(enriched_path, df, target_date):
    fieldnames, encoding = get_enriched_fieldnames(enriched_path)
    existing_keys = load_existing_keys_for_date(enriched_path, encoding, target_date)
    new_rows = []
    for _, r in df.iterrows():
        key = (
            str(r.get("date", "")).strip(),
            str(r.get("time", "")).strip(),
            str(r.get("home_team", "")).strip(),
            str(r.get("away_team", "")).strip(),
        )
        if key in existing_keys:
            continue
        row = {}
        for i, col in enumerate(fieldnames):
            if i >= 10:
                row[col] = ""
            else:
                val = str(r.get(col, "") if col in df.columns else "").strip()
                if col == "time":
                    val = normalize_time_only(val)
                elif col == "home_team":
                    val = TEAM_MAP.get(val, val)
                elif col == "away_team":
                    val = TEAM_MAP.get(val, val)
                row[col] = val
        new_rows.append(row)
    file_exists = os.path.exists(enriched_path)
    mode = "a" if file_exists else "w"
    with open(enriched_path, mode, encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)
    return len(new_rows)

def backfill_enriched_columns(enriched_path, target_date):
    fieldnames, encoding = get_enriched_fieldnames(enriched_path)
    if not os.path.exists(enriched_path):
        return 0
    with open(enriched_path, "r", encoding=encoding, newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
    if not rows:
        return 0
    team_dates = {}
    target_indices = []
    for i, row in enumerate(rows):
        d = parse_date_ymd(row.get("date"))
        if d is None:
            continue
        home = (row.get("home_team") or "").strip()
        away = (row.get("away_team") or "").strip()
        if home:
            team_dates.setdefault(home, set()).add(d)
        if away:
            team_dates.setdefault(away, set()).add(d)
        if (row.get("date") or "").strip() == target_date:
            target_indices.append(i)
    team_dates_sorted = {t: sorted(ds) for t, ds in team_dates.items()}
    def previous_play_date(team, d):
        ds = team_dates_sorted.get(team)
        if not ds:
            return None
        lo = 0
        hi = len(ds)
        while lo < hi:
            mid = (lo + hi) // 2
            if ds[mid] < d:
                lo = mid + 1
            else:
                hi = mid
        j = lo - 1
        if j < 0:
            return None
        return ds[j]
    changed = 0
    for i in target_indices:
        row = rows[i]
        d = parse_date_ymd(row.get("date"))
        if d is None:
            continue
        home = (row.get("home_team") or "").strip()
        away = (row.get("away_team") or "").strip()
        def rest_days(team):
            prev = previous_play_date(team, d)
            if prev is None:
                return None
            delta = (d - prev).days - 1
            if delta < 0:
                return None
            return delta
        home_rest = rest_days(home) if home else None
        away_rest = rest_days(away) if away else None
        home_b2b = 1 if home_rest == 0 else 0 if home_rest is not None else None
        away_b2b = 1 if away_rest == 0 else 0 if away_rest is not None else None
        score = parse_score(row.get("score"))
        handicap = parse_float(row.get("handicap"))
        total_line = parse_float(row.get("total"))
        home_score = None
        away_score = None
        total_score = None
        if score is not None:
            home_score, away_score = score
            total_score = home_score + away_score
        ats_diff = None
        ats_result = ""
        if score is not None and handicap is not None:
            ats_diff = (home_score - away_score) + handicap
            if abs(ats_diff) < 1e-9:
                ats_result = "Push"
            elif ats_diff > 0:
                ats_result = "Home Win"
            else:
                ats_result = "Away Win"
        ou_result = ""
        if score is not None and total_line is not None:
            diff = total_score - total_line
            if abs(diff) < 1e-9:
                ou_result = "Push"
            elif diff > 0:
                ou_result = "Over"
            else:
                ou_result = "Under"
        before = dict(row)
        if not (row.get("home_score") or "").strip() and score is not None:
            row["home_score"] = fmt_num(home_score)
        if not (row.get("away_score") or "").strip() and score is not None:
            row["away_score"] = fmt_num(away_score)
        if not (row.get("total_score") or "").strip() and score is not None:
            row["total_score"] = fmt_num(total_score)
        if not (row.get("ats_diff") or "").strip() and ats_diff is not None:
            row["ats_diff"] = fmt_num(ats_diff)
        if not (row.get("ats_result") or "").strip() and ats_result:
            row["ats_result"] = ats_result
        if not (row.get("ou_result") or "").strip() and ou_result:
            row["ou_result"] = ou_result
        if not (row.get("home_rest") or "").strip() and home_rest is not None:
            row["home_rest"] = fmt_num(home_rest)
        if not (row.get("away_rest") or "").strip() and away_rest is not None:
            row["away_rest"] = fmt_num(away_rest)
        if not (row.get("home_b2b") or "").strip() and home_b2b is not None:
            row["home_b2b"] = fmt_num(home_b2b)
        if not (row.get("away_b2b") or "").strip() and away_b2b is not None:
            row["away_b2b"] = fmt_num(away_b2b)
        if row != before:
            changed += 1
    with open(enriched_path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return changed

def fix_time_column_only(enriched_path):
    fieldnames, encoding = get_enriched_fieldnames(enriched_path)
    if not os.path.exists(enriched_path):
        return 0
    with open(enriched_path, "r", encoding=encoding, newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
    changed = 0
    for row in rows:
        before = row.get("time", "")
        after = normalize_time_only(before)
        if after != before:
            row["time"] = after
            changed += 1
    with open(enriched_path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return changed

def scrape_today(output_path, enriched_path, target_date=None):
    if target_date is None:
        target_date = datetime.today().strftime("%Y-%m-%d")  # 北京日期
    us_date_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    season = season_from_date(target_date)
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    month_year = str(target_dt.year)
    month_num = str(target_dt.month)
    playoffs_year_hint = season.split("-")[1]

    url = f"https://nba.titan007.com/cn/normal.aspx?SclassID=1&MatchSeason={season}"
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    all_records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(800)
        kinds = [("menu3", "季前赛"), ("menu1", "常规赛"), ("menu2", "季后赛")]
        for kind_id, kind_name in kinds:
            if not click_match_kind(page, kind_id):
                continue
            if kind_id == "menu2":
                all_records.extend(parse_sche_tab(page.content(), season, kind_name, playoffs_year_hint))
                opts = page.locator("[onclick^='changePlayoffs']")
                onclicks = []
                for i in range(opts.count()):
                    v = opts.nth(i).get_attribute("onclick") or ""
                    if v and v not in onclicks:
                        onclicks.append(v)
                for v in onclicks:
                    click_playoffs_option(page, v)
                    all_records.extend(parse_sche_tab(page.content(), season, kind_name, playoffs_year_hint))
                    time.sleep(0.2)
            else:
                months = get_month_cells(page)
                matched = False
                for m in months:
                    if m["year"] == month_year and str(int(m["month"])) == str(int(month_num)):
                        matched = click_month(page, m["year"], m["month"])
                        break
                if not matched:
                    all_records.extend(parse_sche_tab(page.content(), season, kind_name, month_year))
                else:
                    all_records.extend(parse_sche_tab(page.content(), season, kind_name, month_year))
                time.sleep(0.2)
        browser.close()

    df = pd.DataFrame(all_records)
    if df.empty:
        df = pd.DataFrame(columns=["season","match_type","date","time","home_team","away_team","score","handicap","total","halftime"])
    else:
        df = df[df["date"] == target_date].copy()
        # 转换到美东时间并映射队名
        cn_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        sh_tz = ZoneInfo("Asia/Shanghai")
        et_tz = ZoneInfo("America/New_York")
        new_dates = []
        new_times = []
        new_home = []
        new_away = []
        for _, r in df.iterrows():
            raw_time = str(r.get("time", "")).strip()
            hhmm = normalize_time_only(raw_time)
            try:
                dt_cn = datetime.strptime(f"{cn_date} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=sh_tz)
                dt_us = dt_cn.astimezone(et_tz)
                new_dates.append(dt_us.strftime("%Y-%m-%d"))
                new_times.append(dt_us.strftime("%H:%M"))
            except:
                new_dates.append(us_date_str)
                new_times.append(hhmm)
            h = str(r.get("home_team", "")).strip()
            a = str(r.get("away_team", "")).strip()
            new_home.append(TEAM_MAP.get(h, h))
            new_away.append(TEAM_MAP.get(a, a))
        df["date"] = new_dates
        df["time"] = new_times
        df["home_team"] = new_home
        df["away_team"] = new_away
        # 仅保留美东“今天”的记录
        df = df[df["date"] == us_date_str].copy()

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    appended = append_to_enriched(enriched_path, df, us_date_str)
    from_this_day = backfill_enriched_columns(enriched_path, us_date_str)
    normalized = fix_time_column_only(enriched_path)
    print(f"抓取北京日期: {target_date} -> 美东日期: {us_date_str}")
    print(f"赛季: {season}")
    print(f"已输出CSV: {output_path} 共{len(df)}行")
    print(f"已追加到: {enriched_path} 新增{appended}行")
    print(f"已回填字段: {enriched_path} 更新{from_this_day}行")
    print(f"已规范time为HH:MM: {enriched_path} 更新{normalized}行")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="")
    parser.add_argument("--enriched", default="nba_enriched_data.csv")
    parser.add_argument("--date", default="")
    parser.add_argument("--fix_time_only", action="store_true")
    args = parser.parse_args()
    target_date = args.date or None
    us_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    out_dir = "daily matches"
    os.makedirs(out_dir, exist_ok=True)
    if args.output:
        if os.path.isabs(args.output) or os.path.dirname(args.output):
            output = args.output
        else:
            output = os.path.join(out_dir, args.output)
    else:
        output = os.path.join(out_dir, f"titan007_nba_{us_today}.csv")
    if args.fix_time_only:
        cnt = fix_time_column_only(args.enriched)
        print(f"已规范time为HH:MM: {args.enriched} 更新{cnt}行")
        return
    scrape_today(output_path=output, enriched_path=args.enriched, target_date=target_date)

if __name__ == "__main__":
    main()
