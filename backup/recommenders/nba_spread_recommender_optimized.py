#!/usr/bin/env python3
"""
优化版NBA盘口推荐系统
结合当前版本和改进版本的优点：
- 动态主场优势计算（改进版）
- 多因素加权预测（改进版）
- 凯利投注规模（当前版）
- 修正的盘口术语显示
- 修复路径和列名问题
"""

import pandas as pd
import numpy as np
import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class OptimizedSpreadRecommender:
    def __init__(self, data_dir: str = "."):
        """
        初始化推荐器
        
        Args:
            data_dir: 数据目录路径，默认为当前目录
        """
        self.data_dir = data_dir
        self.team_stats_df = None
        self.market_data_df = None
        self.player_data_df = None
        self.home_advantage_base = 3.5  # 基础主场优势
        
    def load_data(self) -> bool:
        """加载所有必要数据文件（修复路径问题）"""
        try:
            # 加载球队效率数据
            team_stats_path = os.path.join(self.data_dir, "nba-advanced-stats.csv")
            if os.path.exists(team_stats_path):
                self.team_stats_df = pd.read_csv(team_stats_path)
                print(f"✅ 加载球队效率数据: {len(self.team_stats_df)} 支球队")
            else:
                print(f"⚠️  球队统计文件不存在: {team_stats_path}")
                return False
                
            # 加载市场数据（尝试多个可能的文件）
            market_files = ["nba_enriched_data.csv", "nba-daily-odds.csv", "nba-latest-odds.csv"]
            market_data_loaded = False
            
            for market_file in market_files:
                market_data_path = os.path.join(self.data_dir, market_file)
                if os.path.exists(market_data_path):
                    self.market_data_df = pd.read_csv(market_data_path)
                    print(f"✅ 加载市场数据: {market_file} ({len(self.market_data_df)} 场比赛)")
                    market_data_loaded = True
                    break
                    
            if not market_data_loaded:
                print("⚠️  未找到市场数据文件，将使用测试数据")
                
            # 加载球员数据
            player_data_path = os.path.join(self.data_dir, "nba-roster.csv")
            if os.path.exists(player_data_path):
                self.player_data_df = pd.read_csv(player_data_path)
                print(f"✅ 加载球员数据: {len(self.player_data_df)} 名球员")
            else:
                print(f"⚠️  球员数据文件不存在: {player_data_path}")
                
            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def calculate_dynamic_home_advantage(self, home_team: str, away_team: str) -> float:
        """计算动态主场优势（改进版本算法）"""
        if self.team_stats_df is None:
            return self.home_advantage_base
            
        home_stats = self.team_stats_df[self.team_stats_df['team'] == home_team]
        away_stats = self.team_stats_df[self.team_stats_df['team'] == away_team]
        
        if home_stats.empty or away_stats.empty:
            return self.home_advantage_base
            
        # 基础主场优势
        advantage = self.home_advantage_base
        
        try:
            # 1. 客场球队防守质量调整
            away_def_rating = away_stats['drtg'].values[0] if 'drtg' in away_stats.columns else 110
            if away_def_rating > 115:  # 防守差
                advantage += 1.0
            elif away_def_rating < 108:  # 防守好
                advantage -= 0.5
                
            # 2. 主队进攻效率调整
            home_off_rating = home_stats['ortg'].values[0] if 'ortg' in home_stats.columns else 110
            if home_off_rating > 115:  # 进攻强
                advantage += 0.5
            elif home_off_rating < 105:  # 进攻弱
                advantage -= 0.5
                
            # 3. 比赛节奏调整
            home_pace = home_stats['pace'].values[0] if 'pace' in home_stats.columns else 100
            away_pace = away_stats['pace'].values[0] if 'pace' in away_stats.columns else 100
            pace_diff = home_pace - away_pace
            advantage += pace_diff * 0.05  # 每10节奏差影响0.5分
            
        except Exception as e:
            print(f"⚠️  动态主场优势计算异常，使用基础值: {e}")
            
        # 确保主场优势在合理范围内
        return round(max(min(advantage, 5.0), 2.0), 1)  # 限制在2.0-5.0分之间
    
    def predict_spread(self, home_team: str, away_team: str) -> Optional[Dict]:
        """预测盘口 - 结合版算法"""
        if self.team_stats_df is None:
            print("❌ 统计数据未加载")
            return None
            
        home_stats = self.team_stats_df[self.team_stats_df['team'] == home_team]
        away_stats = self.team_stats_df[self.team_stats_df['team'] == away_team]
        
        if home_stats.empty or away_stats.empty:
            print(f"⚠️  找不到球队数据: {home_team} 或 {away_team}")
            return None
            
        try:
            # 提取关键指标（修复列名问题）
            home_net = float(home_stats['nrtg'].values[0]) if 'nrtg' in home_stats.columns else 0
            away_net = float(away_stats['nrtg'].values[0]) if 'nrtg' in away_stats.columns else 0
            net_diff = home_net - away_net
            
            # 动态主场优势
            home_advantage = self.calculate_dynamic_home_advantage(home_team, away_team)
            
            # 进攻对防守优势
            home_off = float(home_stats['ortg'].values[0]) if 'ortg' in home_stats.columns else 110
            away_def = float(away_stats['drtg'].values[0]) if 'drtg' in away_stats.columns else 110
            off_def_advantage = home_off - away_def
            
            # 防守对进攻优势
            home_def = float(home_stats['drtg'].values[0]) if 'drtg' in home_stats.columns else 110
            away_off = float(away_stats['ortg'].values[0]) if 'ortg' in away_stats.columns else 110
            def_off_advantage = away_off - home_def  # 负值表示防守优势
            
            # 节奏因子（当前版本）
            home_pace = float(home_stats['pace'].values[0]) if 'pace' in home_stats.columns else 100
            away_pace = float(away_stats['pace'].values[0]) if 'pace' in away_stats.columns else 100
            pace_factor = (home_pace - away_pace) * 0.05
            
            # 优化加权预测
            # 权重调整：净效率40%，主场优势30%，攻防匹配20%，节奏因子10%
            predicted_spread = (
                net_diff * 0.4 +            # 球队实力差距
                home_advantage * 0.3 +      # 主场优势
                off_def_advantage * 0.2 +   # 进攻对防守优势
                pace_factor * 0.1           # 节奏调整
            )
            
            # 计算置信度（结合两个版本）
            confidence = self.calculate_combined_confidence(
                home_stats.iloc[0], away_stats.iloc[0],
                net_diff, home_advantage
            )
            
            # 修正盘口显示：负值表示主队让分
            display_spread = -abs(predicted_spread) if predicted_spread > 0 else predicted_spread
            
            return {
                'home_team': home_team,
                'away_team': away_team,
                'net_rating_diff': round(net_diff, 1),
                'home_advantage': home_advantage,
                'off_def_advantage': round(off_def_advantage, 1),
                'def_off_advantage': round(def_off_advantage, 1),
                'pace_factor': round(pace_factor, 2),
                'predicted_spread_raw': round(predicted_spread, 1),  # 原始值
                'predicted_spread_display': round(display_spread, 1),  # 显示值（负号表示让分）
                'confidence': round(confidence, 2)
            }
            
        except Exception as e:
            print(f"❌ 预测计算失败: {e}")
            return None
    
    def calculate_combined_confidence(self, home_stats, away_stats, net_diff, home_advantage) -> float:
        """计算综合置信度（结合两个版本）"""
        confidence = 0.6  # 基础置信度
        
        try:
            # 1. 数据质量评估（改进版本）
            home_games = home_stats.get('games_played', 0) if 'games_played' in home_stats else 0
            away_games = away_stats.get('games_played', 0) if 'games_played' in away_stats else 0
            min_games = min(home_games, away_games)
            
            data_quality = min(min_games / 20.0, 1.0)  # 20场比赛达到完全可信
            confidence += data_quality * 0.2
            
            # 2. 净评分差异（当前版本）
            rating_diff = abs(net_diff)
            if rating_diff > 10:
                confidence += 0.15
            elif rating_diff > 5:
                confidence += 0.1
            elif rating_diff > 2:
                confidence += 0.05
                
            # 3. 攻防一致性（当前版本）
            home_off = home_stats.get('ortg', 110)
            home_def = home_stats.get('drtg', 110)
            away_off = away_stats.get('ortg', 110)
            away_def = away_stats.get('drtg', 110)
            
            if home_off > 115 and home_def < 110:
                confidence += 0.05  # 主队攻防俱佳
            if away_off < 110 and away_def > 115:
                confidence += 0.05  # 客队攻弱守强
                
            # 4. 主场优势合理性
            if 2.5 <= home_advantage <= 4.5:
                confidence += 0.05  # 合理的主场优势范围
                
        except Exception:
            # 如果计算失败，使用基础置信度
            pass
            
        return min(confidence, 0.95)  # 最大95%
    
    def analyze_market_value(self, prediction: Dict, market_spread: float) -> Dict:
        """分析市场价值 - 优化版"""
        if not prediction:
            return {}
            
        predicted_raw = prediction['predicted_spread_raw']
        market = market_spread
        
        # 价值差异（使用原始预测值）
        value_diff = predicted_raw - market
        
        # 计算标准误（基于信心水平）
        confidence = prediction['confidence']
        std_error = max((1.0 - confidence) * 2.5, 0.5)  # 最小0.5
        
        # 计算标准化价值（Z-score）
        z_score = abs(value_diff) / std_error if std_error > 0 else abs(value_diff) / 1.0
        
        # 价值评分（0-100）
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
            
        # 调整价值评分（考虑极端值风险）
        if abs(value_diff) > 8.0:
            value_score = max(0, value_score - 20)  # 极端差异降低可信度
        elif abs(value_diff) < 1.0:
            value_score = max(0, value_score - 10)  # 微小差异降低价值
            
        # 推荐方向（使用正确的盘口术语）
        if value_diff > 0:
            # 预测 > 市场，主队被低估
            if predicted_raw > 0:
                recommendation = "主队让分"
                side = "home"
                bet_spread = -abs(predicted_raw)  # 负号表示让分
            else:
                recommendation = "客队受让"
                side = "away"
                bet_spread = predicted_raw
        else:
            # 预测 < 市场，客队被低估
            if predicted_raw > 0:
                recommendation = "客队受让"
                side = "away"
                bet_spread = -predicted_raw
            else:
                recommendation = "主队让分"
                side = "home"
                bet_spread = predicted_raw
                
        return {
            'predicted_spread_raw': round(predicted_raw, 1),
            'predicted_spread_display': prediction['predicted_spread_display'],
            'market_spread': market,
            'value_diff': round(value_diff, 1),
            'z_score': round(z_score, 2),
            'value_score': value_score,
            'recommendation': recommendation,
            'side': side,
            'bet_spread': round(bet_spread, 1),
            'confidence': confidence
        }
    
    def kelly_bet_size(self, edge: float, odds: float = 1.91) -> float:
        """计算凯利投注规模（半凯利）- 当前版本算法"""
        if edge <= 0:
            return 0.0
            
        b = odds - 1  # 赔率转换
        p = 0.5 + edge/2  # 基础胜率 + 优势调整
        q = 1 - p
        
        # 标准凯利公式
        full_kelly = (b * p - q) / b
        
        # 半凯利（更保守）
        half_kelly = full_kelly / 2
        
        # 限制最大风险（最大5%资金）
        return min(max(half_kelly, 0.01), 0.05)
    
    def calculate_edge_from_value(self, value_score: int, value_diff: float) -> float:
        """从价值评分计算预期优势"""
        # 基础优势
        base_edge = value_score / 100.0 * 0.3
        
        # 价值差异调整
        diff_factor = min(abs(value_diff) / 10.0, 1.0) * 0.2
        
        return base_edge + diff_factor
    
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
        edge = self.calculate_edge_from_value(
            value_analysis['value_score'],
            value_analysis['value_diff']
        )
        bet_size = self.kelly_bet_size(edge)
        
        # 生成理由
        reasoning = self.generate_reasoning(prediction, value_analysis)
        
        # 构建推荐
        recommendation = {
            'matchup': f"{home_team} vs {away_team}",
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'prediction': prediction,
            'market_analysis': value_analysis,
            'betting_advice': {
                'action': value_analysis['recommendation'],
                'side': value_analysis['side'],
                'bet_spread': value_analysis['bet_spread'],
                'value_score': value_analysis['value_score'],
                'confidence_level': '高' if value_analysis['confidence'] > 0.8 else '中' if value_analysis['confidence'] > 0.6 else '低',
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
            reasons.append(f"显著实力差距 (净效率差: {net_diff:.1f})")
        elif abs(net_diff) > 2:
            reasons.append(f"明显实力差距 (净效率差: {net_diff:.1f})")
        else:
            reasons.append(f"实力相近 (净效率差: {net_diff:.1f})")
            
        # 主场优势
        home_advantage = prediction['home_advantage']
        if home_advantage > 4.0:
            reasons.append(f"强主场优势 (+{home_advantage}分)")
        elif home_advantage < 3.0:
            reasons.append(f"弱主场优势 (+{home_advantage}分)")
        else:
            reasons.append(f"标准主场优势 (+{home_advantage}分)")
            
        # 价值评估
        value_diff = value_analysis['value_diff']
        z_score = value_analysis['z_score']
        
        if abs(value_diff) > 3.0 and z_score > 1.5:
            reasons.append(f"高统计价值 (差异: {value_diff:.1f}分, Z-score: {z_score:.2f})")
        elif abs(value_diff) > 2.0:
            reasons.append(f"中等统计价值 (差异: {value_diff:.1f}分, Z-score: {z_score:.2f})")
        else:
            reasons.append(f"有限统计价值 (差异: {value_diff:.1f}分, Z-score: {z_score:.2f})")
            
        # 置信度
        confidence = prediction['confidence']
        if confidence > 0.8:
            reasons.append("高置信度预测")
        elif confidence > 0.6:
            reasons.append("中等置信度预测")
        else:
            reasons.append("低置信度预测")
            
        return " | ".join(reasons)
    
    def find_todays_best_spread_bets(self, matchups: List[Tuple] = None) -> List[Dict]:
        """查找今日最佳盘口投注"""
        if matchups:
            # 如果提供了对阵，使用提供的对阵
            recommendations = []
            for home, away, market_spread in matchups:
                rec = self.generate_recommendation(home, away, market_spread)
                if rec and rec['market_analysis']['value_score'] >= 50:  # 至少中等价值
                    recommendations.append(rec)
        else:
            # 如果没有提供对阵，尝试从市场数据中筛选
            recommendations = []
            
            if self.market_data_df is not None and len(self.market_data_df) > 0:
                # 尝试筛选今日比赛
                # 这里可以根据实际数据结构调整
                print(f"📅  找到 {len(self.market_data_df)} 场市场数据")
                
                # 简单测试：取前几场比赛
                test_games = self.market_data_df.head(3)
                for idx, game in test_games.iterrows():
                    if 'home_team' in game and 'away_team' in game:
                        home_team = game['home_team']
                        away_team = game['away_team']
                        
                        # 尝试获取盘口数据
                        market_spread = -3.5  # 默认测试值
                        if 'close_spread' in game and not pd.isna(game['close_spread']):
                            market_spread = game['close_spread']
                        elif 'open_spread' in game and not pd.isna(game['open_spread']):
                            market_spread = game['open_spread']
                            
                        rec = self.generate_recommendation(home_team, away_team, market_spread)
                        if rec and rec['market_analysis']['value_score'] >= 50:
                            recommendations.append(rec)
            else:
                print("⚠️  市场数据未加载或为空，无法获取今日比赛")
                
        # 按价值评分排序
        recommendations.sort(key=lambda x: x['market_analysis']['value_score'], reverse=True)
        
        return recommendations
    
    def save_recommendation(self, recommendation: Dict, filename: str = None):
        """保存推荐到JSON文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"spread_recommendation_optimized_{timestamp}.json"
            
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(recommendation, f, indent=2, ensure_ascii=False)
            
        print(f"✅ 推荐已保存: {filepath}")
        return filepath
    
    def test_single_prediction(self):
        """测试单个预测"""
        print("\n🔍 测试单个预测...")
        
        if self.team_stats_df is None:
            print("❌ 统计数据未加载")
            return None
            
        # 取前两个球队测试
        teams = self.team_stats_df['team'].tolist()[:2]
        if len(teams) < 2:
            print("❌ 球队数据不足")
            return None
            
        home_team = teams[0]
        away_team = teams[1]
        market_spread = -3.5  # 测试市场盘口
        
        print(f"测试对阵: {home_team} vs {away_team}")
        print(f"市场盘口: {market_spread}")
        
        recommendation = self.generate_recommendation(home_team, away_team, market_spread)
        
        if recommendation:
            print(f"\n📊 预测结果:")
            print(f"  预测盘口: {recommendation['prediction']['predicted_spread_display']}")
            print(f"  市场盘口: {recommendation['market_analysis']['market_spread']}")
            print(f"  价值差异: {recommendation['market_analysis']['value_diff']:.1f}分")
            print(f"  价值评分: {recommendation['market_analysis']['value_score']}/100")
            print(f"  推荐: {recommendation['betting_advice']['action']}")
            print(f"  投注盘口: {recommendation['betting_advice']['bet_spread']}")
            print(f"  投注规模: {recommendation['betting_advice']['bet_size_percent']}%")
            print(f"  置信度: {recommendation['betting_advice']['confidence_level']}")
            print(f"  理由: {recommendation['betting_advice']['reasoning']}")
            
            # 保存测试结果
            self.save_recommendation(recommendation, "test_recommendation.json")
            
        return recommendation

def main():
    """主函数"""
    print("🏀 NBA盘口推荐系统 (优化版) 启动...")
    print("=" * 50)
    
    # 初始化推荐器（使用当前目录）
    recommender = OptimizedSpreadRecommender(data_dir=".")
    
    # 加载数据
    if not recommender.load_data():
        print("❌ 数据加载失败，退出")
        return
        
    print("\n" + "=" * 50)
    
    # 测试单个预测
    recommendation = recommender.test_single_prediction()
    
    if recommendation:
        print("\n✅ 测试完成")
        print(f"📁 测试结果已保存到: test_recommendation.json")
    else:
        print("\n❌ 测试失败")
        
    print("=" * 50)

if __name__ == "__main__":
    main()
