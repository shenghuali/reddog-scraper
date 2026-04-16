#!/bin/bash
# ============================================
# NBA定时任务快速设置脚本
# ============================================

echo "============================================"
echo "   NBA定时任务快速设置"
echo "============================================"

# 1. 设置crontab
echo ""
echo "🔧 步骤1: 设置crontab定时任务"
crontab /data/reddog-scraper/crontab-template.txt

if [ $? -eq 0 ]; then
    echo "✅ Crontab设置成功"
    echo ""
    echo "📋 当前配置:"
    echo "----------------------------------------"
    crontab -l
    echo "----------------------------------------"
else
    echo "❌ Crontab设置失败"
    exit 1
fi

# 2. 备份配置
echo ""
echo "🔧 步骤2: 备份配置"
crontab -l > /data/reddog-scraper/crontab-backup.txt
echo "✅ 配置已备份到: /data/reddog-scraper/crontab-backup.txt"

# 3. 测试时区
echo ""
echo "🔧 步骤3: 检查时区设置"
echo "当前时区: $(cat /etc/timezone 2>/dev/null || echo '未设置')"
echo "当前时间: $(date)"
echo "时区软链接: $(readlink -f /etc/localtime 2>/dev/null || echo '未设置')"

# 4. 测试Python环境
echo ""
echo "🔧 步骤4: 测试Python环境"
if [ -f "/data/reddog-scraper/venv/bin/python" ]; then
    echo "✅ Python虚拟环境可用"
    /data/reddog-scraper/venv/bin/python -c "
import sys
print(f'Python版本: {sys.version.split()[0]}')
try:
    import bs4
    print('✅ BeautifulSoup 可用')
except ImportError:
    print('❌ BeautifulSoup 不可用')
"
else
    echo "⚠️  Python虚拟环境不可用"
fi

# 5. 完成
echo ""
echo "============================================"
echo "   设置完成！"
echo ""
echo "📝 重要文件:"
echo "   1. 恢复脚本: /data/reddog-scraper/restore-after-docker-restart.sh"
echo "   2. 配置模板: /data/reddog-scraper/crontab-template.txt"
echo "   3. 配置备份: /data/reddog-scraper/crontab-backup.txt"
echo "   4. 任务日志: /data/reddog-scraper/cron.log"
echo ""
echo "🚀 使用说明:"
echo "   1. Docker重启后运行: bash /data/reddog-scraper/restore-after-docker-restart.sh"
echo "   2. 查看cron日志: tail -f /data/reddog-scraper/cron.log"
echo "   3. 手动执行测试: cd /data/reddog-scraper && ./venv/bin/python nba-advanced-stats.py"
echo "============================================"