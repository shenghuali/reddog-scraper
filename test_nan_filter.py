#!/usr/bin/env python3
"""
测试NaN过滤逻辑是否正确
"""

import pandas as pd
import numpy as np

def test_nan_logic():
    """测试NaN判断逻辑"""
    print("🧪 测试NaN过滤逻辑")
    print("=" * 50)
    
    # 创建测试数据
    test_data = [
        {"matchup": "BOS vs GSW", "away_score": np.nan, "home_score": np.nan, "spread_line": -5.5, "total_line": 225.5},
        {"matchup": "LAL vs DEN", "away_score": 105.0, "home_score": 110.0, "spread_line": -2.5, "total_line": 220.5},
        {"matchup": "PHX vs DAL", "away_score": np.nan, "home_score": np.nan, "spread_line": -1.5, "total_line": 230.5},
        {"matchup": "MIA vs NYK", "away_score": 98.0, "home_score": np.nan, "spread_line": -3.5, "total_line": 215.5},
        {"matchup": "CLE vs CHI", "away_score": np.nan, "home_score": 102.0, "spread_line": -4.5, "total_line": 210.5},
        {"matchup": "OKC vs UTA", "away_score": 0.0, "home_score": 0.0, "spread_line": -6.5, "total_line": 235.5},
    ]
    
    df = pd.DataFrame(test_data)
    
    print("📊 测试数据:")
    print(df.to_string())
    
    print("\n🎯 应用NaN过滤逻辑:")
    for idx, row in df.iterrows():
        away_score = row.get('away_score')
        home_score = row.get('home_score')
        
        # 新逻辑：两个比分都是NaN = 未开始比赛
        is_upcoming = pd.isna(away_score) and pd.isna(home_score)
        
        # 旧逻辑：两个比分都是0 = 未开始比赛
        is_zero_zero = away_score == 0 and home_score == 0
        
        print(f"\n比赛: {row['matchup']}")
        print(f"  比分: {away_score}-{home_score}")
        print(f"  NaN判断 (新): {'未开始' if is_upcoming else '已开始/结束'}")
        print(f"  0-0判断 (旧): {'未开始' if is_zero_zero else '已开始/结束'}")
        print(f"  市场数据: 让分 {row['spread_line']}, 总分 {row['total_line']}")
    
    print("\n" + "=" * 50)
    print("✅ 逻辑测试完成")
    print("\n📋 结论:")
    print("  - NaN判断：away_score和home_score都是NaN → 未开始比赛")
    print("  - 0-0判断：away_score和home_score都是0 → 未开始比赛（错误）")
    print("  - 实际数据中，未开始比赛的比分应该是NaN，不是0")

if __name__ == "__main__":
    test_nan_logic()