#!/usr/bin/env python3
"""
NBA盘口推荐系统 - 当前版本 (修复路径)
基于球队效率数据、市场数据、情境因素
输出盘口价值投注推荐
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, Tuple, Optional
import json

class SpreadRecommender:
    def __init__(self):
        self.data_dir = "."  # 修复：使用当前目录
        self.team_stats_df = None
        self.market_data_df = None
        self.player_data_df = None
        self.home_court_advantage = 3.5  # 标准主场优势分
        
    def load_data(self):
        """加载所有必要数据文件"""
        try:
            # 加载球队效率数据
            team_stats_path = os.path.join(self.data_dir, "nba-advanced-stats.csv")
            self.team_stats_df = pd.read_csv(team_stats_path)
            print(f"✅ 加载球队效率数据: {len(self.team_stats_df)} 支球队")
            
            # 加载市场数据
            market_data_path = os.path.join(self.data_dir, "nba_enriched_data.csv")
            if os.path.exists(market_data_path):
                self.market_data_df = pd.read_csv(market_data_path)
                print(f"✅ 加载市场数据: {len(self.market_data_df)} 场比赛")
            else:
                # 使用nba-daily-odds.csv作为替代
                market_data_path = os.path.join(self.data_dir, "nba-daily-odds.csv")
                if os.path.exists(market_data_path):
                    self.market_data_df = pd.read_csv(market_data_path)
                    print(f"✅ 加载市场数据(替代): {len(self.market_data_df)} 场比赛")
                
            # 加载球员数据
            player_data_path = os.path.join(self.data_dir, "nba-roster.csv")
            if os.path.exists(player_data_path):
                self.player_data_df = pd.read_csv(player_data_path)
                print(f"✅ 加载球员数据: {len(self.player_data_df)} 名球员")
                
            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def calculate_team_strength(self, team: str) -> Dict:
        """计算球队综合实力评分"""
        if self.team_stats_df is None:
            return {}
            
        team_data = self.team_stats_df[self.team_stats_df['team'] == team]
        if len(team_data) == 0:
            return {}
            
        row = team_data.iloc[0]
        
        # 核心实力指标
        strength = {
            'team': team,
            'net_rating': float(row['nrtg']),
            'off_rating': float(row['ortg']),
            'def_rating': float(row['drtg']),
            'pace': float(row['pace']),
            'off_efg': float(row['o-eFG%']),
            'def_efg': float(row['d-eFG%']),
            'strength_score': float(row['nrtg']) * 0.7 + float(row['ortg']) * 0.2 - float(row['drtg']) * 0.1
        }
        
        return strength
    
    def predict_spread(self, home_team: str, away_team: str) -> Dict:
        """预测主队让分盘口"""
        home_strength = self.calculate_team_strength(home_team)
        away_strength = self.calculate_team_strength(away_team)
        
        if not home_strength or not away_strength:
            return {}
        
        # 基础实力差 (基于Net Rating)
        net_rating_diff = home_strength['net_rating'] - away_strength['net_rating']
        
        # 主场优势 (标准3.5分)
        home_advantage = 3.5
        
        # 节奏调整 (快节奏球队可能放大分差)
        pace_factor = (home_strength['pace'] - away_strength['pace']) * 0.05
        
        # 预测盘口
        predicted_spread = net_rating_diff + home_advantage + pace_factor
        
        # 置信度计算
        confidence = self.calculate_confidence(home_strength, away_strength)
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'predicted_spread': round(predicted_spread, 1),
            'net_rating_diff': round(net_rating_diff, 1),
            'home_advantage': home_advantage,
            'pace_factor': round(pace_factor, 2),
            'confidence': round(confidence, 2)
        }
    
    def calculate_confidence(self, home_strength: Dict, away_strength: Dict) -> float:
        """计算预测置信度 (0-1)"""
        # 基于数据完整性和一致性
        confidence = 0.7  # 基础置信度
        
        # 净评分差异越大，置信度越高
        rating_diff = abs(home_strength['net_rating'] - away_strength['net_rating'])
        if rating_diff > 10:
            confidence += 0.2
        elif rating_diff > 5:
            confidence += 0.1
            
        # 进攻防守效率一致性
        if home_strength['off_rating'] > 115 and home_strength['def_rating'] < 110:
            confidence += 0.05  # 攻防俱佳
        if away_strength['off_rating'] < 110 and away_strength['def_rating'] > 115:
            confidence += 0.05  # 攻弱守强
            
        return min(confidence, 0.95)
    
    def analyze_market_value(self, prediction: Dict, market_spread: float) -> Dict:
        """分析市场价值 - 改进版"""
        if not prediction:
            return {}
            
        predicted = prediction['predicted_spread']
        market = market_spread
        
        # 价值差异
        value_diff = predicted - market
        
        # 计算标准误 (基于信心水平)
        std_error = (1 - prediction['confidence']) * 2.5  # 信心越低，标准误越大
        
        # 计算标准化价值 (Z-score)
        if std_error > 0:
            z_score = abs(value_diff) / std_error
        else:
            z_score = abs(value_diff) / 2.0  # 默认标准误
        
        # 基于Z-score的价值评分 (0-3)
        if z_score < 0.5:
            value_score = 0  # 无显著价值
        elif z_score < 1.0:
            value_score = 1  # 低价值
        elif z_score < 1.5:
            value_score = 2  # 中价值
        else:
            value_score = 3  # 高价值
            
        # 考虑市场深度 (差异越大，价值可能越高但也越不稳定)
        if abs(value_diff) > 5.0:
            # 极端差异可能表明数据问题，降低价值评分
            value_score = min(value_score, 2)
            
        # 调整价值评分为百分制 (更平滑)
        value_score_100 = (value_score * 25) + (prediction['confidence'] * 25)
        
        # 推荐方向
        if value_diff > 0:
            recommendation = "主队让分"  # 预测盘口 > 市场盘口，主队可能被低估
            side = "home"
        else:
            recommendation = "客队受让"  # 预测盘口 < 市场盘口，客队可能被低估
            side = "away"
            
        return {
            'predicted_spread': predicted,
            'market_spread': market,
            'value_diff': round(value_diff, 1),
            'z_score': round(z_score, 2),
            'value_score': value_score,
            'value_score_100': round(value_score_100, 0),
            'recommendation': recommendation,
            'recommendation_side': side,
            'confidence': prediction['confidence']
        }
    
    def kelly_bet_size(self, edge: float, odds: float = 1.91) -> float:
        """计算凯利投注规模 (半凯利)"""
        # edge: 预期优势 (0-1)
        # odds: 赔率 (默认1.91，即-110)
        
        if edge <= 0:
            return 0.0
            
        b = odds - 1  # 赔率转换
        p = 0.5 + edge/2  # 基础胜率 + 优势调整
        q = 1 - p
        
        # 标准凯利公式
        full_kelly = (b * p - q) / b
        
        # 半凯利 (更保守)
        half_kelly = full_kelly / 2
        
        # 限制最大风险 (最大5%资金)
        return min(max(half_kelly, 0.01), 0.05)
    
    def generate_recommendation(self, home_team: str, away_team: str, market_spread: float) -> Dict:
        """生成完整推荐"""
        # 预测盘口
        prediction = self.predict_spread(home_team, away_team)
        if not prediction:
            return {}
            
        # 分析市场价值
        value_analysis = self.analyze_market_value(prediction, market_spread)
        if not value_analysis:
            return {}
            
        # 计算投注规模
        edge = abs(value_analysis['value_diff']) / 10  # 简化优势计算
        bet_size = self.kelly_bet_size(edge)
        
        # 构建推荐
        recommendation = {
            'matchup': f"{home_team} vs {away_team}",
            'date': pd.Timestamp.now().strftime("%Y-%m-%d"),
            'prediction': prediction,
            'market_analysis': value_analysis,
            'betting_advice': {
                'recommendation': value_analysis['recommendation'],
                'side': value_analysis['recommendation_side'],
                'value_score': int(value_analysis['value_score_100']),
                'confidence_level': '高' if value_analysis['confidence'] > 0.8 else '中' if value_analysis['confidence'] > 0.6 else '低',
                'bet_size_percent': round(bet_size * 100, 1),
                'reasoning': self.generate_reasoning(prediction, value_analysis)
            }
        }
        
        return recommendation
    
    def generate_reasoning(self, prediction: Dict, value_analysis: Dict) -> str:
        """生成推荐理由"""
        reasons = []
        
        # 实力对比
        net_diff = prediction['net_rating_diff']
        if net_diff > 5:
            reasons.append(f"实力差距明显 (Net Rating差: +{net_diff:.1f})")
        elif net_diff > 0:
            reasons.append(f"主队实力略占优势 (Net Rating差: +{net_diff:.1f})")
        else:
            reasons.append(f"客队实力占优 (Net Rating差: {net_diff:.1f})")
            
        # 主场优势
        reasons.append(f"主场优势: +{prediction['home_advantage']}分")
        
        # 价值分析
        value_diff = value_analysis['value_diff']
        if abs(value_diff) > 3:
            reasons.append(f"显著价值差异: {value_diff:+.1f}分")
        elif abs(value_diff) > 2:
            reasons.append(f"中等价值差异: {value_diff:+.1f}分")
            
        # 置信度
        if prediction['confidence'] > 0.8:
            reasons.append("高置信度预测")
        elif prediction['confidence'] > 0.6:
            reasons.append("中等置信度预测")
            
        return " | ".join(reasons)
    
    def test_prediction(self):
        """测试预测功能"""
        print("\n🔍 测试预测功能...")
        
        # 读取球队数据
        team_stats_path = os.path.join(self.data_dir, "nba-advanced-stats.csv")
        if os.path.exists(team_stats_path):
            df = pd.read_csv(team_stats_path)
            teams = df['team'].tolist()[:4]  # 取前4个球队测试
            
            if len(teams) >= 2:
                home_team = teams[0]
                away_team = teams[1]
                market_spread = -3.5  # 假设市场盘口
                
                print(f"测试对阵: {home_team} vs {away_team}")
                print(f"市场盘口: {market_spread}")
                
                rec = self.generate_recommendation(home_team, away_team, market_spread)
                if rec:
                    print(f"预测盘口: {rec['prediction']['predicted_spread']}")
                    print(f"价值评分: {rec['market_analysis']['value_score_100']}/100")
                    print(f"推荐: {rec['betting_advice']['recommendation']}")
                    return rec
        return None

def main():
    """主函数"""
    print("🏀 NBA盘口推荐系统启动 (当前版本)...")
    
    recommender = SpreadRecommender()
    
    # 加载数据
    if not recommender.load_data():
        print("❌ 数据加载失败，退出")
        return
        
    # 测试预测
    recommender.test_prediction()
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main()