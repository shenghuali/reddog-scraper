#!/usr/bin/env python3
"""
修复 nba_total_recommender.py 的未开始比赛判断逻辑
"""

import re

# 读取原始文件
with open('/data/reddog-scraper/nba_total_recommender.py', 'r') as f:
    content = f.read()

# 查找并替换NaN判断逻辑
old_pattern = r'''            # 检查比赛是否未开始 - 使用比分NaN判断
            away_score = row\.get\('away_score'\)
            home_score = row\.get\('home_score'\)
            # 如果away_score或home_score不是NaN，说明比赛已开始或结束
            if not \(pd\.isna\(away_score\) and pd\.isna\(home_score\)\):
                # 比赛已开始或结束，跳过
                continue'''

new_content = '''            # 检查比赛是否未开始 - 正确逻辑：比分都是0
            away_score = row.get('away_score', 0)
            home_score = row.get('home_score', 0)
            # 如果away_score或home_score不是0，说明比赛已开始或结束
            if away_score != 0 or home_score != 0:
                # 比赛已开始或结束，跳过
                continue'''

# 执行替换
if old_pattern in content:
    content = content.replace(old_pattern, new_content)
    print("✅ 找到并替换了NaN判断逻辑")
else:
    # 尝试另一种模式
    content = content.replace(
        "if not (pd.isna(away_score) and pd.isna(home_score)):",
        "if away_score != 0 or home_score != 0:"
    )
    print("✅ 使用简化的替换模式")

# 写入修复后的文件
with open('/data/reddog-scraper/nba_total_recommender.py', 'w') as f:
    f.write(content)

print("✅ nba_total_recommender.py 修复完成")

# 验证修复
with open('/data/reddog-scraper/nba_total_recommender.py', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[160:180], 161):
        if 'away_score' in line or 'home_score' in line:
            print(f"第{i}行: {line.rstrip()}")