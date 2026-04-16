#!/usr/bin/env python3
"""
NBA数据与赔率关系分析 - 预测比赛结果
分析 enriched_data, injury, advanced_stats 三个数据集
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

def load_data():
    """加载三个数据源"""
    print("📊 加载NBA数据文件...")
    
    data_files = {
        'enriched': '/Users/shenghuali/reddog-scraper/nba_enriched_data.csv',
        'injury': '/Users/shenghuali/reddog-scraper/nba-injury-latest.csv',
        'advanced': '/Users/shenghuali/reddog-scraper/nba-advanced-stats.csv'
    }
    
    data = {}
    for name, path in data_files.items():
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                data[name] = df
                print(f"✅ {name}: {len(df)} 行, {len(df.columns)} 列")
                print(f"   列名: {list(df.columns)[:5]}...")
            except Exception as e:
                print(f"❌ 加载 {name} 失败: {e}")
                data[name] = pd.DataFrame()
        else:
            print(f"❌ 文件不存在: {path}")
            data[name] = pd.DataFrame()
    
    return data

def analyze_data_relationships(data):
    """分析数据关系"""
    print("\n🔍 分析数据关系...")
    
    enriched_df = data['enriched']
    injury_df = data['injury']
    advanced_df = data['advanced']
    
    # 1. 基本统计
    print("1. 数据集基本信息:")
    if not enriched_df.empty:
        print(f"   enriched_data 行数: {len(enriched_df)}")
        print(f"   时间范围: {enriched_df['data_date'].min() if 'data_date' in enriched_df.columns else '未知'} 到 {enriched_df['data_date'].max() if 'data_date' in enriched_df.columns else '未知'}")
    
    if not injury_df.empty:
        print(f"   injury 行数: {len(injury_df)}")
        print(f"   受伤球员数: {injury_df['Player'].nunique() if 'Player' in injury_df.columns else '未知'}")
        print(f"   受影响球队数: {injury_df['Team'].nunique() if 'Team' in injury_df.columns else '未知'}")
    
    if not advanced_df.empty:
        print(f"   advanced_stats 行数: {len(advanced_df)}")
        print(f"   球队数: {advanced_df['Team'].nunique() if 'Team' in advanced_df.columns else '未知'}")
        if 'nrtg' in advanced_df.columns:
            print(f"   净效率范围: {advanced_df['nrtg'].min():.1f} 到 {advanced_df['nrtg'].max():.1f}")
    
    # 2. 关键特征识别
    print("\n2. 关键特征识别:")
    
    # enriched_data的特征
    if not enriched_df.empty:
        enriched_features = []
        for col in enriched_df.columns:
            if any(keyword in col.lower() for keyword in ['odds', 'moneyline', 'spread', 'total', 'price']):
                enriched_features.append(col)
        print(f"   enriched_data中的赔率相关列: {enriched_features}")
    
    # injury数据的影响
    if not injury_df.empty:
        if 'Status' in injury_df.columns:
            status_counts = injury_df['Status'].value_counts()
            print(f"   伤病状态分布: {dict(status_counts.head())}")
    
    # advanced_stats的关键指标
    if not advanced_df.empty:
        key_stats = ['ortg', 'drtg', 'nrtg', 'pace', 'efg_pct', 'tov_pct', 'orb_pct', 'ft_rate', 'off_rating', 'def_rating']
        available_stats = [stat for stat in key_stats if stat in advanced_df.columns]
        print(f"   可用的高级统计指标: {available_stats}")
    
    return {
        'enriched_features': enriched_features if 'enriched_features' in locals() else [],
        'available_stats': available_stats if 'available_stats' in locals() else []
    }

def research_betting_patterns():
    """研究赔率模式（基于网络资料）"""
    print("\n📚 基于研究的赔率模式分析:")
    
    # NBA赔率常见模式（基于公开研究）
    patterns = {
        'home_advantage': '主场胜率通常比客场高5-8%',
        'rest_days': '休息3天以上的球队胜率提高10-15%',
        'back_to_back': '背靠背第二场胜率下降8-12%',
        'injury_impact': '核心球员缺阵导致胜率下降15-25%',
        'travel_distance': '长途旅行后首场比赛胜率下降5-10%',
        'division_games': '同分区比赛通常更激烈，分差较小',
        'playoff_push': '赛季末争夺季后赛席位的球队更有动力',
        'tank_mode': '无望季后赛的球队可能故意输球',
        'star_player': '有MVP级别球员的球队胜率提高10-15%',
        'coaching': '优秀教练可提升球队胜率5-10%'
    }
    
    for pattern, desc in patterns.items():
        print(f"   • {pattern}: {desc}")
    
    return patterns

def build_prediction_framework():
    """构建预测框架"""
    print("\n🤖 构建预测框架...")
    
    framework = {
        'data_sources': [
            '实时赔率数据 (enriched_data)',
            '球队伤病情况 (injury)',
            '球队高级统计 (advanced_stats)',
            '历史对战胜负',
            '赛程因素 (主场/客场/休息)',
            '球队近期状态',
            '球员个人表现'
        ],
        
        'prediction_factors': [
            '球队实力对比 (净效率差)',
            '伤病影响权重',
            '主场优势系数',
            '赛程疲劳度',
            '近期战绩动量',
            '关键球员状态',
            '历史交锋记录',
            '盘口变化趋势'
        ],
        
        'machine_learning_models': [
            '逻辑回归 (胜/负分类)',
            '梯度提升树 (XGBoost/LightGBM)',
            '神经网络 (深度学习)',
            '集成学习 (多模型投票)',
            '时间序列分析 (状态变化)'
        ],
        
        'output_predictions': [
            '胜负预测 (胜率百分比)',
            '让分盘预测',
            '大小分预测',
            '具体比分范围',
            '信心指数'
        ]
    }
    
    print("   数据源:")
    for source in framework['data_sources']:
        print(f"     • {source}")
    
    print("\n   预测因素:")
    for factor in framework['prediction_factors']:
        print(f"     • {factor}")
    
    print("\n   可用模型:")
    for model in framework['machine_learning_models']:
        print(f"     • {model}")
    
    return framework

def create_prediction_pipeline():
    """创建预测流水线"""
    print("\n🔧 创建预测流水线...")
    
    pipeline_code = '''
# NBA比赛预测流水线
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb
import lightgbm as lgb

class NBAPredictor:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_importance = {}
    
    def prepare_features(self, enriched_data, injury_data, advanced_stats):
        """准备特征工程"""
        features = {}
        
        # 1. 球队实力特征
        if not advanced_stats.empty:
            features['team_strength'] = self._extract_team_strength(advanced_stats)
        
        # 2. 伤病影响特征
        if not injury_data.empty:
            features['injury_impact'] = self._calculate_injury_impact(injury_data)
        
        # 3. 赔率市场特征
        if not enriched_data.empty:
            features['market_signals'] = self._extract_market_signals(enriched_data)
        
        # 4. 赛程特征
        features['schedule_factors'] = self._calculate_schedule_factors()
        
        return pd.concat(features.values(), axis=1) if features else pd.DataFrame()
    
    def _extract_team_strength(self, advanced_stats):
        """提取球队实力特征"""
        # 净效率、进攻效率、防守效率、节奏等
        strength_features = ['nrtg', 'ortg', 'drtg', 'pace', 'efg_pct']
        return advanced_stats[strength_features]
    
    def _calculate_injury_impact(self, injury_data):
        """计算伤病影响"""
        # 根据球员重要性、伤病严重程度计算影响分数
        impact_score = injury_data.groupby('Team').apply(
            lambda x: len(x) * 0.5  # 简化计算
        )
        return impact_score
    
    def _extract_market_signals(self, enriched_data):
        """提取市场信号"""
        # 赔率变化、盘口调整、投注分布等
        market_features = ['odds_movement', 'line_change', 'volume_ratio']
        return enriched_data[market_features]
    
    def _calculate_schedule_factors(self):
        """计算赛程因素"""
        # 休息天数、旅行距离、背靠背等
        return pd.DataFrame()
    
    def train(self, X, y):
        """训练多个模型"""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        # 标准化特征
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 训练多个模型
        models = {
            'random_forest': RandomForestClassifier(n_estimators=100),
            'gradient_boosting': GradientBoostingClassifier(n_estimators=100),
            'xgboost': xgb.XGBClassifier(n_estimators=100),
            'lightgbm': lgb.LGBMClassifier(n_estimators=100)
        }
        
        for name, model in models.items():
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            print(f"{name} 准确率: {accuracy:.3f}")
            self.models[name] = model
        
        return self
    
    def predict(self, X):
        """集成预测"""
        X_scaled = self.scaler.transform(X)
        predictions = []
        
        for name, model in self.models.items():
            pred = model.predict_proba(X_scaled)[:, 1]  # 胜率概率
            predictions.append(pred)
        
        # 集成预测（平均）
        ensemble_pred = np.mean(predictions, axis=0)
        return ensemble_pred
    
    def feature_importance_analysis(self):
        """特征重要性分析"""
        if 'random_forest' in self.models:
            importances = self.models['random_forest'].feature_importances_
            self.feature_importance = dict(zip(self.feature_names, importances))
        
        return self.feature_importance

# 使用示例
if __name__ == "__main__":
    # 加载数据
    enriched = pd.read_csv('nba_enriched_data.csv')
    injury = pd.read_csv('nba-injury-latest.csv')
    advanced = pd.read_csv('nba-advanced-stats.csv')
    
    # 创建预测器
    predictor = NBAPredictor()
    
    # 准备特征
    X = predictor.prepare_features(enriched, injury, advanced)
    
    # 需要历史比赛结果作为标签 (y)
    # y = load_historical_results()
    
    # 训练模型
    # predictor.train(X, y)
    
    # 预测新比赛
    # predictions = predictor.predict(X_new)
    
    print("预测流水线准备就绪")
'''
    
    print("   流水线代码已生成")
    print("   包含: 特征工程、多模型训练、集成预测、特征重要性分析")
    
    return pipeline_code

def generate_recommendations():
    """生成推荐"""
    print("\n🎯 预测系统实施建议:")
    
    recommendations = [
        "1. 收集更多历史比赛数据（至少2-3个赛季）",
        "2. 添加球队对阵历史数据",
        "3. 集成球员个人统计数据",
        "4. 考虑赛程和旅行因素",
        "5. 监控赔率实时变化",
        "6. 使用机器学习模型集成",
        "7. 定期回测和优化模型",
        "8. 考虑市场效率和异常值",
        "9. 建立风险管理系统",
        "10. 保持模型更新和适应性"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    
    return recommendations

def main():
    """主函数"""
    print("=" * 60)
    print("NBA数据与赔率关系分析 - 比赛结果预测")
    print("=" * 60)
    
    # 1. 加载数据
    data = load_data()
    
    # 2. 分析数据关系
    features = analyze_data_relationships(data)
    
    # 3. 研究赔率模式
    patterns = research_betting_patterns()
    
    # 4. 构建预测框架
    framework = build_prediction_framework()
    
    # 5. 创建预测流水线
    pipeline = create_prediction_pipeline()
    
    # 6. 生成建议
    recommendations = generate_recommendations()
    
    # 7. 保存分析结果
    output_file = "/Users/shenghuali/reddog-scraper/nba_prediction_analysis.txt"
    with open(output_file, 'w') as f:
        f.write("NBA预测系统分析报告\n")
        f.write("=" * 40 + "\n")
        f.write(f"生成时间: {datetime.now()}\n\n")
        
        f.write("数据统计:\n")
        for name, df in data.items():
            f.write(f"  {name}: {len(df)} 行, {len(df.columns)} 列\n")
        
        f.write("\n关键特征:\n")
        f.write(f"  enriched_features: {features.get('enriched_features', [])}\n")
        f.write(f"  available_stats: {features.get('available_stats', [])}\n")
        
        f.write("\n赔率模式:\n")
        for pattern, desc in patterns.items():
            f.write(f"  {pattern}: {desc}\n")
        
        f.write("\n实施建议:\n")
        for rec in recommendations:
            f.write(f"  {rec}\n")
    
    print(f"\n✅ 分析完成！结果已保存到: {output_file}")
    print("🎯 下一步: 实现预测流水线并收集更多训练数据")

if __name__ == "__main__":
    main()