import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta


BASE = "https://www.sportsbookreview.com/betting-odds/nba-basketball/"

TEAM_CODE_MAP = {
    "BRK": "BKN",
    "BK": "BKN",
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

def season_from_us_date(d):
    if d.month >= 10:
        return f"{d.year}-{d.year+1}"
    return f"{d.year-1}-{d.year}"


def extract_next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except:
        return None


def fetch_html(url, timeout=60, retries=3, max_redirects=5):
    last_err = None
    for i in range(retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "close",
            }
            current_url = url
            for _ in range(max_redirects + 1):
                req = urllib.request.Request(current_url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        return resp.read().decode("utf-8", errors="replace")
                except urllib.error.HTTPError as e:
                    if e.code not in [301, 302, 303, 307, 308]:
                        raise
                    loc = e.headers.get("Location")
                    if not loc:
                        raise
                    current_url = urllib.parse.urljoin(current_url, loc)
            raise urllib.error.HTTPError(url, 310, "Too many redirects", None, None)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last_err = e
            backoff = 1.5 * (i + 1)
            if isinstance(e, urllib.error.HTTPError) and e.code in [429, 403, 503]:
                backoff = max(backoff, 8.0 * (i + 1))
            time.sleep(backoff)
    raise last_err


def fetch_odds_table(us_date, odds_type):
    params = {"date": us_date.strftime("%Y-%m-%d")}
    if odds_type == "pointspread":
        url = BASE + "pointspread/full-game/?" + urllib.parse.urlencode(params)
    elif odds_type == "totals":
        url = BASE + "totals/full-game/?" + urllib.parse.urlencode(params)
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
    return model.get("gameRows") or []


def fetch_odds_rows_and_html(us_date, odds_type):
    params = {"date": us_date.strftime("%Y-%m-%d")}
    if odds_type == "pointspread":
        url = BASE + "pointspread/full-game/?" + urllib.parse.urlencode(params)
    elif odds_type == "totals":
        url = BASE + "totals/full-game/?" + urllib.parse.urlencode(params)
    else:
        url = BASE + "?" + urllib.parse.urlencode(params)

    html = fetch_html(url)
    data = extract_next_data(html)
    if not data:
        return [], html
    tables = data.get("props", {}).get("pageProps", {}).get("oddsTables") or []
    if not tables:
        return [], html
    model = tables[0].get("oddsTableModel") or {}
    return model.get("gameRows") or [], html


def pick_book_view(views, preferred):
    for v in views:
        if (v.get("sportsbook") or "").lower() == preferred.lower():
            return v
    return views[0] if views else None


def extract_wager_pct_map(pointspread_html):
    if not pointspread_html:
        return {}
    pcts = {}
    q = '"'
    game_iter = list(re.finditer(r'data-horizontal-eid=' + re.escape(q) + r'(\d+)' + re.escape(q), pointspread_html))
    for idx, m in enumerate(game_iter):
        gid = m.group(1)
        start = m.start()
        end = game_iter[idx + 1].start() if idx + 1 < len(game_iter) else min(len(pointspread_html), start + 120000)
        chunk = pointspread_html[start:end]
        vals = re.findall(r'<span class="opener">(\d{1,3})%</span>', chunk)
        if len(vals) >= 2:
            pcts[gid] = (vals[0], vals[1])
    return pcts


def extract_score_map(pointspread_html):
    if not pointspread_html:
        return {}
    scores = {}
    q = '"'
    game_iter = list(re.finditer(r'data-horizontal-eid=' + re.escape(q) + r'(\d+)' + re.escape(q), pointspread_html))
    for idx, m in enumerate(game_iter):
        gid = m.group(1)
        start = m.start()
        end = game_iter[idx + 1].start() if idx + 1 < len(game_iter) else min(len(pointspread_html), start + 120000)
        chunk = pointspread_html[start:end]
        pos = chunk.find("GameRows_scores__")
        if pos < 0:
            continue
        window = chunk[pos : pos + 2500]
        nums = re.findall(r"<div>(\d{1,3})</div>", window)
        if len(nums) >= 2:
            away_score = nums[0]
            home_score = nums[1]
            scores[gid] = (home_score, away_score)
    return scores


def american_to_decimal_odds(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if "." in s:
        try:
            d = float(s)
            if d > 1:
                return f"{d:.2f}"
        except:
            return ""
    try:
        american = int(float(s))
    except:
        return ""
    if american == 0:
        return ""
    if american > 0:
        dec = 1.0 + (american / 100.0)
    else:
        dec = 1.0 + (100.0 / abs(american))
    return f"{dec:.2f}"


def parse_rows(rows, market, preferred_book, wager_pct_map=None, score_map=None):
    out = {}
    wager_pct_map = wager_pct_map or {}
    score_map = score_map or {}
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
            home_score, away_score = score_map.get(str(game_id), ("Not Played", "Not Played"))
            out[game_id] = {
                "game_id": str(game_id),
                "season": season_from_us_date(start_dt.date()) if start_dt else "",
                "date": start_dt.date().strftime("%Y-%m-%d") if start_dt else "",
                "time_et": start_dt.strftime("%H:%M") if start_dt else "",
                "home_score": home_score,
                "away_score": away_score,
                "home": home,
                "away": away,
                "book": book,
                "open_spread": "",
                "close_spread": "",
                "open_total": "",
                "close_total": "",
                "away_spread_odds": "",
                "home_spread_odds": "",
                "away_wagers_pct": "",
                "home_wagers_pct": "",
            }
        else:
            if not out[game_id].get("book") and book:
                out[game_id]["book"] = book
        if not out[game_id].get("away_wagers_pct") and not out[game_id].get("home_wagers_pct"):
            awp, hwp = wager_pct_map.get(str(game_id), ("", ""))
            out[game_id]["away_wagers_pct"] = awp or ""
            out[game_id]["home_wagers_pct"] = hwp or ""
        if (out[game_id].get("home_score") in ["", "Not Played"]) and (out[game_id].get("away_score") in ["", "Not Played"]):
            hs, aws = score_map.get(str(game_id), ("", ""))
            if hs and aws:
                out[game_id]["home_score"] = hs
                out[game_id]["away_score"] = aws

        if market == "spread":
            os_ = opening.get("homeSpread")
            cs_ = current.get("homeSpread")
            if os_ is None:
                away_os = opening.get("awaySpread")
                if isinstance(away_os, (int, float)):
                    os_ = -away_os
            if cs_ is None:
                away_cs = current.get("awaySpread")
                if isinstance(away_cs, (int, float)):
                    cs_ = -away_cs
            out[game_id]["open_spread"] = "" if os_ is None else str(os_)
            out[game_id]["close_spread"] = "" if cs_ is None else str(cs_)
            away_w = current.get("awayOdds")
            home_w = current.get("homeOdds")
            if away_w is None:
                away_w = opening.get("awayOdds")
            if home_w is None:
                home_w = opening.get("homeOdds")
            out[game_id]["away_spread_odds"] = american_to_decimal_odds(away_w)
            out[game_id]["home_spread_odds"] = american_to_decimal_odds(home_w)
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
        for f in [
            "home_score",
            "away_score",
            "open_spread",
            "close_spread",
            "open_total",
            "close_total",
            "home_spread_odds",
            "away_spread_odds",
            "home_wagers_pct",
            "away_wagers_pct",
            "book",
            "date",
            "time_et",
            "home",
            "away",
        ]:
            if not out[k].get(f) and v.get(f):
                out[k][f] = v[f]
            if f in [
                "home_score",
                "away_score",
                "open_spread",
                "close_spread",
                "open_total",
                "close_total",
                "home_spread_odds",
                "away_spread_odds",
                "home_wagers_pct",
                "away_wagers_pct",
            ] and v.get(f) != "":
                out[k][f] = v[f]
    return out


def write_csv(path, rows):
    fieldnames = [
        "season",
        "date",
        "time_et",
        "home_score",
        "away_score",
        "home",
        "away",
        "book",
        "open_spread",
        "close_spread",
        "open_total",
        "close_total",
        "home_spread_odds",
        "away_spread_odds",
        "home_wagers_pct",
        "away_wagers_pct",
        "game_id",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def resolve_output_path(output_arg, target_date):
    out_dir = "daily matches"
    os.makedirs(out_dir, exist_ok=True)
    if output_arg:
        if os.path.isabs(output_arg) or os.path.dirname(output_arg):
            return output_arg
        return os.path.join(out_dir, output_arg)
    return os.path.join(out_dir, f"sbr_nba_{target_date.strftime('%Y-%m-%d')}.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--book", default="bet365")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    if (args.date or "").strip():
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = (datetime.now().date() - timedelta(days=1))
    dated_output_path = resolve_output_path((args.output or "").strip(), target_date)
    latest_output_path = "nba-latest-odds.csv"

    try:
        spread_rows, spread_html = fetch_odds_rows_and_html(target_date, "pointspread")
        total_rows = fetch_odds_table(target_date, "totals")
    except Exception as ex:
        write_csv(dated_output_path, [])
        write_csv(latest_output_path, [])
        print(f"已输出: {latest_output_path} 共0行", flush=True)
        print(f"已输出: {dated_output_path} 共0行", flush=True)
        print(f"{target_date.strftime('%Y-%m-%d')} {repr(ex)}", flush=True)
        return

    wager_pct_map = extract_wager_pct_map(spread_html)
    score_map = extract_score_map(spread_html)
    spread_map = parse_rows(spread_rows, "spread", args.book, wager_pct_map=wager_pct_map, score_map=score_map)
    total_map = parse_rows(total_rows, "total", args.book, score_map=score_map)
    day_map = merge_game_maps(spread_map, total_map)
    day_rows = list(day_map.values())
    day_rows.sort(key=lambda r: (r.get("date", ""), r.get("time_et", ""), r.get("home", ""), r.get("away", "")))
    write_csv(dated_output_path, day_rows)
    write_csv(latest_output_path, day_rows)
    print(f"已输出: {latest_output_path} 共{len(day_rows)}行", flush=True)
    print(f"已输出: {dated_output_path} 共{len(day_rows)}行", flush=True)


if __name__ == "__main__":
    main()
