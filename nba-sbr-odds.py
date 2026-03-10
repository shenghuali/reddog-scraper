import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta


BASE = "https://www.sportsbookreview.com/betting-odds/nba-basketball/"

TEAM_CODE_MAP = {
    "BRK": "BKN",
    "CHO": "CHA",
    "PHO": "PHX",
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
}


def normalize_team(code):
    c = (code or "").strip().upper()
    return TEAM_CODE_MAP.get(c, c)


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def season_from_us_date(d):
    if d.month >= 10:
        return f"{d.year}-{d.year+1}"
    return f"{d.year-1}-{d.year}"


def default_season_ranges(seasons):
    today = datetime.utcnow().date()
    end_year = today.year + 1 if today.month >= 10 else today.year
    start_year = end_year - seasons
    ranges = []
    for y in range(start_year, end_year):
        ranges.append((date(y, 10, 1), date(y + 1, 7, 1)))
    return ranges


def extract_next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except:
        return None


def fetch_html(url, timeout=60, retries=3):
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise last_err


def fetch_odds_table(us_date, odds_type):
    params = {"date": us_date.strftime("%Y-%m-%d")}
    if odds_type == "pointspread":
        url = BASE + "pointspread/?" + urllib.parse.urlencode(params)
    elif odds_type == "totals":
        url = BASE + "totals/?" + urllib.parse.urlencode(params)
    else:
        url = BASE + "?" + urllib.parse.urlencode(params)

    html = fetch_html(url)
    data = extract_next_data(html)
    if not data:
        return []
    tables = data.get("props", {}).get("pageProps", {}).get("oddsTables") or []
    if not tables:
        return []
    model = tables[0].get("oddsTableModel") or {}
    rows = model.get("gameRows") or []
    return rows


def pick_book_view(views, preferred):
    for v in views:
        if (v.get("sportsbook") or "").lower() == preferred.lower():
            return v
    return views[0] if views else None


def parse_rows(rows, market, preferred_book):
    out = {}
    for r in rows:
        gv = r.get("gameView") or {}
        game_id = gv.get("gameId")
        if game_id is None:
            continue
        home = normalize_team(((gv.get("homeTeam") or {}).get("shortName")) or "")
        away = normalize_team(((gv.get("awayTeam") or {}).get("shortName")) or "")
        start_iso = gv.get("startDate") or ""
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        except:
            start_dt = None

        views = r.get("oddsViews") or []
        v = pick_book_view(views, preferred_book)
        if not v:
            continue
        opening = v.get("openingLine") or {}
        current = v.get("currentLine") or {}
        book = (v.get("sportsbook") or "").lower()

        if game_id not in out:
            out[game_id] = {
                "game_id": str(game_id),
                "season": season_from_us_date(start_dt.date()) if start_dt else "",
                "date": start_dt.date().strftime("%Y-%m-%d") if start_dt else "",
                "time_et": start_dt.strftime("%H:%M") if start_dt else "",
                "home": home,
                "away": away,
                "book": book,
                "open_spread": "",
                "close_spread": "",
                "open_total": "",
                "close_total": "",
            }
        else:
            if not out[game_id].get("book") and book:
                out[game_id]["book"] = book

        if market == "spread":
            os_ = opening.get("homeSpread")
            cs_ = current.get("homeSpread")
            out[game_id]["open_spread"] = "" if os_ is None else str(os_)
            out[game_id]["close_spread"] = "" if cs_ is None else str(cs_)
        elif market == "total":
            ot = opening.get("total")
            ct = current.get("total")
            out[game_id]["open_total"] = "" if ot is None else str(ot)
            out[game_id]["close_total"] = "" if ct is None else str(ct)
    return out


def merge_game_maps(a, b):
    out = dict(a)
    for k, v in b.items():
        if k not in out:
            out[k] = v
            continue
        for f in ["open_spread", "close_spread", "open_total", "close_total", "book", "season", "date", "time_et", "home", "away"]:
            if not out[k].get(f) and v.get(f):
                out[k][f] = v[f]
            if f in ["open_spread", "close_spread", "open_total", "close_total"] and v.get(f) != "":
                out[k][f] = v[f]
    return out


def write_csv(path, rows):
    fieldnames = [
        "season",
        "date",
        "time_et",
        "away",
        "home",
        "book",
        "open_spread",
        "close_spread",
        "open_total",
        "close_total",
        "game_id",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=5)
    ap.add_argument("--start", default="")
    ap.add_argument("--end", default="")
    ap.add_argument("--book", default="draftkings")
    ap.add_argument("--output", default="sbr_nba_open_close_5y.csv")
    args = ap.parse_args()

    if args.start and args.end:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()
        ranges = [(start, end)]
    else:
        ranges = default_season_ranges(args.seasons)

    all_games = {}
    total_days = sum((e - s).days + 1 for s, e in ranges)
    done_days = 0

    for s, e in ranges:
        for d in daterange(s, e):
            done_days += 1
            if done_days % 25 == 0:
                print(f"进度: {done_days}/{total_days} 日期 {d}")
            try:
                spread_rows = fetch_odds_table(d, "pointspread")
                total_rows = fetch_odds_table(d, "totals")
            except Exception:
                continue

            spread_map = parse_rows(spread_rows, "spread", args.book)
            total_map = parse_rows(total_rows, "total", args.book)
            day_map = merge_game_maps(spread_map, total_map)
            all_games = merge_game_maps(all_games, day_map)
            time.sleep(0.15)

    rows = list(all_games.values())
    rows.sort(key=lambda r: (r.get("date", ""), r.get("time_et", ""), r.get("away", ""), r.get("home", "")))
    write_csv(args.output, rows)
    print(f"已输出: {args.output} 共{len(rows)}行")


if __name__ == "__main__":
    main()

