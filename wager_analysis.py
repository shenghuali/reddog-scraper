#!/usr/bin/env python3
"""
投注量分析模块
分析投注量与盘口胜率的关系
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class WagerAnalyzer:
    """投注量分析器"""
    
    def __init__(self):
        self.wager_data = None
        self.wager_rules = {}
        
    def load_wager_data(self, df: pd.DataFrame) -> bool:
        """加载投注量数据"""
        try:
            # 检查是否有投注量字段
            home_wager_col = None
            away_wager_col = None
            
            for col in df.columns:
                if 'wager' in col.lower():
                    if 'home' in col.lower():
                        home_wager_col = col
                    elif 'away' in col.lower():
                        away_wager_col = col
            
            if not home_wager_col or not away_wager_col:
                print("⚠️ 数据中没有投注量字段")
                return False
            
            # 筛选有完整数据的比赛
            wager_df = df.copy()
            wager_df['home_wager_pct'] = pd.to_numeric(wager_df[home_wager_col], errors='coerce')
            wager_df['away_wager_pct'] = pd.to_numeric(wager_df[away_wager_col], errors='coerce')
            wager_df['home_score'] = pd.to_numeric(wager_df['home_score'], errors='coerce')
            wager_df['away_score'] = pd.to_numeric(wager_df['away_score'], errors='coerce')
            wager_df['close_spread'] = pd.to_numeric(wager_df['close_spread'], errors='coerce')
            
            # 确保有比分和盘口
            wager_df = wager_df[
                wager_df['home_wager_pct'].notna() &
                wager_df['away_wager_pct'].notna() &
                wager_df['home_score'].notna() &
                wager_df['away_score'].notna() &
                wager_df['close_spread'].notna()
            ]
            
            if len(wager_df) < 50:
                print(f"⚠️ 投注量数据不足: {len(wager_df)} 场比赛")
                return False
            
            self.wager_data = wager_df
            print(f"✅ 加载 {len(wager_df)} 场投注量数据")
            return True
            
        except Exception as e:
            print(f"❌ 加载投注量数据失败: {e}")
            return False
    
    def analyze_wager_patterns(self) -> Dict:
        """分析投注量规律"""
        if self.wager_data is None or len(self.wager_data) < 50:
            return {}
        
        df = self.wager_data.copy()
        
        # 计算实际盘口结果
        df['actual_margin'] = df['home_score'] - df['away_score']
        df['ats_result'] = df['actual_margin'] - df['close_spread']
        
        # 投注量偏差（正数表示主队更热）
        df['wager_bias'] = df['home_wager_pct'] - 50.0
        
        # 分位数分析
        print("\n📊 投注量偏差分布与胜率:")
        print("-" * 50)
        
        results = {}
        
        # 按投注量偏差分组
        bias_bins = {
            'strong_away_bias': (-50, -15),    # 客队过热 (>65%)
            'moderate_away_bias': (-15, -5),   # 客队偏热 (55-65%)
            'balanced': (-5, 5),               # 平衡 (45-55%)
            'moderate_home_bias': (5, 15),     # 主队偏热 (55-65%)
            'strong_home_bias': (15, 50)       # 主队过热 (>65%)
        }
        
        for bias_type, (min_bias, max_bias) in bias_bins.items():
            mask = (df['wager_bias'] >= min_bias) & (df['wager_bias'] < max_bias)
            group = df[mask]
            
            if len(group) > 10:
                home_cover = (group['ats_result'] > 0).sum()
                away_cover = (group['ats_result'] < 0).sum()
                total = len(group)
                
                home_cover_rate = home_cover / total
                away_cover_rate = away_cover / total
                
                # 计算反买机会（如果大众错误）
                if home_cover_rate < 0.45 and max_bias > 10:  # 主队过热但赢盘率低
                    action = '反买主队'  # 应该买客队
                    edge = 0.55 - home_cover_rate  # 预期优势
                elif away_cover_rate < 0.45 and min_bias < -10:  # 客队过热但赢盘率低
                    action = '反买客队'  # 应该买主队
                    edge = 0.55 - away_cover_rate
                else:
                    action = '跟随大众' if abs(home_cover_rate - 0.5) < 0.1 else '无明确信号'
                    edge = 0.0
                
                # 显示结果
                bias_name = {
                    'strong_away_bias': '客队过热(>65%)',
                    'moderate_away_bias': '客队偏热(55-65%)',
                    'balanced': '投注平衡(45-55%)',
                    'moderate_home_bias': '主队偏热(55-65%)',
                    'strong_home_bias': '主队过热(>65%)'
                }[bias_type]
                
                print(f"  {bias_name}: {total}场比赛")
                print(f"    主队赢盘率: {home_cover_rate:.1%} ({home_cover}/{total})")
                print(f"    客队赢盘率: {away_cover_rate:.1%} ({away_cover}/{total})")
                print(f"    建议: {action}")
                if edge > 0:
                    print(f"    预期优势: {edge:.2%}")
                print()
                
                # 存储规则
                if edge > 0.05:  # 只有明显优势才记录
                    self.wager_rules[bias_type] = {
                        'min_bias': min_bias,
                        'max_bias': max_bias,
                        'action': action,
                        'edge': edge,
                        'home_cover_rate': home_cover_rate,
                        'away_cover_rate': away_cover_rate,
                        'sample_size': total
                    }
        
        # 分析极端情况
        print("\n📈 极端投注量分析:")
        print("-" * 50)
        
        # 找到投注量最不平衡的比赛
        df['total_wager_pct'] = df['home_wager_pct'] + df['away_wager_pct']
        df['wager_imbalance'] = abs(df['home_wager_pct'] - df['away_wager_pct'])
        
        # 投注量最不平衡的20%比赛
        threshold = df['wager_imbalance'].quantile(0.8)
        extreme_games = df[df['wager_imbalance'] >= threshold]
        
        if len(extreme_games) > 20:
            # 分析大众错误的情况
            home_favorites = extreme_games[extreme_games['wager_bias'] > 0]
            away_favorites = extreme_games[extreme_games['wager_bias'] < 0]
            
            if len(home_favorites) > 10:
                home_fav_cover_rate = (home_favorites['ats_result'] > 0).sum() / len(home_favorites)
                print(f"  主队热门({len(home_favorites)}场): 赢盘率 {home_fav_cover_rate:.1%}")
                if home_fav_cover_rate < 0.48:
                    print(f"  ⚠️ 主队热门可能是陷阱!")
            
            if len(away_favorites) > 10:
                away_fav_cover_rate = (away_favorites['ats_result'] < 0).sum() / len(away_favorites)
                print(f"  客队热门({len(away_favorites)}场): 赢盘率 {away_fav_cover_rate:.1%}")
                if away_fav_cover_rate < 0.48:
                    print(f"  ⚠️ 客队热门可能是陷阱!")
        
        return self.wager_rules
    
    def get_wager_advice(self, home_wager_pct: float, away_wager_pct: float) -> Tuple[str, float]:
        """根据投注量给出建议"""
        if not self.wager_rules:
            return "无投注量数据", 0.0
        
        wager_bias = home_wager_pct - 50.0  # 主队投注偏差
        
        for bias_type, rule in self.wager_rules.items():
            if rule['min_bias'] <= wager_bias < rule['max_bias']:
                return rule['action'], rule['edge']
        
        return "无明确信号", 0.0
    
    def calculate_wager_adjustment(self, home_wager_pct: float, away_wager_pct: float, 
                                 predicted_margin: float) -> float:
        """根据投注量调整预测净胜分"""
        if not self.wager_rules:
            return predicted_margin
        
        wager_bias = home_wager_pct - 50.0
        
        # 如果投注量极不平衡，可能表示市场情绪过热
        wager_imbalance = abs(wager_bias)
        
        # 调整逻辑：
        # 1. 投注量平衡（45-55%）：不调整
        # 2. 轻微不平衡（55-65%）：微调
        # 3. 严重不平衡（>65%）：较大调整（反买逻辑）
        
        adjustment = 0.0
        
        if wager_imbalance > 15:  # 严重不平衡 (>65%投注一边)
            # 反买逻辑：如果大众过热，实际表现可能更差
            if wager_bias > 0:  # 主队过热
                adjustment = -1.5  # 降低主队预期
            else:  # 客队过热
                adjustment = 1.5   # 提高主队预期（降低客队预期）
        elif wager_imbalance > 5:  # 轻微不平衡 (55-65%)
            if wager_bias > 0:  # 主队稍热
                adjustment = -0.5
            else:  # 客队稍热
                adjustment = 0.5
        
        return predicted_margin + adjustment


def main():
    """测试投注量分析"""
    import os
    
    data_path = os.path.join(os.path.dirname(__file__), 'nba_enriched_data.csv')
    if not os.path.exists(data_path):
        print(f"❌ 数据文件不存在: {data_path}")
        return
    
    df = pd.read_csv(data_path)
    analyzer = WagerAnalyzer()
    
    if analyzer.load_wager_data(df):
        rules = analyzer.analyze_wager_patterns()
        
        print("\n🎯 投注量规则总结:")
        print("=" * 50)
        for bias_type, rule in rules.items():
            print(f"  规则: {bias_type}")
            print(f"    偏差范围: {rule['min_bias']:.1f}% 到 {rule['max_bias']:.1f}%")
            print(f"    建议操作: {rule['action']}")
            print(f"    预期优势: {rule['edge']:.2%}")
            print(f"    样本量: {rule['sample_size']} 场比赛")
            print()


if __name__ == "__main__":
    main()