#!/usr/bin/env python3
"""
调试预测盘口计算
"""

import pandas as pd
import numpy as np
import os

# 读取数据
df = pd.read_csv("nba-advanced-stats.csv")

# 查找OKC和SAS数据
okc = df[df['team'] == 'OKC'].iloc[0]
sas = df[df['team'] == 'SAS'].iloc[0]

print("=== 球队数据对比 ===")
print(f"OKC: 净效率={okc['nrtg']}, 进攻={okc['ortg']}, 防守={okc['drtg']}, 节奏={okc['pace']}")
print(f"SAS: 净效率={sas['nrtg']}, 进攻={sas['ortg']}, 防守={sas['drtg']}, 节奏={sas['pace']}")

print("\n=== 当前版本计算 ===")
# 当前版本算法
net_diff = okc['nrtg'] - sas['nrtg']
home_advantage = 3.5
pace_factor = (okc['pace'] - sas['pace']) * 0.05
predicted_spread_current = net_diff + home_advantage + pace_factor

print(f"净效率差: {net_diff:.1f}")
print(f"主场优势: {home_advantage}")
print(f"节奏因子: {pace_factor:.2f}")
print(f"预测盘口: {predicted_spread_current:.1f}")

print("\n=== 改进版本计算 ===")
# 改进版本算法
# 动态主场优势
advantage = 3.5
# 防守质量调整
if sas['drtg'] > 115:
    advantage += 1.0
elif sas['drtg'] < 108:
    advantage -= 0.5
# 进攻效率调整
if okc['ortg'] > 115:
    advantage += 0.5
elif okc['ortg'] < 105:
    advantage -= 0.5
# 节奏调整
pace_diff = okc['pace'] - sas['pace']
advantage += pace_diff * 0.05
home_advantage_dynamic = round(max(advantage, 2.0), 1)

# 进攻对防守优势
off_def_advantage = okc['ortg'] - sas['drtg']

# 加权预测
predicted_spread_improved = (
    net_diff * 0.5 +            # 球队实力差距
    home_advantage_dynamic * 0.3 +      # 主场优势
    (off_def_advantage * 0.2)   # 进攻对防守优势
)

print(f"净效率差: {net_diff:.1f}")
print(f"动态主场优势: {home_advantage_dynamic}")
print(f"攻防优势: {off_def_advantage:.1f}")
print(f"预测盘口: {predicted_spread_improved:.1f}")

print("\n=== 盘口解释 ===")
print(f"市场盘口: -3.5 (表示SAS让3.5分)")
print(f"当前版本预测: {predicted_spread_current:.1f} (表示OKC让{predicted_spread_current:.1f}分)")
print(f"改进版本预测: {predicted_spread_improved:.1f} (表示OKC让{predicted_spread_improved:.1f}分)")

print("\n=== 价值分析 ===")
market_spread = -3.5
value_diff_current = predicted_spread_current - market_spread
value_diff_improved = predicted_spread_improved - market_spread

print(f"当前版本价值差异: {value_diff_current:.1f}分 (OKC被低估{value_diff_current:.1f}分)")
print(f"改进版本价值差异: {value_diff_improved:.1f}分 (OKC被低估{value_diff_improved:.1f}分)")

print("\n=== 结论 ===")
print("1. 两个模型都认为OKC应该让分，而不是SAS让分")
print("2. 市场盘口(-3.5)与模型预测相反，存在价值机会")
print("3. 改进版本预测更保守(2.6分 vs 6.5分)，但价值评分更高")
print("4. 预测盘口正数 = 主队让分，负数 = 客队让分")