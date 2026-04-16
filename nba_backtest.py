#!/usr/bin/env python3
"""
NBA推荐系统历史回测
- 测试盘口推荐胜率
- 测试总分推荐胜率
- 使用历史已完赛数据
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import sys
import os

# 添加当前目录到路径，以便导入推荐器
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nba_spread_recommender import SpreadRecommender
from nba_total_recommender import TotalRecommender


class NBABacktester:
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.dirname(os.path.abspath(__file__))
        self.spread_recommender = SpreadRecommender(data_dir)
        self.total_recommender = TotalRecommender(data_dir)
        
    def load_data(self) -> bool:
        """加载数据"""
        if not self.spread_recommender.load_data():
            return False
        if not self.total_recommender.load_data():
            return False
        return True
    
    def backtest_spread(self, season: str = "2025-2026") -> Dict:
        """回测盘口推荐系统"""
        print("🏀 开始盘口推荐系统回测...")
        
        df = self.spread_recommender.market_data_df
        if df is None:
            return {"error": "市场数据未加载"}
        
        # 筛选本赛季已完成比赛
        if 'season' in df.columns:
            df = df[df['season'] == season]
        else:
            # 如果没有赛季字段，使用日期筛选（假设本赛季是最近的数据）
            df = df[df['date'] >= '2025-10-01']
        
        # 确保有比分
        df = df[(df['home_score'].notna()) & (df['away_score'].notna())]
        
        print(f"📊 分析 {len(df)} 场本赛季比赛")
        
        results = []
        total_games = 0
        correct_predictions = 0
        total_edge = 0
        
        for idx, game in df.iterrows():
            try:
                home = game.get('home_team') or game.get('home', '')
                away = game.get('away_team') or game.get('away', '')
                
                if not home or not away:
                    continue
                
                # 获取市场盘口（使用 close_spread）
                market_spread = game.get('close_spread')
                if pd.isna(market_spread):
                    market_spread = game.get('open_spread')
                if pd.isna(market_spread):
                    continue
                
                # 生成预测
                prediction = self.spread_recommender.predict_spread(home, away)
                if not prediction:
                    continue
                
                # 获取实际结果
                home_score = float(game['home_score'])
                away_score = float(game['away_score'])
                actual_margin = home_score - away_score
                
                # 判断预测是否正确
                predicted_margin = prediction['predicted_margin']
                market_spread_float = float(market_spread)
                
                # 实际盘口结果：主队得分 - 客队得分 - 盘口
                actual_ats_result = actual_margin - market_spread_float
                
                # 预测盘口结果：预测净胜分 - 盘口
                predicted_ats_result = predicted_margin - market_spread_float
                
                # 判断是否预测正确（符号相同）
                is_correct = (actual_ats_result * predicted_ats_result) > 0
                
                # 计算 edge（预测净胜分 - 市场盘口）
                edge = predicted_margin - market_spread_float
                
                results.append({
                    'game': f"{home} vs {away}",
                    'date': game.get('date', ''),
                    'market_spread': market_spread_float,
                    'predicted_margin': round(predicted_margin, 1),
                    'actual_margin': round(actual_margin, 1),
                    'edge': round(edge, 1),
                    'is_correct': is_correct,
                    'home_score': home_score,
                    'away_score': away_score
                })
                
                total_games += 1
                if is_correct:
                    correct_predictions += 1
                total_edge += abs(edge)
                
                # 每100场比赛打印一次进度
                if total_games % 100 == 0:
                    print(f"  已分析 {total_games} 场比赛...")
                    
            except Exception as e:
                continue
        
        if total_games == 0:
            return {"error": "没有可分析的数据"}
        
        win_rate = correct_predictions / total_games
        avg_edge = total_edge / total_games
        
        print(f"✅ 盘口回测完成:")
        print(f"   总比赛数: {total_games}")
        print(f"   正确预测: {correct_predictions}")
        print(f"   胜率: {win_rate:.1%}")
        print(f"   平均Edge: {avg_edge:.2f}")
        
        return {
            "total_games": total_games,
            "correct_predictions": correct_predictions,
            "win_rate": win_rate,
            "avg_edge": avg_edge,
            "results": results[:50]  # 只返回前50条记录
        }
    
    def backtest_total(self, season: str = "2025-2026") -> Dict:
        """回测总分推荐系统"""
        print("\n🏀 开始总分推荐系统回测...")
        
        df = self.total_recommender.market_data_df
        if df is None:
            return {"error": "市场数据未加载"}
        
        # 筛选本赛季已完成比赛
        if 'season' in df.columns:
            df = df[df['season'] == season]
        else:
            df = df[df['date'] >= '2025-10-01']
        
        # 确保有比分
        df = df[(df['home_score'].notna()) & (df['away_score'].notna())]
        
        print(f"📊 分析 {len(df)} 场本赛季比赛")
        
        results = []
        total_games = 0
        correct_predictions = 0
        total_value_diff = 0
        
        for idx, game in df.iterrows():
            try:
                home = game.get('home_team') or game.get('home', '')
                away = game.get('away_team') or game.get('away', '')
                
                if not home or not away:
                    continue
                
                # 获取市场总分（使用 close_total）
                market_total = game.get('close_total')
                if pd.isna(market_total):
                    market_total = game.get('open_total')
                if pd.isna(market_total):
                    continue
                
                # 生成预测
                prediction = self.total_recommender.calculate_expected_total(home, away)
                if not prediction:
                    continue
                
                # 获取实际结果
                home_score = float(game['home_score'])
                away_score = float(game['away_score'])
                actual_total = home_score + away_score
                
                # 判断预测是否正确
                predicted_total = prediction['predicted_total']
                market_total_float = float(market_total)
                
                # 实际总分结果：实际总分 vs 市场总分
                actual_over_under = actual_total - market_total_float
                
                # 预测总分结果：预测总分 vs 市场总分
                predicted_over_under = predicted_total - market_total_float
                
                # 判断是否预测正确（符号相同）
                is_correct = (actual_over_under * predicted_over_under) > 0
                
                # 计算价值差异
                value_diff = predicted_total - market_total_float
                
                results.append({
                    'game': f"{home} vs {away}",
                    'date': game.get('date', ''),
                    'market_total': market_total_float,
                    'predicted_total': round(predicted_total, 1),
                    'actual_total': round(actual_total, 1),
                    'value_diff': round(value_diff, 1),
                    'is_correct': is_correct,
                    'home_score': home_score,
                    'away_score': away_score
                })
                
                total_games += 1
                if is_correct:
                    correct_predictions += 1
                total_value_diff += abs(value_diff)
                
                # 每100场比赛打印一次进度
                if total_games % 100 == 0:
                    print(f"  已分析 {total_games} 场比赛...")
                    
            except Exception as e:
                continue
        
        if total_games == 0:
            return {"error": "没有可分析的数据"}
        
        win_rate = correct_predictions / total_games
        avg_value_diff = total_value_diff / total_games
        
        print(f"✅ 总分回测完成:")
        print(f"   总比赛数: {total_games}")
        print(f"   正确预测: {correct_predictions}")
        print(f"   胜率: {win_rate:.1%}")
        print(f"   平均价值差异: {avg_value_diff:.2f}")
        
        return {
            "total_games": total_games,
            "correct_predictions": correct_predictions,
            "win_rate": win_rate,
            "avg_value_diff": avg_value_diff,
            "results": results[:50]
        }
    
    def run_backtest(self, season: str = "2025-2026"):
        """运行完整回测"""
        print("=" * 60)
        print("🏀 NBA推荐系统历史回测")
        print("=" * 60)
        
        if not self.load_data():
            print("❌ 数据加载失败")
            return
        
        # 盘口回测
        spread_results = self.backtest_spread(season)
        
        # 总分回测
        total_results = self.backtest_total(season)
        
        print("\n" + "=" * 60)
        print("📈 回测总结")
        print("=" * 60)
        
        if 'win_rate' in spread_results:
            print(f"盘口推荐系统:")
            print(f"  • 胜率: {spread_results['win_rate']:.1%} ({spread_results['correct_predictions']}/{spread_results['total_games']})")
            print(f"  • 平均Edge: {spread_results['avg_edge']:.2f}")
        
        if 'win_rate' in total_results:
            print(f"总分推荐系统:")
            print(f"  • 胜率: {total_results['win_rate']:.1%} ({total_results['correct_predictions']}/{total_results['total_games']})")
            print(f"  • 平均价值差异: {total_results['avg_value_diff']:.2f}")
        
        print("\n📝 注:")
        print("1. 回测基于本赛季所有已完赛比赛")
        print("2. 胜率 > 52.4% 才可能长期盈利（考虑抽水）")
        print("3. Edge/价值差异越大，潜在利润空间越大")


def main():
    backtester = NBABacktester()
    backtester.run_backtest()


if __name__ == "__main__":
    main()