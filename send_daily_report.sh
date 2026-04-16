#!/bin/bash
# 发送每日报告到Discord

# 1. 生成报告
cd /Users/shenghuali/reddog-scraper
./daily_cron_report.sh > /tmp/daily_report_$(date +%Y%m%d_%H%M%S).txt

# 2. 提取报告内容
REPORT_FILE="/tmp/daily_report_latest.txt"
./daily_cron_report.sh | tail -n +2 > "$REPORT_FILE"

# 3. 通过OpenClaw工具发送到Discord
if command -v python3 >/dev/null 2>&1; then
    echo "通过OpenClaw消息工具发送..."
    
    # 发送到Discord频道
    python3 -c "
import sys
import subprocess

# 读取报告内容
with open('$REPORT_FILE', 'r', encoding='utf-8') as f:
    content = f.read()

# Discord消息有2000字符限制
if len(content) > 1900:
    content = content[:1900] + '\\n... [消息太长，已截断]'

# 准备消息
message = f'📊 NBA数据抓取系统 - 每日执行报告\\n生成时间: $(date '+%Y-%m-%d %H:%M') (墨尔本时间)\\n\\n' + content

# 尝试通过OpenClaw工具发送
try:
    # 使用message工具发送到Discord
    import json
    import subprocess
    
    cmd = ['openclaw', 'message', 'send', '--action', 'send', '--channel', 'discord', '--message', message]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print('✅ 报告已发送到Discord')
    else:
        print('⚠️ OpenClaw CLI发送失败，尝试备用方法...')
        print('错误:', result.stderr)
        
        # 备用方法：直接通过当前的session发送
        print('📋 报告内容已保存到: $REPORT_FILE')
        print('💡 请手动复制或使用其他方式发送')
        
except Exception as e:
    print(f'❌ 发送失败: {e}')
    print('📋 报告内容已保存到: $REPORT_FILE')
" 2>&1
else
    echo "❌ Python不可用，无法发送报告"
    echo "📋 报告内容已保存到: $REPORT_FILE"
fi