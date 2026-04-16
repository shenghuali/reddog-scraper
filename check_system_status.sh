#!/bin/bash
# ============================================
# NBA数据抓取系统状态检查脚本
# ============================================

echo "============================================"
echo "   NBA数据抓取系统状态检查"
echo "   检查时间: $(date)"
echo "============================================"

# ========== 1. 系统基础状态 ==========
echo ""
echo "🔧 1. 系统基础状态"
echo "----------------------------------------"

# 时区检查
echo "时区状态:"
echo "  当前时间: $(date)"
echo "  系统时区: $(cat /etc/timezone 2>/dev/null || echo '未设置')"
echo "  时区文件: $(readlink -f /etc/localtime 2>/dev/null || echo '未设置')"

# 磁盘空间
echo "磁盘空间:"
df -h /data/reddog-scraper/ 2>/dev/null | tail -1 | awk '{print "  挂载点: "$6", 可用: "$4", 使用率: "$5}'

# ========== 2. Crontab状态 ==========
echo ""
echo "🔧 2. Crontab定时任务状态"
echo "----------------------------------------"

# 检查cron服务
if command -v service >/dev/null 2>&1; then
    service cron status 2>/dev/null | grep -E "(Active|running)" || echo "  ❌ Cron服务可能未运行"
else
    echo "  ℹ️  无法检查cron服务状态"
fi

# 显示当前crontab配置
echo "当前crontab配置:"
crontab -l 2>/dev/null | while read line; do
    echo "  $line"
done

if [ $? -ne 0 ]; then
    echo "  ❌ 无crontab配置"
fi

# 检查备份文件
echo "配置备份:"
if [ -f "/data/reddog-scraper/crontab-backup.txt" ]; then
    BACKUP_LINES=$(wc -l < /data/reddog-scraper/crontab-backup.txt)
    echo "  ✅ 备份文件存在 ($BACKUP_LINES 行)"
else
    echo "  ❌ 备份文件不存在"
fi

# ========== 3. Python环境状态 ==========
echo ""
echo "🔧 3. Python环境状态"
echo "----------------------------------------"

# 检查venv
if [ -d "/data/reddog-scraper/venv" ]; then
    echo "  ✅ Python虚拟环境存在"
    
    # 检查Python可执行文件
    if [ -f "/data/reddog-scraper/venv/bin/python" ]; then
        PYTHON_VERSION=$(/data/reddog-scraper/venv/bin/python -c "import sys; print(sys.version.split()[0])" 2>/dev/null)
        echo "  ✅ Python版本: $PYTHON_VERSION"
        
        # 检查关键依赖
        echo "  依赖检查:"
        /data/reddog-scraper/venv/bin/python -c "
try:
    import bs4
    print('    ✅ BeautifulSoup4')
except ImportError:
    print('    ❌ BeautifulSoup4')

try:
    import pandas
    print('    ✅ pandas')
except ImportError:
    print('    ❌ pandas')

try:
    import requests
    print('    ✅ requests')
except ImportError:
    print('    ❌ requests')
" 2>/dev/null
    else
        echo "  ❌ Python可执行文件不存在"
    fi
else
    echo "  ❌ Python虚拟环境不存在"
fi

# ========== 4. 脚本文件状态 ==========
echo ""
echo "🔧 4. 脚本文件状态"
echo "----------------------------------------"

SCRIPTS=(
    "nba-injury.py"
    "nba-daily-odds.py" 
    "nba-advanced-stats.py"
    "sync_to_enriched.py"
    "daily_odds_with_sync.sh"
    "restore-after-docker-restart.sh"
    "setup-nba-cron.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "/data/reddog-scraper/$script" ]; then
        PERM=$(stat -c "%A" "/data/reddog-scraper/$script" 2>/dev/null || echo "未知")
        SIZE=$(stat -c "%s" "/data/reddog-scraper/$script" 2>/dev/null || echo "0")
        echo "  ✅ $script (权限: $PERM, 大小: ${SIZE}字节)"
    else
        echo "  ❌ $script 不存在"
    fi
done

# ========== 5. 数据文件状态 ==========
echo ""
echo "🔧 5. 数据文件状态"
echo "----------------------------------------"

DATA_FILES=(
    "nba-injury-latest.csv"
    "nba-daily-odds.csv"
    "nba_enriched_data.csv"
    "nba-advanced-stats.csv"
)

for datafile in "${DATA_FILES[@]}"; do
    if [ -f "/data/reddog-scraper/$datafile" ]; then
        LINES=$(wc -l < "/data/reddog-scraper/$datafile" 2>/dev/null || echo "0")
        MOD_TIME=$(stat -c "%y" "/data/reddog-scraper/$datafile" 2>/dev/null | cut -d'.' -f1 || echo "未知")
        SIZE=$(stat -c "%s" "/data/reddog-scraper/$datafile" 2>/dev/null || echo "0")
        echo "  ✅ $datafile"
        echo "     行数: $LINES, 大小: ${SIZE}字节, 修改: $MOD_TIME"
    else
        echo "  ⚠️  $datafile 不存在"
    fi
done

# ========== 6. 日志文件状态 ==========
echo ""
echo "🔧 6. 日志文件状态"
echo "----------------------------------------"

LOG_FILES=(
    "cron.log"
    "error.log"
    "status.log"
)

for logfile in "${LOG_FILES[@]}"; do
    if [ -f "/data/reddog-scraper/$logfile" ]; then
        LINES=$(wc -l < "/data/reddog-scraper/$logfile" 2>/dev/null || echo "0")
        SIZE=$(stat -c "%s" "/data/reddog-scraper/$logfile" 2>/dev/null || echo "0")
        if [ "$logfile" = "error.log" ] && [ "$LINES" -gt 0 ]; then
            echo "  ⚠️  $logfile (有 $LINES 行错误日志)"
            echo "     最后5行错误:"
            tail -5 "/data/reddog-scraper/$logfile" | while read line; do
                echo "     $line"
            done
        else
            echo "  ✅ $logfile ($LINES 行, ${SIZE}字节)"
        fi
    else
        if [ "$logfile" = "error.log" ]; then
            echo "  ✅ $logfile 不存在 (无错误)"
        else
            echo "  ⚠️  $logfile 不存在"
        fi
    fi
done

# ========== 7. 备份目录状态 ==========
echo ""
echo "🔧 7. 备份目录状态"
echo "----------------------------------------"

if [ -d "/data/reddog-scraper/backup" ]; then
    BACKUP_COUNT=$(find /data/reddog-scraper/backup -name "*.tar.gz" -type f 2>/dev/null | wc -l)
    echo "  ✅ 备份目录存在 ($BACKUP_COUNT 个备份文件)"
    
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        echo "  最新备份:"
        find /data/reddog-scraper/backup -name "*.tar.gz" -type f -exec ls -lh {} \; 2>/dev/null | head -3 | while read line; do
            echo "     $line"
        done
    fi
else
    echo "  ⚠️  备份目录不存在"
fi

# ========== 8. 汇总报告 ==========
echo ""
echo "============================================"
echo "   状态检查完成"
echo "============================================"

echo ""
echo "📊 汇总报告:"
echo "   1. 系统基础: $(if [ -f /etc/timezone ] && grep -q Melbourne /etc/timezone 2>/dev/null; then echo '✅'; else echo '⚠️ '; fi)"
echo "   2. Crontab配置: $(if crontab -l >/dev/null 2>&1; then echo '✅'; else echo '❌'; fi)"
echo "   3. Python环境: $(if [ -f /data/reddog-scraper/venv/bin/python ]; then echo '✅'; else echo '❌'; fi)"
echo "   4. 脚本文件: $(if [ -f /data/reddog-scraper/nba-injury.py ]; then echo '✅'; else echo '⚠️ '; fi)"
echo "   5. 数据文件: $(if [ -f /data/reddog-scraper/nba-injury-latest.csv ]; then echo '✅'; else echo '⚠️ '; fi)"
echo "   6. 日志系统: $(if [ -f /data/reddog-scraper/cron.log ]; then echo '✅'; else echo '⚠️ '; fi)"
echo "   7. 备份系统: $(if [ -d /data/reddog-scraper/backup ]; then echo '✅'; else echo '⚠️ '; fi)"

echo ""
echo "🚀 建议操作:"

# 检查时区
if ! date | grep -q "AEDT\|AEST"; then
    echo "   1. 设置墨尔本时区:"
    echo "      ln -sf /usr/share/zoneinfo/Australia/Melbourne /etc/localtime"
    echo "      echo 'Australia/Melbourne' > /etc/timezone"
fi

# 检查crontab
if ! crontab -l >/dev/null 2>&1; then
    echo "   2. 设置crontab:"
    echo "      crontab /data/reddog-scraper/crontab-final-schedule.txt"
fi

# 检查备份
if [ ! -f "/data/reddog-scraper/crontab-backup.txt" ]; then
    echo "   3. 备份crontab配置:"
    echo "      crontab -l > /data/reddog-scraper/crontab-backup.txt"
fi

# 检查错误日志
if [ -f "/data/reddog-scraper/error.log" ] && [ -s "/data/reddog-scraper/error.log" ]; then
    echo "   4. 检查错误日志:"
    echo "      cat /data/reddog-scraper/error.log"
fi

echo ""
echo "📝 详细文档:"
echo "   - 完整指南: CRONTAB_README.md"
echo "   - 快速启动: QUICK_START.md"
echo "   - 恢复脚本: restore-after-docker-restart.sh"
echo ""
echo "============================================"