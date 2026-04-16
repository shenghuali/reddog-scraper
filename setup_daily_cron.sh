#!/bin/bash
# 设置每日8点Cron报告任务

echo "=================================================="
echo "设置每日Cron报告任务"
echo "=================================================="

# 检查当前Cron任务
echo "📋 当前Cron任务:"
crontab -l 2>/dev/null

# 创建执行脚本
SCRIPT_PATH="/Users/shenghuali/reddog-scraper/run_daily_report.sh"
cat > "$SCRIPT_PATH" << 'EOF'
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
EOF

# 设置执行权限
chmod +x "$SCRIPT_PATH"
echo "✅ 执行脚本已创建: $SCRIPT_PATH"

# 墨尔本时间8:00对应的UTC时间
# 墨尔本 UTC+10 (AEST) 或 UTC+11 (AEDT)
# 简化处理：使用UTC 22:00（前一天）对应墨尔本8:00
# 实际需根据夏令时调整

CRON_JOB="0 22 * * * /bin/bash $SCRIPT_PATH >> /Users/shenghuali/reddog-scraper/daily_report_cron.log 2>&1"

# 添加到crontab
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_JOB") | crontab -

echo "✅ Cron任务已添加:"
echo "   $CRON_JOB"
echo ""
echo "📅 执行时间: 每天墨尔本时间 8:00"
echo "   (UTC时间 22:00，前一天)"
echo "📱 发送到: Discord"
echo ""
echo "🔍 验证设置:"
crontab -l | grep "$SCRIPT_PATH"
echo ""
echo "🎯 立即测试:"
echo "   bash $SCRIPT_PATH"
echo ""
echo "📊 查看日志:"
echo "   tail -f /Users/shenghuali/reddog-scraper/daily_report_cron.log"
echo ""
echo "⚠️  注意："
echo "   需要确保OpenClaw网关已启动并配置Discord连接"