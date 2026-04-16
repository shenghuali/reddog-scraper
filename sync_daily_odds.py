#!/usr/bin/env python3
import csv
import os
from pathlib import Path


BASE = Path('/Users/shenghuali/reddog-scraper')
ENRICHED_CSV = BASE / 'nba_enriched_data.csv'
LATEST_ODDS_CSV = BASE / 'nba-latest-odds.csv'
WINDOW_START = ''
WINDOW_END = ''

TEAM_MAP = {
    'BK': 'BKN', 'BKN': 'BKN',
    'GS': 'GSW', 'GSW': 'GSW',
    'NO': 'NOP', 'NOP': 'NOP',
    'NY': 'NYK', 'NYK': 'NYK',
    'SA': 'SAS', 'SAS': 'SAS',
    'PHO': 'PHX', 'PHX': 'PHX',
    'WAS': 'WSH', 'WSH': 'WSH', 'WASH': 'WSH',
    'CHA': 'CHA', 'CHO': 'CHA',
}


def load_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def normalize(v):
    return (v or '').strip()


def normalize_team(v):
    team = normalize(v).upper()
    return TEAM_MAP.get(team, team)


def to_float(v):
    try:
        s = normalize(v).replace('%', '')
        if s == '':
            return None
        return float(s)
    except Exception:
        return None


def resolve_window(rows):
    dates = sorted({normalize(row.get('date')) for row in rows if normalize(row.get('date'))})
    if not dates:
        return WINDOW_START, WINDOW_END

    start = WINDOW_START or dates[0]
    end = WINDOW_END or dates[-1]
    return start, end


def in_window(date, start, end):
    if not date:
        return False
    if start and date < start:
        return False
    if end and date > end:
        return False
    return True


def ensure_headers(existing_headers):
    headers = list(existing_headers)
    additions = [
        'season', 'match_type', 'game_type', 'date', 'home_team', 'away_team',
        'home_score', 'away_score', 'score', 'home_rest', 'away_rest',
        'home_b2b', 'away_b2b', 'handicap', 'total',
        'open_spread', 'close_spread', 'open_total', 'close_total',
        'home_spread_odds', 'away_spread_odds',
        'home_wagers_pct', 'away_wagers_pct',
        'ats_diff', 'ats_result', 'total_score', 'ou_result'
    ]
    for field in additions:
        if field not in headers:
            headers.append(field)
    return headers


def build_odds_lookup(rows):
    lookup = {}
    for row in rows:
        date = normalize(row.get('date'))
        home = normalize_team(row.get('home'))
        away = normalize_team(row.get('away'))
        if not date or not home or not away:
            continue
        lookup[(date, home, away)] = row
    return lookup


def calculate_results(row):
    home_score = to_float(row.get('home_score'))
    away_score = to_float(row.get('away_score'))
    close_spread = to_float(row.get('close_spread'))
    close_total = to_float(row.get('close_total'))

    if home_score is None or away_score is None:
        return

    if home_score == 0 and away_score == 0:
        row['score'] = ''
        row['total_score'] = ''
        row['ats_diff'] = ''
        row['ats_result'] = ''
        row['ou_result'] = ''
        return

    total_score = home_score + away_score
    row['score'] = f'{int(home_score)}-{int(away_score)}'
    row['total_score'] = f'{total_score:.1f}'

    if close_spread is not None:
        ats_diff = home_score - away_score - close_spread
        row['ats_diff'] = f'{ats_diff:.1f}'
        if ats_diff > 0:
            row['ats_result'] = 'Home Win'
        elif ats_diff < 0:
            row['ats_result'] = 'Away Win'
        else:
            row['ats_result'] = 'Push'

    if close_total is not None:
        if total_score > close_total:
            row['ou_result'] = 'Over'
        elif total_score < close_total:
            row['ou_result'] = 'Under'
        else:
            row['ou_result'] = 'Push'


def sync():
    enriched_rows = load_csv(ENRICHED_CSV)
    latest_rows = load_csv(LATEST_ODDS_CSV)

    if not enriched_rows:
        raise SystemExit('No enriched rows found')

    headers = ensure_headers(enriched_rows[0].keys())
    odds_lookup = build_odds_lookup(latest_rows)
    window_start, window_end = resolve_window(latest_rows)

    updated = 0
    added = 0

    existing_keys = {
        (normalize(row.get('date')), normalize_team(row.get('home_team')), normalize_team(row.get('away_team')))
        for row in enriched_rows
    }

    for row in enriched_rows:
        date = normalize(row.get('date'))
        if not in_window(date, window_start, window_end):
            continue

        home_team = normalize_team(row.get('home_team'))
        away_team = normalize_team(row.get('away_team'))
        if not home_team or not away_team:
            continue

        odds = odds_lookup.get((date, home_team, away_team))
        if not odds:
            continue

        row['open_spread'] = normalize(odds.get('opener_spread'))
        row['close_spread'] = normalize(odds.get('spread'))
        row['current_spread'] = normalize(odds.get('spread'))  # 保持向后兼容
        row['open_total'] = normalize(odds.get('opener_total'))
        row['close_total'] = normalize(odds.get('total'))
        # 保持向后兼容的字段
        if 'home' in row:
            row['home'] = normalize_team(odds.get('home'))
        if 'away' in row:
            row['away'] = normalize_team(odds.get('away'))
        row['home_spread_odds'] = normalize(odds.get('home_spread_odds'))
        row['away_spread_odds'] = normalize(odds.get('away_spread_odds'))
        row['home_wagers_pct'] = normalize(odds.get('home wager'))
        row['away_wagers_pct'] = normalize(odds.get('away wager'))
        row['home_score'] = normalize(odds.get('Home Score'))
        row['away_score'] = normalize(odds.get('Away Score'))

        if row['close_spread']:
            row['handicap'] = row['close_spread']
        if row['close_total']:
            row['total'] = row['close_total']

        calculate_results(row)
        updated += 1

    for odds in latest_rows:
        date = normalize(odds.get('date'))
        if not in_window(date, window_start, window_end):
            continue

        home_team = normalize_team(odds.get('home'))
        away_team = normalize_team(odds.get('away'))
        key = (date, home_team, away_team)
        if key in existing_keys:
            continue

        row = {h: '' for h in headers}
        row.update({
            'season': '2025-2026',
            'match_type': 'season',
            'game_type': 'season',
            'date': date,
            'home_team': home_team,
            'away_team': away_team,
            'home': home_team,      # 保持向后兼容
            'away': away_team,      # 保持向后兼容
            'home_score': normalize(odds.get('Home Score')),
            'away_score': normalize(odds.get('Away Score')),
            'handicap': normalize(odds.get('spread')),
            'total': normalize(odds.get('total')),
            'open_spread': normalize(odds.get('opener_spread')),
            'close_spread': normalize(odds.get('spread')),
            'open_total': normalize(odds.get('opener_total')),
            'close_total': normalize(odds.get('total')),
            'home_spread_odds': normalize(odds.get('home_spread_odds')),
            'away_spread_odds': normalize(odds.get('away_spread_odds')),
            'home_wagers_pct': normalize(odds.get('home wager')),
            'away_wagers_pct': normalize(odds.get('away wager')),
        })
        calculate_results(row)
        enriched_rows.append(row)
        existing_keys.add(key)
        added += 1

    with open(ENRICHED_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f'Sync complete. Updated {updated} rows, added {added} rows for {window_start} to {window_end}.')


if __name__ == '__main__':
    window_start = os.environ.get('WINDOW_START', '').strip()
    window_end = os.environ.get('WINDOW_END', '').strip()
    if window_start:
        WINDOW_START = window_start
    if window_end:
        WINDOW_END = window_end
    sync()
