#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

import requests

BASE = Path('/data/reddog-scraper')
OUT = BASE / 'nba-sbr-extra.csv'
URL = 'https://www.sportsbookreview.com/betting-odds/nba-basketball/'

HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept-Language': 'en-US,en;q=0.9',
}


def find_next_data(html: str):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def norm(v):
    return '' if v is None else str(v).strip()


def parse_rows(data):
    rows = []
    for obj in walk(data):
        game_id = obj.get('gameId') or obj.get('id')
        home = obj.get('homeTeam') or obj.get('home') or obj.get('homeTeamAbbr')
        away = obj.get('awayTeam') or obj.get('away') or obj.get('awayTeamAbbr')
        start = obj.get('startTime') or obj.get('startDate') or obj.get('date')
        opening = obj.get('openingLine') or {}
        current = obj.get('currentLine') or {}
        if not game_id or not home or not away:
            continue
        if not opening and not current:
            continue
        date = str(start)[:10] if start else ''
        row = {
            'game_id': norm(game_id),
            'home': norm(home),
            'away': norm(away),
            'date': date,
            'spread': norm(current.get('homeSpread')),
            'totals': norm(current.get('total')),
            'opener_spread': norm(opening.get('homeSpread')),
            'opener_total': norm(opening.get('total')),
            'away_wagers_pct': '',
            'home_wagers_pct': '',
        }
        if any(row[k] for k in ['spread', 'totals', 'opener_spread', 'opener_total']):
            rows.append(row)
    dedup = {}
    for row in rows:
        dedup[(row['date'], row['home'], row['away'])] = row
    return list(dedup.values())


def main():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = find_next_data(r.text)
    if not data:
        raise SystemExit('No __NEXT_DATA__ found')
    rows = parse_rows(data)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['game_id','home','away','date','spread','totals','opener_spread','opener_total','away_wagers_pct','home_wagers_pct'])
        w.writeheader()
        w.writerows(rows)
    print(f'Wrote {len(rows)} rows to {OUT}')
    for row in rows[:10]:
        print(row)


if __name__ == '__main__':
    main()
