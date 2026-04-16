#!/bin/bash
# 测试报告生成（不发送）

LOG_FILE="/Users/shenghuali/reddog-scraper/cron.log"
ERROR_LOG="/Users/shenghuali/reddog-scraper/error.log"

# 昨天日期（墨尔本时间）
# macOS兼容的日期计算
YESTERDAY=$(TZ=Australia/Melbourne date -v -1d '+%Y-%m-%d')
TODAY=$(TZ=Australia/Melbourne date '+%Y-%m-%d')

# 任务定义数组：任务名称 日志中识别的关键词
# 格式：任务名称:关键词1|关键词2
TASKS=(
    "nba-injury.py:python3 nba-injury.py|nba-injury.py"
    "nba-daily-odds.py:python3 nba-daily-odds.py|nba-daily-odds.py"
    "sync_daily_odds.py:python3 sync_daily_odds.py|sync_daily_odds.py"
    "fill_rest_data.py:python3 fill_rest_data.py|fill_rest_data.py"
    "nba-advanced-stats.py:python3 nba-advanced-stats.py|nba-advanced-stats.py"
    "daily_cron_report.sh:\./daily_cron_report.sh|daily_cron_report.sh"
)

# 函数：获取任务前一天的成功/失败次数和最近执行时间
get_task_stats() {
    local task_name="$1"
    local pattern="$2"
    local success_count=0
    local fail_count=0
    local last_exec_time="无记录"
    
    if [ -f "$LOG_FILE" ]; then
        # 获取昨天该任务的所有日志行
        local yesterday_lines=$(grep "\\[$YESTERDAY" "$LOG_FILE" 2>/dev/null | grep -E "$pattern" || true)
        
        if [ -n "$yesterday_lines" ]; then
            # 统计成功和失败
            success_count=$(echo "$yesterday_lines" | grep -c "✅\\|成功\\|SUCCESS" || echo "0")
            fail_count=$(echo "$yesterday_lines" | grep -c "❌\\|失败\\|ERROR" || echo "0")
        fi
        
        # 获取最近执行时间（不限日期）
        local last_line=$(grep -E "$pattern" "$LOG_FILE" 2>/dev/null | tail -1 || true)
        if [ -n "$last_line" ]; then
            # 提取时间戳 [2026-04-14 00:13:18]
            last_exec_time=$(echo "$last_line" | grep -o '\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\]' | head -1 | tr -d '[]' || echo "未知时间")
            if [ -z "$last_exec_time" ] || [ "$last_exec_time" = "未知时间" ]; then
                last_exec_time=$(echo "$last_line" | cut -d' ' -f1-2 | sed 's/^\[//;s/\]$//' 2>/dev/null || echo "未知时间")
            fi
        fi
    fi
    
    echo "$success_count:$fail_count:$last_exec_time"
}

# 生成报告
echo "📊 NBA数据抓取系统 - 每日执行报告（按任务）"
echo "生成时间: $(date '+%Y-%m-%d %H:%M') (墨尔本时间)"
echo "统计日期: $YESTERDAY"
echo "============================================"

echo ""
echo "🔧 昨日任务执行统计:"
echo ""
echo "任务名称                     成功  失败  最近执行时间"
echo "--------------------------------------------------------"

for task_def in "${TASKS[@]}"; do
    task_name=$(echo "$task_def" | cut -d':' -f1)
    pattern=$(echo "$task_def" | cut -d':' -f2)
    
    stats=$(get_task_stats "$task_name" "$pattern")
    success_count=$(echo "$stats" | cut -d':' -f1)
    fail_count=$(echo "$stats" | cut -d':' -f2)
    last_exec_time=$(echo "$stats" | cut -d':' -f3)
    
    # 格式化输出
    printf "%-28s %4s %4s  %s\n" "$task_name" "$success_count" "$fail_count" "$last_exec_time"
done

echo ""
echo "📈 昨日总体统计:"
if [ -f "$LOG_FILE" ]; then
    YESTERDAY_ENTRIES=$(grep -c "\\[$YESTERDAY" "$LOG_FILE" 2>/dev/null || echo "0")
    YESTERDAY_SUCCESS=$(grep "\\[$YESTERDAY" "$LOG_FILE" 2>/dev/null | grep -c "✅\\|成功\\|SUCCESS" || echo "0")
    YESTERDAY_FAIL=$(grep "\\[$YESTERDAY" "$LOG_FILE" 2>/dev/null | grep -c "❌\\|失败\\|ERROR" || echo "0")
    
    echo "   ✅ 总成功: ${YESTERDAY_SUCCESS} 次"
    echo "   ❌ 总失败: ${YESTERDAY_FAIL} 次"
    echo "   📅 昨日记录: ${YESTERDAY_ENTRIES} 条"
else
    echo "   ⚠️  日志文件不存在"
fi

echo ""
echo "⚠️  最近错误摘要:"
if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
    tail -3 "$ERROR_LOG" | while read error; do
        echo " • $error"
    done
else
    echo " • 无最近错误记录"
fi

echo ""
echo "============================================"
echo "报告生成完成 | 保持监控 🐕"
echo "============================================"