#!/bin/bash
# ============================================
# Docker重启后恢复脚本
# 保存位置: /data/reddog-scraper/restore-after-docker-restart.sh
# ============================================

echo "============================================"
echo "   Docker重启后恢复 - NBA数据抓取环境"
echo "   时间: $(date)"
echo "============================================"

# ========== 1. 设置墨尔本时区 ==========
echo ""
echo "🔧 步骤1: 设置墨尔本时区"
if [ -f /usr/share/zoneinfo/Australia/Melbourne ]; then
    ln -sf /usr/share/zoneinfo/Australia/Melbourne /etc/localtime 2>/dev/null
    echo "Australia/Melbourne" > /etc/timezone 2>/dev/null
    export TZ=Australia/Melbourne
    echo "✅ 时区已设置为: Australia/Melbourne"
    echo "   当前时间: $(date)"
else
    echo "⚠️  警告: 找不到墨尔本时区文件"
    echo "   请确保已安装时区数据: apt-get install tzdata"
fi

# ========== 2. 恢复crontab配置 ==========
echo ""
echo "🔧 步骤2: 恢复crontab定时任务"
BACKUP_FILE="/data/reddog-scraper/crontab-backup.txt"

if [ -f "$BACKUP_FILE" ]; then
    echo "📋 找到备份文件: $BACKUP_FILE"
    crontab "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ Crontab配置恢复成功"
        echo ""
        echo "📋 当前crontab配置:"
        echo "----------------------------------------"
        crontab -l
        echo "----------------------------------------"
    else
        echo "❌ Crontab恢复失败"
    fi
else
    echo "⚠️  警告: 未找到crontab备份文件"
    echo "   请先运行: crontab -l > /data/reddog-scraper/crontab-backup.txt"
    echo ""
    echo "📝 建议的crontab配置:"
    echo "----------------------------------------"
    cat << 'EOF'
TZ=Australia/Melbourne

# NBA数据抓取定时任务
0 9 * * * cd /data/reddog-scraper && /data/reddog-scraper/venv/bin/python nba-advanced-stats.py >> /data/reddog-scraper/cron.log 2>&1
0 10 * * * cd /data/reddog-scraper && /data/reddog-scraper/venv/bin/python nba-injury.py >> /data/reddog-scraper/cron.log 2>&1
0 11 * * * cd /data/reddog-scraper && /data/reddog-scraper/venv/bin/python nba-daily-odds.py >> /data/reddog-scraper/cron.log 2>&1
EOF
    echo "----------------------------------------"
fi

# ========== 3. 检查环境 ==========
echo ""
echo "🔧 步骤3: 检查Python环境"
if [ -d "/data/reddog-scraper/venv" ]; then
    echo "✅ Python虚拟环境存在: /data/reddog-scraper/venv/"
    
    # 测试venv中的Python
    if [ -f "/data/reddog-scraper/venv/bin/python" ]; then
        /data/reddog-scraper/venv/bin/python -c "import sys; print('✅ Python版本:', sys.version.split()[0])"
    fi
else
    echo "⚠️  警告: Python虚拟环境不存在"
    echo "   请检查 /data/reddog-scraper/venv/ 目录"
fi

# ========== 4. 检查脚本 ==========
echo ""
echo "🔧 步骤4: 检查NBA脚本"
SCRIPTS=("nba-advanced-stats.py" "nba-injury.py" "nba-daily-odds.py")
for script in "${SCRIPTS[@]}"; do
    if [ -f "/data/reddog-scraper/$script" ]; then
        echo "✅ $script 存在"
    else
        echo "❌ $script 不存在"
    fi
done

# ========== 5. 检查数据目录 ==========
echo ""
echo "🔧 步骤5: 检查数据目录"
if [ -d "/data/reddog-scraper" ]; then
    echo "✅ 数据目录存在: /data/reddog-scraper/"
    echo "   目录内容:"
    ls -la /data/reddog-scraper/*.py 2>/dev/null | wc -l | xargs echo "   Python脚本数量:"
    ls -la /data/reddog-scraper/*.csv 2>/dev/null | wc -l | xargs echo "   CSV数据文件数量:"
else
    echo "❌ 数据目录不存在!"
fi

# ========== 6. 完成 ==========
echo ""
echo "============================================"
echo "   恢复完成！"
echo "   下次重启后，运行此脚本恢复环境:"
echo "   bash /data/reddog-scraper/restore-after-docker-restart.sh"
echo "============================================"
echo ""
echo "📝 手动操作命令:"
echo "1. 编辑crontab: crontab -e"
echo "2. 查看crontab: crontab -l"
echo "3. 备份crontab: crontab -l > /data/reddog-scraper/crontab-backup.txt"
echo "4. 测试Python: /data/reddog-scraper/venv/bin/python -c 'import bs4; print(\"BeautifulSoup OK\")'"
echo ""