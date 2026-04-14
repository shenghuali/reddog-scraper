#!/usr/bin/env python3
"""
改进版NBA盘口推荐系统
- 动态主场优势计算
- 统计标准化价值评估
- 多因素加权预测
- 风险调整投注规模
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import os

class ImprovedNBASpreadRecommender:
    def __init__(self):
        self.data_dir = "/data/reddog-scraper"
        self.team_stats_df = None
        self.market_data_df = None
        self.player_data_df = None
        self.home_advantage_base = 3.5  # 基础主场优势
        
    def load_data(self) -> bool:
        """加载统计数据"""
        try:
            team_stats_path = os.path.join(self.data_dir, "nba-advanced-stats.csv")
            market_data_path = os.path.join(self.data_dir, "nba-daily-odds.csv")
            roster_path = os.path.join(self.data_dir, "nba-roster.csv")
            
            if os.path.exists(team_stats_path):
                self.team_stats_df = pd.read_csv(team_stats_path)
                print(f"✅ 加载球队统计: {len(self.team_stats_df)} 行")
            else:
                print(f"⚠️  球队统计文件不存在: {team_stats_path}")
                
            if os.path.exists(market_data_path):
                self.market_data_df = pd.read_csv(market_data_path)
                print(f"✅ 加载市场数据: {len(self.market_data_df)} 行")
            else:
                print(f"⚠️  市场数据文件不存在: {market_data_path}")
                
            if os.path.exists(roster_path):
                self.player_data_df = pd.read_csv(roster_path)
                print(f"✅ 加载球员数据: {len(self.player_data_df)} 行")
            else:
                print(f"⚠️  球员数据文件不存在: {roster_path}")
                
            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def calculate_dynamic_home_advantage(self, home_team: str, away_team: str) -> float:
        """计算动态主场优势"""
        if self.team_stats_df is None:
            return self.home_advantage_base
            
        home_stats = self.team_stats_df[self.team_stats_df['team'] == home_team]
        away_stats = self.team_stats_df[self.team_stats_df['team'] == away_team]
        
        if home_stats.empty or away_stats.empty:
            return self.home_advantage_base
            
        # 基础主场优势
        advantage = self.home_advantage_base
        
        # 1. 客场球队防守质量调整
        away_def_rating = away_stats['def_rating'].values[0] if 'def_rating' in away_stats else 110
        if away_def_rating > 115:  # 防守差
            advantage += 1.0
        elif away_def_rating < 108:  # 防守好
            advantage -= 0.5
            
        # 2. 主队进攻效率调整
        home_off_rating = home_stats['off_rating'].values[0] if 'off_rating' in home_stats else 110
        if home_off_rating > 115:  # 进攻强
            advantage += 0.5
        elif home_off_rating < 105:  # 进攻弱
            advantage -= 0.5
            
        # 3. 比赛节奏调整
        home_pace = home_stats['pace'].values[0] if 'pace' in home_stats else 100
        away_pace = away_stats['pace'].values[0] if 'pace' in away_stats else 100
        pace_diff = home_pace - away_pace
        advantage += pace_diff * 0.05  # 每10节奏差影响0.5分
        
        # 4. 旅行距离/背靠背调整 (简化版)
        # 可扩展: 从赛程数据获取
        
        return round(max(advantage, 2.0), 1)  # 最低2.0分优势
    
    def predict_spread(self, home_team: str, away_team: str) -> Optional[Dict]:
        """预测盘口 - 多因素加权"""
        if self.team_stats_df is None:
            print("❌ 统计数据未加载")
            return None
            
        home_stats = self.team_stats_df[self.team_stats_df['team'] == home_team]
        away_stats = self.team_stats_df[self.team_stats_df['team'] == away_team]
        
        if home_stats.empty or away_stats.empty:
            print(f"⚠️  找不到球队数据: {home_team} 或 {away_team}")
            return None
            
        # 提取关键指标
        home_net = home_stats['net_rating'].values[0]
        away_net = away_stats['net_rating'].values[0]
        net_diff = home_net - away_net
        
        # 动态主场优势
        home_advantage = self.calculate_dynamic_home_advantage(home_team, away_team)
        
        # 进攻对防守优势
        home_off = home_stats['off_rating'].values[0] if 'off_rating' in home_stats else 110
        away_def = away_stats['def_rating'].values[0] if 'def_rating' in away_stats else 110
        off_def_advantage = home_off - away_def
        
        # 防守对进攻优势
        home_def = home_stats['def_rating'].values[0] if 'def_rating' in home_stats else 110
        away_off = away_stats['off_rating'].values[0] if 'off_rating' in away_stats else 110
        def_off_advantage = away_off - home_def  # 负值表示防守优势
        
        # 多因素加权预测
        # 权重: 净效率50%, 主场优势30%, 攻防匹配20%
        predicted_spread = (
            net_diff * 0.5 +            # 球队实力差距
            home_advantage * 0.3 +      # 主场优势
            (off_def_advantage * 0.2)   # 进攻对防守优势
        )
        
        # 计算置信度
        home_games = home_stats['games_played'].values[0] if 'games_played' in home_stats else 0
        away_games = away_stats['games_played'].values[0] if 'games_played' in away_stats else 0
        min_games = min(home_games, away_games)
        
        data_quality = min(min_games / 20.0, 1.0)  # 20场比赛达到完全可信
        consistency = 0.8  # 基础一致性
        
        confidence = 0.4 + (data_quality * 0.3) + (consistency * 0.3)
        confidence = min(confidence, 0.95)
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'net_rating_diff': round(net_diff, 1),
            'home_advantage': home_advantage,
            'off_def_advantage': round(off_def_advantage, 1),
            'def_off_advantage': round(def_off_advantage, 1),
            'predicted_spread': round(predicted_spread, 1),
            'confidence': round(confidence, 2)
        }
    
    def analyze_value(self, prediction: Dict, market_spread: float) -> Dict:
        """价值分析 - 统计标准化"""
        if not prediction:
            return {}
            
        predicted = prediction['predicted_spread']
        market = market_spread
        
        # 价值差异
        value_diff = predicted - market
        
        # 计算标准误 (基于信心和样本量)
        confidence = prediction['confidence']
        std_error = (1.0 - confidence) * 3.0  # 信心越低，标准误越大
        
        # 标准化价值 (Z-score)
        if std_error > 0:
            z_score = abs(value_diff) / std_error
        else:
            z_score = abs(value_diff) / 2.0
            
        # 价值评分 (0-100)
        if z_score < 0.5:
            value_score = 0
        elif z_score < 1.0:
            value_score = 25
        elif z_score < 1.5:
            value_score = 50
        elif z_score < 2.0:
            value_score = 75
        else:
            value_score = 100
            
        # 调整价值评分 (考虑极端值风险)
        if abs(value_diff) > 8.0:
            value_score = max(0, value_score - 20)  # 极端差异降低可信度
            
        # 推荐方向
        if value_diff > 0:
            recommendation = "主队让分"  # 预测 > 市场，主队被低估
            side = "home"
        else:
            recommendation = "客队受让"  # 预测 < 市场，客队被低估
            side = "away"
            
        return {
            'predicted_spread': predicted,
            'market_spread': market,
            'value_diff': round(value_diff, 1),
            'z_score': round(z_score, 2),
            'value_score': value_score,
            'recommendation': recommendation,
            'side': side,
            'confidence': confidence
        }
    
    def calculate_bet_size(self, value_score: int, confidence: float, risk_tolerance: float = 0.5) -> float:
        """计算投注规模 (风险调整)"""
        # 基础规模: 价值评分/100
        base_size = value_score / 100.0
        
        # 信心调整
        confidence_adjustment = confidence * 0.5
        
        # 风险容忍度调整
        risk_adjustment = risk_tolerance * 0.5
        
        # 综合规模 (最大5%)
        bet_size = base_size * confidence_adjustment * risk_adjustment
        bet_size = min(bet_size, 0.05)  # 最大5%
        bet_size = max(bet_size, 0.01)  # 最小1%
        
        return round(bet_size, 3)
    
    def generate_recommendation(self, home_team: str, away_team: str, market_spread: float) -> Dict:
        """生成完整推荐"""
        # 预测
        prediction = self.predict_spread(home_team, away_team)
        if not prediction:
            return {}
            
        # 价值分析
        value_analysis = self.analyze_value(prediction, market_spread)
        if not value_analysis:
            return {}
            
        # 投注规模
        bet_size = self.calculate_bet_size(
            value_analysis['value_score'],
            value_analysis['confidence']
        )
        
        # 生成理由
        reasoning = self.generate_reasoning(prediction, value_analysis)
        
        recommendation = {
            'matchup': f"{home_team} vs {away_team}",
            'date': datetime.now().strftime("%Y-%m-%d"),
            'market_spread': market_spread,
            'prediction': prediction,
            'value_analysis': value_analysis,
            'betting_advice': {
                'action': value_analysis['recommendation'],
                'side': value_analysis['side'],
                'value_score': value_analysis['value_score'],
                'confidence': '高' if value_analysis['confidence'] > 0.8 else '中' if value_analysis['confidence'] > 0.6 else '低',
                'bet_size_percent': round(bet_size * 100, 1),
                'reasoning': reasoning
            }
        }
        
        return recommendation
    
    def generate_reasoning(self, prediction: Dict, value_analysis: Dict) -> str:
        """生成推荐理由"""
        reasons = []
        
        # 实力差距
        net_diff = prediction['net_rating_diff']
        if abs(net_diff) > 5:
            reasons.append(f"球队实力差距显著 (净效率差: {net_diff:.1f})")
        elif abs(net_diff) > 2:
            reasons.append(f"球队实力存在差距 (净效率差: {net_diff:.1f})")
        else:
            reasons.append(f"球队实力相近 (净效率差: {net_diff:.1f})")
            
        # 主场优势
        home_advantage = prediction['home_advantage']
        if home_advantage > 4.0:
            reasons.append(f"有利的主场条件 (优势: {home_advantage}分)")
        elif home_advantage < 3.0:
            reasons.append(f"主场优势有限 (优势: {home_advantage}分)")
        else:
            reasons.append(f"标准主场优势 (优势: {home_advantage}分)")
            
        # 价值评估
        value_diff = value_analysis['value_diff']
        z_score = value_analysis['z_score']
        
        if abs(value_diff) > 3.0 and z_score > 1.0:
            reasons.append(f"显著的统计价值 (差异: {value_diff:.1f}, Z-score: {z_score:.2f})")
        elif abs(value_diff) > 1.5:
            reasons.append(f"适度的统计价值 (差异: {value_diff:.1f}, Z-score: {z_score:.2f})")
        else:
            reasons.append(f"有限的统计价值 (差异: {value_diff:.1f}, Z-score: {z_score:.2f})")
            
        return " | ".join(reasons)
    
    def run_analysis(self, matchups: List[Dict]) -> List[Dict]:
        """批量分析比赛"""
        recommendations = []
        
        if not self.load_data():
            print("❌ 数据加载失败，无法进行分析")
            return recommendations
            
        for matchup in matchups:
            home_team = matchup.get('home_team')
            away_team = matchup.get('away_team')
            market_spread = matchup.get('market_spread')
            
            if not all([home_team, away_team, market_spread]):
                continue
                
            print(f"分析: {home_team} vs {away_team} (市场盘口: {market_spread})")
            recommendation = self.generate_recommendation(home_team, away_team, market_spread)
            
            if recommendation:
                recommendations.append(recommendation)
                
        return recommendations

# 使用示例
if __name__ == "__main__":
    recommender = ImprovedNBASpreadRecommender()
    
    # 测试比赛
    test_matchups = [
        {'home_team': 'Los Angeles Lakers', 'away_team': 'Golden State Warriors', 'market_spread': -3.5},
        {'home_team': 'Boston Celtics', 'away_team': 'Milwaukee Bucks', 'market_spread': -1.5}
    ]
    
    recommendations = recommender.run_analysis(test_matchups)
    
    for rec in recommendations:
        print(f"\n{'='*50}")
        print(f"比赛: {rec['matchup']}")
        print(f"市场盘口: {rec['market_spread']}")
        print(f"预测盘口: {rec['prediction']['predicted_spread']}")
        print(f"价值评分: {rec['value_analysis']['value_score']}/100")
        print(f"推荐: {rec['betting_advice']['action']}")
        print(f"投注规模: {rec['betting_advice']['bet_size_percent']}%")
        print(f"理由: {rec['betting_advice']['reasoning']}")
        print(f"{'='*50}")