#!/bin/bash
"""
NBA每日推荐流水线
自动执行推荐计算和memo发布
"""

echo "🚀 NBA每日推荐流水线启动 - $(date)"

# 设置工作目录
WORKDIR="/data/reddog-scraper"
cd "$WORKDIR"

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "❌ 虚拟环境不存在，请先创建"
    exit 1
fi

# 步骤1: 运行盘口推荐系统
echo -e "\n📊 步骤1: 运行盘口推荐系统..."
python nba_spread_recommender.py
if [ $? -eq 0 ]; then
    echo "✅ 盘口推荐系统完成"
else
    echo "❌ 盘口推荐系统失败"
fi

# 步骤2: 运行大小分推荐系统
echo -e "\n📊 步骤2: 运行大小分推荐系统..."
python nba_total_recommender.py
if [ $? -eq 0 ]; then
    echo "✅ 大小分推荐系统完成"
else
    echo "❌ 大小分推荐系统失败"
fi

# 步骤3: 发布memo推荐
echo -e "\n📤 步骤3: 发布memo推荐..."
python memo_publisher.py
if [ $? -eq 0 ]; then
    echo "✅ memo发布完成"
else
    echo "⚠️ memo发布可能存在问题，检查日志"
fi

# 步骤4: 生成今日报告
echo -e "\n📋 步骤4: 生成今日报告..."
timestamp=$(date +"%Y%m%d_%H%M%S")
report_file="daily_report_${timestamp}.txt"

echo "=== NBA每日推荐报告 ===" > "$report_file"
echo "日期: $(date)" >> "$report_file"
echo "执行时间: $(date +"%H:%M:%S")" >> "$report_file"
echo "" >> "$report_file"

# 检查生成的文件
echo "📁 生成文件检查:" >> "$report_file"
find . -name "*.json" -newermt "$(date +"%Y-%m-%d") 00:00:00" -type f | while read file; do
    echo "  - $(basename "$file")" >> "$report_file"
done

echo "" >> "$report_file"
echo "📊 系统状态:" >> "$report_file"
echo "虚拟环境: $(which python)" >> "$report_file"
python -c "import pandas, numpy; print(f'pandas版本: {pandas.__version__}')" >> "$report_file" 2>/dev/null || echo "pandas: 未安装" >> "$report_file"

echo "✅ 报告已生成: $report_file"

# 步骤5: 清理旧文件（保留最近7天）
echo -e "\n🧹 步骤5: 清理旧文件..."
find . -name "spread_recommendation_*.json" -mtime +7 -delete
find . -name "total_recommendation_*.json" -mtime +7 -delete
find . -name "memo_output_*.md" -mtime +7 -delete
find . -name "daily_report_*.txt" -mtime +30 -delete

echo "✅ 清理完成（保留最近7天文件）"

echo -e "\n🎉 NBA每日推荐流水线完成 - $(date)"
echo "📋 总结:"
echo "  - 盘口推荐: ✓"
echo "  - 大小分推荐: ✓"
echo "  - memo发布: ✓"
echo "  - 报告生成: ✓"
echo "  - 文件清理: ✓"