#!/bin/bash
# ============================================
# 添加新Cron Job辅助脚本
# ============================================

echo "============================================"
echo "   添加新Cron Job"
echo "============================================"

# 获取新任务信息
read -p "📝 任务名称: " TASK_NAME
read -p "📝 脚本文件名 (例如: my-task.py): " SCRIPT_FILE
read -p "📝 Cron时间表达式 (例如: 0 * * * *): " CRON_EXPR
read -p "📝 任务描述: " TASK_DESC

# 检查脚本是否存在
SCRIPT_PATH="/data/reddog-scraper/$SCRIPT_FILE"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo ""
    echo "⚠️  脚本文件不存在: $SCRIPT_PATH"
    read -p "是否创建空脚本文件? (y/n): " CREATE_SCRIPT
    if [ "$CREATE_SCRIPT" = "y" ]; then
        cat > "$SCRIPT_PATH" << EOF
#!/usr/bin/env python3
"""
$TASK_NAME - $TASK_DESC
"""

print("$TASK_NAME 执行中...")
# 在这里添加你的代码

print("$TASK_NAME 完成")
EOF
        chmod +x "$SCRIPT_PATH"
        echo "✅ 已创建脚本: $SCRIPT_PATH"
    else
        echo "❌ 脚本不存在，无法添加任务"
        exit 1
    fi
fi

# 检查脚本权限
if [ ! -x "$SCRIPT_PATH" ]; then
    echo "设置脚本执行权限..."
    chmod +x "$SCRIPT_PATH"
fi

# 添加到crontab模板
echo ""
echo "📋 添加到crontab模板..."
echo "" >> /data/reddog-scraper/crontab-template.txt
echo "# $TASK_NAME - $TASK_DESC" >> /data/reddog-scraper/crontab-template.txt
echo "$CRON_EXPR cd /data/reddog-scraper && /data/reddog-scraper/venv/bin/python $SCRIPT_FILE >> /data/reddog-scraper/cron.log 2>&1" >> /data/reddog-scraper/crontab-template.txt

# 应用新配置
echo "🔄 应用新配置..."
crontab /data/reddog-scraper/crontab-template.txt

# 备份配置
echo "💾 备份配置..."
crontab -l > /data/reddog-scraper/crontab-backup.txt

# 验证
echo ""
echo "✅ 新任务已添加!"
echo ""
echo "📊 任务详情:"
echo "   名称: $TASK_NAME"
echo "   脚本: $SCRIPT_FILE"
echo "   时间: $CRON_EXPR"
echo "   描述: $TASK_DESC"
echo ""
echo "📋 当前crontab配置:"
echo "----------------------------------------"
crontab -l | tail -5
echo "----------------------------------------"
echo ""
echo "🚀 下一步操作:"
echo "   1. 测试脚本: cd /data/reddog-scraper && ./venv/bin/python $SCRIPT_FILE"
echo "   2. 查看日志: tail -f /data/reddog-scraper/cron.log"
echo "   3. 运行状态检查: bash check_system_status.sh"
echo ""
echo "📝 文档更新建议:"
echo "   更新 CRONTAB_README.md 和 QUICK_START.md 文档"
echo "============================================"