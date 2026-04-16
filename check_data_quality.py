#!/usr/bin/env python3
"""
检查数据质量，验证0-0比赛过滤逻辑
"""

import pandas as pd
import os

def check_data_quality():
    """检查数据文件质量和过滤逻辑"""
    data_dir = "/data/reddog-scraper"
    
    print("📊 NBA数据质量检查报告")
    print("=" * 50)
    
    # 检查nba_enriched_data.csv
    enriched_file = os.path.join(data_dir, "nba_enriched_data.csv")
    if not os.path.exists(enriched_file):
        print(f"❌ 文件不存在: {enriched_file}")
        return
    
    try:
        # 加载数据
        df = pd.read_csv(enriched_file)
        print(f"✅ 成功加载数据: {len(df)} 行, {len(df.columns)} 列")
        
        # 检查必要列
        required_columns = ['matchup', 'away_score', 'home_score']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            print(f"❌ 缺少必要列: {missing_cols}")
            print(f"📋 可用列: {list(df.columns)}")
        else:
            print(f"✅ 所有必要列都存在")
        
        # 统计0-0比赛
        zero_zero_games = df[(df['away_score'] == 0) & (df['home_score'] == 0)]
        non_zero_games = df[(df['away_score'] != 0) | (df['home_score'] != 0)]
        
        print(f"\n📊 比赛状态统计:")
        print(f"   0-0比赛（未开始）: {len(zero_zero_games)} 场 ({len(zero_zero_games)/len(df)*100:.1f}%)")
        print(f"   非0-0比赛（已开始/结束）: {len(non_zero_games)} 场 ({len(non_zero_games)/len(df)*100:.1f}%)")
        
        # 显示部分0-0比赛
        if len(zero_zero_games) > 0:
            print(f"\n🎯 未开始比赛示例 (前5场):")
            for idx, row in zero_zero_games.head(5).iterrows():
                print(f"   - {row['matchup']} (比分: {row['away_score']}-{row['home_score']})")
        
        # 显示部分已开始比赛
        if len(non_zero_games) > 0:
            print(f"\n⏰ 已开始/结束比赛示例 (前5场):")
            for idx, row in non_zero_games.head(5).iterrows():
                print(f"   - {row['matchup']} (比分: {row['away_score']}-{row['home_score']})")
        
        # 检查推荐系统会过滤掉的比赛
        print(f"\n🔍 推荐系统过滤逻辑验证:")
        print(f"   系统将分析: {len(zero_zero_games)} 场未开始比赛")
        print(f"   系统将跳过: {len(non_zero_games)} 场已开始/结束比赛")
        
        # 检查是否有市场数据列
        market_cols = [col for col in df.columns if 'spread' in col.lower() or 'total' in col.lower()]
        if market_cols:
            print(f"\n💰 发现市场数据列: {market_cols}")
        else:
            print(f"\n⚠️ 未发现市场数据列（盘口/总分）")
        
        # 检查数据时间范围（如果有日期列）
        date_cols = [col for col in df.columns if 'date' in col.lower()]
        if date_cols:
            print(f"\n📅 发现日期列: {date_cols}")
            for col in date_cols:
                unique_dates = df[col].dropna().unique()
                print(f"   {col}: {len(unique_dates)} 个唯一日期")
                if len(unique_dates) > 0:
                    print(f"     最早: {min(unique_dates)[:10]}, 最晚: {max(unique_dates)[:10]}")
        
    except Exception as e:
        print(f"❌ 数据检查失败: {e}")
    
    print(f"\n{'='*50}")
    print("✅ 数据质量检查完成")

if __name__ == "__main__":
    check_data_quality()