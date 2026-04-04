# DogGPT Lessons

[DogGPT] 2026-03-31 NBA odds sync repair: `/data/reddog-scraper/sync_daily_odds.py` 写回闭环本身没坏，真正故障点在 merge/match；`/data/reddog-scraper/nba_enriched_data.csv` 的 `2026-03-24` 到 `2026-03-30` 部分行不只是 `P~AA` 为空，连 `season/home_team/away_team` 也可能为空，导致按键同步失效。先用现有 `nba-latest-odds.csv` 补 `open_spread/close_spread/open_total/close_total/ats_diff/ats_result/total_score/ou_result`，不要把问题误判成 writer 或 cron。 

[DogGPT] 2026-03-31 SBR scraping lessons: `wagers` 只在 SBR 页面可见，页面语义已确认“上面=客队 wager%，下面=主队 wager%”，落地字段应映射为 `away_wagers_pct` / `home_wagers_pct`。SBR 页面可访问，且已实测抓到 `currentLine/openingLineViews/homeOdds/awayOdds/homeSpread/awaySpread` 与渲染层 `+2.5/-115`、`-2.5/-105`，说明 `spread + spread_odds` 有抓取路径；但 `null` 不是可接受值，任何抓取链输出 `null` 都视为解析失败，必须继续从页面真实 DOM/脚本结构补取，不能把 `null` 写进最终业务 CSV。

[DogGPT] 2026-03-31 SBR field naming rules: 字段名不要写成 `bet365_*`。盘口列统一叫 `spread` / `totals`，开盘列保持 `opener_spread` / `opener_total`。只有 `wagers` 需要明确主客场拆分，即 `away_wagers_pct` / `home_wagers_pct`。`spread` 永远按主队盘口写单值，例如 `PHX @ ORL` 时如果主队 ORL 是 `-2`，则写 `spread=-2`；`opener_spread` 同理写主队开盘值，例如 `-2.5`，不需要同时保留主客两个 spread 值。
