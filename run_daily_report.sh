#!/bin/bash
# 每日Cron报告执行脚本

# 设置环境变量
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
export TZ="Australia/Melbourne"

# 切换到脚本目录
cd /Users/shenghuali/reddog-scraper

# 获取当前时间
TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIME] 开始执行每日Cron报告..."

# 执行报告脚本
./daily_cron_report.sh

# 记录执行状态
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$TIME] ✅ 每日报告执行成功"
else
    echo "[$TIME] ❌ 每日报告执行失败 (退出码: $EXIT_CODE)"
fi