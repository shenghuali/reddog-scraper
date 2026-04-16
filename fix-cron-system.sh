#!/bin/bash
# Docker cron系统修复脚本
# 修复方法：使用cron前台运行（Docker最佳实践）

echo "🐕 Docker Cron系统修复开始..."
echo "当前时间: $(TZ=Australia/Melbourne date)"

# 1. 安装cron包（如果未安装）
echo "🔧 检查cron包..."
if ! command -v cron &> /dev/null; then
    echo "  安装cron包..."
    apt-get update && apt-get install -y cron
else
    echo "  ✅ cron已安装"
fi

# 2. 停止现有cron进程
echo "🛑 停止现有cron进程..."
pkill cron 2>/dev/null
sleep 2

# 3. 恢复crontab配置
echo "📋 恢复crontab配置..."
# 尝试容器内路径
if [ -f "/data/reddog-scraper/crontab-final-schedule.txt" ]; then
    crontab /data/reddog-scraper/crontab-final-schedule.txt
    echo "  ✅ crontab配置已恢复（容器内路径）"
# 尝试主机映射路径
elif [ -f "/Users/shenghuali/reddog-scraper/crontab-final-schedule.txt" ]; then
    crontab /Users/shenghuali/reddog-scraper/crontab-final-schedule.txt
    echo "  ✅ crontab配置已恢复（主机路径）"
else
    echo "  ❌ crontab配置文件不存在"
    echo "  尝试创建默认配置..."
    # 创建默认crontab配置
    cat > /tmp/default-crontab.txt << 'EOF'
TZ=Australia/Melbourne

# 每小时执行
0 * * * * cd /data/reddog-scraper && ./venv/bin/python nba-injury.py >> /data/reddog-scraper/cron.log 2>&1
5 * * * * cd /data/reddog-scraper && ./venv/bin/python nba-daily-odds.py >> /data/reddog-scraper/cron.log 2>&1 && ./venv/bin/python sync_to_enriched.py >> /data/reddog-scraper/cron.log 2>&1

# 每周一执行
0 9 * * 1 cd /data/reddog-scraper && ./venv/bin/python nba-advanced-stats.py >> /data/reddog-scraper/cron.log 2>&1

# 每日报告
0 8 * * * cd /data/reddog-scraper && ./daily_cron_report.sh >> /data/reddog-scraper/cron.log 2>&1
EOF
    crontab /tmp/default-crontab.txt
    echo "  ✅ 已创建并使用默认crontab配置"
fi

# 4. 前台启动cron（Docker最佳实践）
echo "🚀 启动cron前台进程..."
cron -f &
CRON_PID=$!
echo "  ✅ cron前台进程已启动 (PID: $CRON_PID)"

# 5. 验证配置
echo "🔍 验证crontab配置..."
crontab -l | head -5

# 6. 生成今日报告
echo "📊 生成今日报告..."
cd /data/reddog-scraper && ./daily_cron_report.sh

echo ""
echo "✅ 修复完成！"
echo "📅 下次执行时间："
echo "   伤病抓取: 每小时整点"
echo "   赔率抓取: 每小时第5分钟"  
echo "   每日报告: 08:00 (墨尔本时间)"
echo "   高级统计: 每周一09:00"
echo ""
echo "📝 验证命令："
echo "   ps aux | grep cron"
echo "   tail -f /data/reddog-scraper/cron.log"
echo "   crontab -l"