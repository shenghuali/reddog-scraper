# Reddog Scraper Infra Notes

## Scope
这份说明书只记录 `reddog-scraper` 当前可用的 NBA 抓取/同步链、关键文件、踩坑结论与后续迁移时必须保留的执行顺序。只记结论，不记闲话。

## Critical Paths
- 工作根目录：`/data/reddog-scraper`
- Python venv：`/data/reddog-scraper/venv`
- 主同步文件：`/data/reddog-scraper/sync_daily_odds.py`
- 赔率主输出：`/data/reddog-scraper/nba-latest-odds.csv`
- 富化主输出：`/data/reddog-scraper/nba_enriched_data.csv`
- SBR 试验抓取：`/data/reddog-scraper/nba_sbr_extra.py`
- Lessons：`/data/reddog-scraper/memory/lessons.md`

## Stable Manual Chain
当前已实测可顺序跑通的核心链路：
1. `/data/reddog-scraper/venv/bin/python /data/reddog-scraper/nba-injury.py`
2. `/data/reddog-scraper/venv/bin/python /data/reddog-scraper/nba-advanced-stats.py`
3. `/data/reddog-scraper/venv/bin/python /data/reddog-scraper/analyze.py`
4. `/data/reddog-scraper/venv/bin/python /data/reddog-scraper/fill_rest_data.py`
5. `/data/reddog-scraper/venv/bin/python /data/reddog-scraper/sync_daily_odds.py`

## Current Sync State
- `sync_daily_odds.py` 已重写为更直接的按键同步逻辑，用现有 `nba-latest-odds.csv` 回填 `nba_enriched_data.csv`。
- 当前已确认能补回的字段：`open_spread`、`close_spread`、`open_total`、`close_total`、`ats_diff`、`ats_result`、`total_score`、`ou_result`。
- 当前仍需从 SBR 专门补抓的字段：`spread`、`totals`、`opener_spread`、`opener_total`、`away_wagers_pct`、`home_wagers_pct`。
- 业务要求：任何 `null` 都不算有效值；抓取链里只要出现 `null`，就视为解析未完成，不能写进最终业务 CSV。

## SBR Findings
- 有效入口：`https://www.sportsbookreview.com/betting-odds/nba-basketball/`
- 备选入口：`https://www.sportsbookreview.com/betting-odds/nba-basketball/pointspread/full-game/`
- 页面可访问，且已实测命中以下结构或片段：
  - `currentLine`
  - `openingLineViews`
  - `homeOdds`
  - `awayOdds`
  - `homeSpread`
  - `awaySpread`
  - `GameRows_consensusColumn__AOd1q`
  - `data-cy="odd-grid-opener-homepage"`
  - 实际渲染值示例：`+2.5 / -115`、`-2.5 / -105`
- `wagers` 视觉语义已确认：上面是客队百分比，下面是主队百分比。落地字段映射必须是：`away_wagers_pct` = 上，`home_wagers_pct` = 下。
- `spread` 永远按主队盘口写单值，不保留主客两套 spread；例如 `PHX @ ORL` 时主队 ORL 当前盘口是 `-2`，则写 `spread=-2`。
- `opener_spread` 同样按主队开盘盘口写单值；例如主队 ORL 开盘 `-2.5`，则写 `opener_spread=-2.5`。
- 字段命名不要带 `bet365` 前缀；当前盘口列统一写 `spread` / `totals`，开盘列统一写 `opener_spread` / `opener_total`。
- 之前 `nba_sbr_extra.py` 跑出 `Wrote 0 rows to /data/reddog-scraper/nba-sbr-extra.csv`，说明旧解析路径没命中；不是站点不可访问。

## Environment Rules
- 一律优先使用：`/data/reddog-scraper/venv/bin/python`
- 不要混用系统 `python3`，否则会出现假性缺库，例如：`ModuleNotFoundError: No module named 'requests'`
- `requests` 已确认存在于：`/data/reddog-scraper/venv/lib/python3.11/site-packages`

## Migration / Rebuild Rule
如果后续确认 `nba_sbr_extra.py` 能稳定抓全以下字段：
- `game_id`
- `home`
- `away`
- `date`
- `spread`
- `totals`
- `opener_spread`
- `opener_total`
- `away_wagers_pct`
- `home_wagers_pct`

则可以删除旧版 `nba-daily-odds.py`，并将新的 SBR 版脚本改名顶替为：`/data/reddog-scraper/nba-daily-odds.py`。
