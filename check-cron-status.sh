#!/bin/bash
echo "🐕 Cron系统状态检查"
echo "=================="

echo "1. 进程状态："
ps aux | grep -E "cron|crond" | grep -v grep || echo "  ❌ 无cron进程"

echo ""
echo "2. 配置验证："
crontab -l 2>/dev/null | head -10 || echo "  ❌ 无crontab配置"

echo ""
echo "3. 日志检查："
tail -5 /data/reddog-scraper/cron.log 2>/dev/null || echo "  ❌ 无日志文件"

echo ""
echo "4. 时区验证："
echo "   UTC时间: $(date)"
echo "   墨尔本时间: $(TZ=Australia/Melbourne date)"

echo ""
echo "5. 下次执行："
echo "   伤病抓取: 下个整点"
echo "   赔率抓取: 下个:05分钟"
echo "   每日报告: 明天08:00 (墨尔本时间)"