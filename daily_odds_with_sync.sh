#!/bin/bash
# ============================================
# 每日赔率抓取 + 自动同步脚本
# 功能：1. 执行nba-daily-odds.py
#       2. 自动同步到nba_enriched_data.csv
# ============================================

echo "============================================"
echo "   NBA每日赔率抓取与同步"
echo "   开始时间: $(date)"
echo "============================================"

LOG_FILE="/Users/shenghuali/reddog-scraper/cron.log"
ERROR_LOG="/Users/shenghuali/reddog-scraper/error.log"

# ========== 步骤1：执行每日赔率抓取 ==========
echo ""
echo "🔧 步骤1: 执行 nba-daily-odds.py"
echo "执行命令: cd /Users/shenghuali/reddog-scraper && /Users/shenghuali/reddog-scraper/venv/bin/python nba-daily-odds.py"

cd /Users/shenghuali/reddog-scraper

# 执行赔率抓取
START_TIME=$(date +%s)
/Users/shenghuali/reddog-scraper/venv/bin/python nba-daily-odds.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ nba-daily-odds.py 执行成功"
    echo "   执行时间: ${DURATION}秒"
    
    # 检查是否生成了CSV文件
    if [ -f "nba-daily-odds.csv" ]; then
        CSV_SIZE=$(wc -l < "nba-daily-odds.csv")
        echo "   CSV文件行数: $CSV_SIZE"
    else
        echo "⚠️  警告: 未生成 nba-daily-odds.csv 文件"
    fi
else
    echo "❌ nba-daily-odds.py 执行失败 (退出码: $EXIT_CODE)"
    echo "   详细错误请查看: $LOG_FILE"
    echo "   执行时间: ${DURATION}秒"
    exit $EXIT_CODE
fi

# ========== 步骤2：同步到enriched data ==========
echo ""
echo "🔧 步骤2: 同步数据到 nba_enriched_data.csv"
echo "执行命令: cd /Users/shenghuali/reddog-scraper && /Users/shenghuali/reddog-scraper/venv/bin/python sync_daily_odds.py"

START_TIME=$(date +%s)
/Users/shenghuali/reddog-scraper/venv/bin/python sync_daily_odds.py >> "$LOG_FILE" 2>&1
SYNC_EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    echo "✅ 数据同步成功"
    echo "   执行时间: ${DURATION}秒"
    
    # 检查enriched文件
    if [ -f "nba_enriched_data.csv" ]; then
        ENRICHED_SIZE=$(wc -l < "nba_enriched_data.csv" 2>/dev/null || echo "未知")
        echo "   nba_enriched_data.csv 行数: $ENRICHED_SIZE"
    fi
else
    echo "❌ 数据同步失败 (退出码: $SYNC_EXIT_CODE)"
    echo "   详细错误请查看: $LOG_FILE"
    # 同步失败不终止，只记录错误
    echo "$(date): 数据同步失败 (退出码: $SYNC_EXIT_CODE)" >> "$ERROR_LOG"
fi

# ========== 步骤3：验证和清理 ==========
echo ""
echo "🔧 步骤3: 验证和清理"

# 检查文件大小
echo "文件状态:"
ls -lh nba-daily-odds.csv nba_enriched_data.csv 2>/dev/null | while read line; do
    echo "   $line"
done

# 清理临时文件（如果有）
find /Users/shenghuali/reddog-scraper -name "*.tmp" -type f -delete 2>/dev/null || true
find /Users/shenghuali/reddog-scraper -name "*.temp" -type f -delete 2>/dev/null || true

# ========== 完成 ==========
echo ""
echo "============================================"
echo "   任务完成！"
echo "   结束时间: $(date)"
echo ""
echo "📊 执行摘要:"
echo "   - 赔率抓取: $(if [ $EXIT_CODE -eq 0 ]; then echo '✅ 成功'; else echo '❌ 失败'; fi)"
echo "   - 数据同步: $(if [ $SYNC_EXIT_CODE -eq 0 ]; then echo '✅ 成功'; else echo '❌ 失败'; fi)"
echo "   - 总执行时间: ${DURATION}秒"
echo ""
echo "📁 重要文件:"
echo "   - 日志文件: $LOG_FILE"
echo "   - 错误日志: $ERROR_LOG"
echo "   - 原始数据: nba-daily-odds.csv"
echo "   - 丰富数据: nba_enriched_data.csv"
echo "============================================"

# 返回主要任务的退出码
exit $EXIT_CODE