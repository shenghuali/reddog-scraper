# Reddog Scraper Infra Notes

## Scope
这份说明书只记录 `reddog-scraper` 当前可用的 NBA 抓取/同步链、关键文件、踩坑结论与后续迁移时必须保留的执行顺序。只记结论，不记闲话。

## Core NBA Data Analysis Framework (From Literature Research)

### 📊 Data-Driven Betting Philosophy (from CMU Research)
- **Find value, not predict winners**: Identify market mispricings (value bets)
- **Strategy over model**: Simple model + smart strategy = profit
- **Scientific money management**: Kelly Criterion (half-Kelly), bet sizing based on edge
- **Margin betting**: Only bet when model vs market difference > 2 points
- **Discipline**: Don't bet every game, wait for best opportunities

### 🏀 Key Statistical Dimensions (from Dunkest & Stanford Research)
#### **Core Efficiency Metrics:**
- ⚡ **Offensive Efficiency (ORTG)** - Points per 100 possessions
- 🛡️ **Defensive Efficiency (DRTG)** - Points allowed per 100 possessions  
- 📈 **Net Rating** - ORTG minus DRTG (most predictive)
- 🎯 **Effective Field Goal % (eFG%)** - Adjusts for 3-point value
- ⏱️ **Pace** - Possessions per game

#### **Contextual Factors Weighting:**
- 📍 **Home Court Advantage**: ~3-4 point advantage
- ⏰ **Rest Days / Fatigue Factors**
- 📊 **ATS Performance History**
- ⚕️ **Injury & Rotation Impact**
- 📈 **Recent Form Trends**

### 🧠 Prediction Models & Methods (from Stanford & CMU Research)
#### **Practical Model Architecture:**
- 📈 **Linear Regression** (baseline, robust)
- 🌳 **Gradient Boosting Decision Trees** (best performance)
- 📊 **Rolling Window Training** (adapts to team state changes)
- 🎯 **Probability Calibration** (spread → win probability)

#### **Feature Priority:**
1. Offensive Efficiency (most important)
2. Defensive Efficiency  
3. Home Court Advantage
4. Game Pace
5. Recent Performance
6. ATS History

### 💰 Value Bet Identification Framework (from CMU)
#### **Value Score Calculation:**
```
Value Score = (Model Prediction - Market Line) × Confidence Level
- Difference > 2 points → potential value
- Difference > 3 points → high value  
- Difference > 5 points → extreme value opportunity
```

#### **Bet Decision Matrix:**
- 📊 **High confidence + Large difference** → Core bet
- 📊 **Medium confidence + Medium difference** → Probe bet  
- 📊 **Low confidence + Small difference** → Observe, no bet

### 🎯 Market Segment Opportunities (from CMU)
#### **High-Value Markets:**
- 🎯 **Halftime spreads** (Brownian motion model)
- 🎯 **Alternate lines** (normal distribution analysis)
- 🎯 **Team props** (lower market attention)
- 🎯 **Player props** (information asymmetry)

### ⚠️ Pitfalls to Avoid
- ❌ **Gambler's Fallacy** (Stanford literature warning)
- ❌ **Ignoring matchup analysis**
- ❌ **Emotional decision-making**
- ❌ **Over-reliance on single metrics**
- ❌ **Neglecting sample size limitations**

### ✅ Essential Steps
- ✅ **Multi-dimensional data validation**
- ✅ **Statistical significance testing**
- ✅ **Backtesting & historical validation**
- ✅ **Real-time data updates**
- ✅ **Continuous optimization & iteration**

## Critical Paths
- 工作根目录：`/home/shenghuali/reddog-scraper`
- Python venv：`/home/shenghuali/reddog-scraper/venv`
- 主同步文件：`/home/shenghuali/reddog-scraper/sync_daily_odds.py`
- 赔率主输出：`/home/shenghuali/reddog-scraper/nba-latest-odds.csv`
- 富化主输出：`/home/shenghuali/reddog-scraper/nba_enriched_data.csv`
- SBR 试验抓取：`/home/shenghuali/reddog-scraper/nba_sbr_extra.py`
- Lessons：`/home/shenghuali/reddog-scraper/memory/lessons.md`

## 📋 Memo Recommendation Template Structure

### **Recommended Format:**
```
🏀 NBA今日价值投注推荐
📅 日期：YYYY-MM-DD
🎯 置信度：[高/中/低]

### 📊 对阵分析
- 主队：[球队名] (主场优势：+3.5)
- 客队：[球队名] 
- 盘口：[主队让分/客队受让]

### 📈 数据洞察
1. **效率对比**：主队NetRating +8.2 vs 客队 -3.5
2. **近期状态**：主队5连胜，客队3连败
3. **伤病影响**：[关键球员状态]
4. **ATS记录**：主队20-10，客队12-18

### 💰 价值识别
- **模型预测**：主队 -6.5分
- **市场盘口**：主队 -4.5分
- **价值差异**：+2.0分
- **价值评分**：8.5/10

### 🎯 投注建议
- **推荐**：[主队/客队/总分大/总分小]
- **投注类型**：[让分盘/总分盘/胜负盘]
- **建议金额**：[基于凯利准则]
- **风险提示**：[关键注意事项]

### 📊 历史表现
- 历史推荐准确率：XX%
- 平均回报率：XX%
- 最大回撤：XX%
```

### **Data Source Priority:**
1. Team efficiency data (nrtg, ortg, drtg)
2. Home/away performance differentials
3. Recent trends (last 10 games)
4. Injury & rotation reports
5. Market line movements

## Stable Manual Chain
当前已实测可顺序跑通的核心链路：
1. `/home/shenghuali/reddog-scraper/venv/bin/python /home/shenghuali/reddog-scraper/nba-injury.py`
2. `/home/shenghuali/reddog-scraper/venv/bin/python /home/shenghuali/reddog-scraper/nba-advanced-stats.py`
3. `/home/shenghuali/reddog-scraper/venv/bin/python /home/shenghuali/reddog-scraper/analyze.py`
4. `/home/shenghuali/reddog-scraper/venv/bin/python /home/shenghuali/reddog-scraper/fill_rest_data.py`
5. `/home/shenghuali/reddog-scraper/venv/bin/python /home/shenghuali/reddog-scraper/sync_daily_odds.py`

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
- 之前 `nba_sbr_extra.py` 跑出 `Wrote 0 rows to /home/shenghuali/reddog-scraper/nba-sbr-extra.csv`，说明旧解析路径没命中；不是站点不可访问。

## 🔧 Technical Implementation Requirements

### **Features to Integrate:**
- ✅ **Value difference calculator**
- ✅ **Confidence scoring system**  
- ✅ **Kelly money management**
- ✅ **Multi-dimensional data aggregation**
- ✅ **Automated backtesting framework**

### **Update Frequency:**
- 🔄 **Daily**: Update team efficiency data
- 🔄 **Pre-game**: Update injury & rotation data
- 🔄 **Real-time**: Monitor line movements
- 🔄 **Post-game**: Validation & optimization

## Environment Rules
- 一律优先使用：`/home/shenghuali/reddog-scraper/venv/bin/python`
- 不要混用系统 `python3`，否则会出现假性缺库，例如：`ModuleNotFoundError: No module named 'requests'`
- `requests` 已确认存在于：`/home/shenghuali/reddog-scraper/venv/lib/python3.11/site-packages`

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

则可以删除旧版 `nba-daily-odds.py`，并将新的 SBR 版脚本改名顶替为：`/home/shenghuali/reddog-scraper/nba-daily-odds.py`。

## 📚 Literature References Summary
1. **Stanford CS229 (2013)**: Machine learning for NBA point spread prediction
2. **Dunkest.com**: Practical statistical betting strategies  
3. **Medium/Coemeta**: Statistical inference & pitfalls in NBA analysis
4. **CMU Capstone (2020)**: Data-driven NBA betting strategy implementation

**Key Takeaway**: Simple models + sophisticated strategies > Complex models + naive strategies
