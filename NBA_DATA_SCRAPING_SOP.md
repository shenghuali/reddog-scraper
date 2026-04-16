# NBA Data Scraping SOP

## Purpose
This SOP defines the standard workflow for the NBA data scraping pipeline under `/home/shenghuali/reddog-scraper/`. It covers the order of execution, data dependencies, validation checkpoints, and failure-handling rules for producing analysis-ready NBA datasets.

## Workspace
- Root path: `/home/shenghuali/reddog-scraper/`
- Time basis: Melbourne time (AEST/AEDT)

## Core Output Files
- `nba-roster.csv`
- `nba-advanced-stats.csv`
- `nba-latest-odds.csv`
- latest injury CSV in `/home/shenghuali/reddog-scraper/`
- `nba_enriched_data.csv`

## Script Inventory
- `scrape_espn_roster.py`
- `nba-advanced-stats.py`
- `nba-daily-odds.py`
- `nba-injury.py`
- `sync_odds.py`
- `sync_daily_odds.py`
- `track_injury_changes.py`
- `parse_data.py`
- `nba_daemon.py`

## Data Priority
1. Roster: `nba-roster.csv`
2. Stats: `nba-advanced-stats.csv`
3. Injury: latest dated injury CSV in the same directory

## Standard Workflow

### 1. Update roster data
- Script: `scrape_espn_roster.py`
- Goal: refresh team rosters and player base info
- Output: `nba-roster.csv`

### 2. Update advanced stats
- Script: `nba-advanced-stats.py`
- Goal: refresh player/team advanced metrics
- Output: `nba-advanced-stats.csv`

### 3. Update injury data
- Script: `nba-injury.py`
- Goal: fetch the latest injury report data
- Companion check: `track_injury_changes.py`

### 4. Fetch daily odds
- Script: `nba-daily-odds.py`
- Goal: fetch the current day's betting lines and totals
- Rule: do **not** manually add `--date`

### 5. Sync and normalize odds
- Scripts:
  - `sync_odds.py`
  - `sync_daily_odds.py`
- Goal:
  - fill missing odds rows
  - normalize latest odds snapshots
  - align odds data for merge

### 6. Track injury changes
- Script: `track_injury_changes.py`
- Goal: detect status changes, additions, and removals in injury data

### 7. Parse and merge final datasets
- Script: `parse_data.py`
- Goal:
  - clean raw outputs
  - normalize team/date fields
  - merge roster, stats, injury, and odds data
  - generate analysis-ready enriched output
- Output: `nba_enriched_data.csv`

## Recommended Execution Order
1. `scrape_espn_roster.py`
2. `nba-advanced-stats.py`
3. `nba-injury.py`
4. `nba-daily-odds.py`
5. `sync_odds.py`
6. `sync_daily_odds.py`
7. `track_injury_changes.py`
8. `parse_data.py`

## Validation Checklist
After each run, check:
- target CSV exists
- file is non-empty
- headers are correct
- team names are normalized
- dates are aligned to expected format/time basis
- latest injury file is actually current
- odds fields are populated
- `nba_enriched_data.csv` has no major column shift or null explosion

## Important Enriched Fields
Common key fields in `nba_enriched_data.csv` include:
- `season`
- `match_type`
- `date`
- `home_team`
- `away_team`
- `home_score`
- `away_score`
- `home_rest`
- `away_rest`
- `home_b2b`
- `away_b2b`
- `handicap`
- `total`
- `open_spread`
- `close_spread`
- `open_total`
- `close_total`
- `home_spread_odds`
- `away_spread_odds`
- `home_wagers_pct`
- `away_wagers_pct`
- `ats_diff`
- `ats_result`
- `total_score`
- `ou_result`

## Error Recovery Rules
If a script fails, recover in this order:
1. Permission issue:
   - `chmod -R 777 /data`
2. Missing Python package:
   - `pip install <package>`
3. Missing system package:
   - `apt-get install <package>`
4. Wrong path / missing file:
   - inspect `/data` and correct the path
5. Bad merge / schema drift:
   - inspect CSV headers
   - inspect parse/merge logic
   - normalize team/date/column names

## Output Standard
Do not report only “success”. Always verify outputs by checking at least one of:
- CSV header
- last few rows
- recent log lines

## Odds Movement Rule
If odds movement is greater than `0.5`:
- treat as a notable market move
- write to `http://localhost:5230`
- visibility must be `PUBLIC`

## Notes
- This SOP intentionally excludes cron scheduling.
- `nba_daemon.py` can be used later for continuous or scheduled execution, but scheduling is not part of this document.
