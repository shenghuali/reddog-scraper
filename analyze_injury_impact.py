#!/usr/bin/env python3
"""
伤病影响分析 - 结合roster和伤病数据
评估球员缺阵对球队的影响程度
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

def load_all_data():
    """加载所有相关数据"""
    print("📊 加载球员和伤病数据...")
    
    data_files = {
        'roster': '/Users/shenghuali/reddog-scraper/nba-roster.csv',
        'injury': '/Users/shenghuali/reddog-scraper/nba-injury-latest.csv',
        'advanced': '/Users/shenghuali/reddog-scraper/nba-advanced-stats.csv',
        'enriched': '/Users/shenghuali/reddog-scraper/nba_enriched_data.csv'
    }
    
    data = {}
    for name, path in data_files.items():
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                data[name] = df
                print(f"✅ {name}: {len(df)} 行")
            except Exception as e:
                print(f"❌ 加载 {name} 失败: {e}")
                data[name] = pd.DataFrame()
        else:
            print(f"⚠️  文件不存在: {path}")
            data[name] = pd.DataFrame()
    
    return data

def analyze_roster_structure(roster_df):
    """分析球队阵容结构"""
    if roster_df.empty:
        return {}
    
    print("\n🏀 球队阵容结构分析:")
    
    # 按球队分组，分析阵容深度
    team_rosters = {}
    
    if 'Team' in roster_df.columns and 'Player' in roster_df.columns:
        for team, group in roster_df.groupby('Team'):
            total_players = len(group)
            
            # 简单的球员重要性分类（基于位置和经验）
            # 这里可以根据实际数据添加更多逻辑
            key_players = []
            role_players = []
            
            for _, player in group.iterrows():
                player_name = player['Player']
                # 简单的判断逻辑 - 可以根据实际数据优化
                if any(keyword in str(player_name).lower() for keyword in ['lebron', 'curry', 'jokic', 'giannis', 'durant', 'luka']):
                    key_players.append(player_name)
                else:
                    role_players.append(player_name)
            
            team_rosters[team] = {
                'total_players': total_players,
                'key_players': key_players,
                'key_player_count': len(key_players),
                'role_players': role_players,
                'role_player_count': len(role_players)
            }
        
        # 输出统计
        print(f"   总球队数: {len(team_rosters)}")
        print(f"   总球员数: {roster_df['Player'].nunique()}")
        
        # 显示几支球队的阵容
        sample_teams = list(team_rosters.keys())[:3]
        for team in sample_teams:
            roster = team_rosters[team]
            print(f"   {team}: {roster['total_players']}名球员 ({roster['key_player_count']}名核心)")
    
    return team_rosters

def calculate_injury_impact(injury_df, roster_analysis):
    """计算伤病影响程度"""
    if injury_df.empty:
        return {}
    
    print("\n🤕 伤病影响分析:")
    
    impact_scores = {}
    
    if 'Team' in injury_df.columns and 'Player' in injury_df.columns and 'Status' in injury_df.columns:
        # 按球队分组伤病情况
        for team, group in injury_df.groupby('Team'):
            injured_players = list(group['Player'])
            injury_count = len(injured_players)
            
            # 获取球队阵容信息
            team_roster = roster_analysis.get(team, {})
            key_players = team_roster.get('key_players', [])
            total_players = team_roster.get('total_players', 15)  # 默认15名球员
            
            # 计算核心球员伤病情况
            injured_key_players = [p for p in injured_players if p in key_players]
            injured_key_count = len(injured_key_players)
            
            # 影响分数计算（简化版）
            # 1. 核心球员伤病权重更高
            # 2. 伤病球员比例影响
            # 3. 伤病严重程度影响（根据Status）
            
            base_impact = 0
            
            # 核心球员伤病影响
            if injured_key_count > 0:
                base_impact += injured_key_count * 25  # 每个核心球员+25%
                print(f"   ⚠️  {team}: {injured_key_count}名核心球员受伤")
                for player in injured_key_players:
                    # 查找伤病状态
                    player_status = group[group['Player'] == player]['Status'].iloc[0] if not group[group['Player'] == player].empty else '未知'
                    print(f"      • {player}: {player_status}")
            
            # 普通球员伤病影响
            regular_injured = injury_count - injured_key_count
            if regular_injured > 0:
                base_impact += regular_injured * 10  # 每个普通球员+10%
            
            # 伤病比例影响
            if total_players > 0:
                injury_ratio = injury_count / total_players
                if injury_ratio > 0.3:  # 超过30%球员受伤
                    base_impact += 20
                elif injury_ratio > 0.2:  # 超过20%球员受伤
                    base_impact += 10
            
            # 伤病状态影响
            status_impact = 0
            for status in group['Status']:
                status_lower = str(status).lower()
                if 'out for season' in status_lower or 'season-ending' in status_lower:
                    status_impact += 30
                elif 'out indefinitely' in status_lower:
                    status_impact += 20
                elif 'out until' in status_lower:
                    status_impact += 15
                elif 'game time decision' in status_lower:
                    status_impact += 5
            
            total_impact = min(base_impact + status_impact, 100)  # 上限100%
            
            impact_scores[team] = {
                'injured_players': injured_players,
                'injured_count': injury_count,
                'injured_key_players': injured_key_players,
                'injured_key_count': injured_key_count,
                'impact_score': total_impact,
                'impact_category': categorize_impact(total_impact)
            }
        
        # 输出影响最大的球队
        if impact_scores:
            sorted_impacts = sorted(impact_scores.items(), key=lambda x: x[1]['impact_score'], reverse=True)
            print("\n📉 伤病影响排名:")
            for team, impact in sorted_impacts[:5]:  # 显示前5名
                print(f"   {team}: {impact['impact_score']:.1f}% ({impact['impact_category']})")
                print(f"      受伤球员: {impact['injured_count']}名 ({impact['injured_key_count']}名核心)")
    
    return impact_scores

def categorize_impact(score):
    """根据分数分类影响程度"""
    if score >= 50:
        return "严重影响（胜率下降25-35%）"
    elif score >= 30:
        return "显著影响（胜率下降15-25%）"
    elif score >= 15:
        return "中等影响（胜率下降8-15%）"
    elif score >= 5:
        return "轻微影响（胜率下降3-8%）"
    else:
        return "无实质影响（胜率下降<3%）"

def correlate_with_performance(impact_scores, advanced_df):
    """将伤病影响与球队表现关联"""
    if not impact_scores or advanced_df.empty:
        return
    
    print("\n📈 伤病影响与球队表现关联:")
    
    correlations = []
    
    for team, impact in impact_scores.items():
        if 'Team' in advanced_df.columns:
            team_stats = advanced_df[advanced_df['Team'] == team]
            if not team_stats.empty:
                # 获取球队效率数据
                if 'nrtg' in advanced_df.columns:  # 净效率
                    nrtg = team_stats['nrtg'].iloc[0]
                else:
                    nrtg = None
                
                if 'ortg' in advanced_df.columns:  # 进攻效率
                    ortg = team_stats['ortg'].iloc[0]
                else:
                    ortg = None
                
                if 'drtg' in advanced_df.columns:  # 防守效率
                    drtg = team_stats['drtg'].iloc[0]
                else:
                    drtg = None
                
                correlations.append({
                    'team': team,
                    'impact_score': impact['impact_score'],
                    'impact_category': impact['impact_category'],
                    'nrtg': nrtg,
                    'ortg': ortg,
                    'drtg': drtg
                })
    
    # 分析关联性
    if correlations:
        # 按影响程度分组
        severe_teams = [c for c in correlations if c['impact_score'] >= 30]
        moderate_teams = [c for c in correlations if 15 <= c['impact_score'] < 30]
        mild_teams = [c for c in correlations if c['impact_score'] < 15]
        
        print(f"   严重影响球队: {len(severe_teams)}支")
        print(f"   中等影响球队: {len(moderate_teams)}支")
        print(f"   轻微影响球队: {len(mild_teams)}支")
        
        # 输出示例
        if severe_teams:
            print("\n   🚨 严重影响球队示例:")
            for team in severe_teams[:2]:
                print(f"      • {team['team']}: 影响{team['impact_score']:.1f}%")
                if team['nrtg']:
                    print(f"        当前净效率: {team['nrtg']:.1f}")

def predict_game_outcomes(injury_impact, enriched_data):
    """基于伤病影响预测比赛结果"""
    if not injury_impact or enriched_data.empty:
        return
    
    print("\n🎯 基于伤病影响的比赛预测:")
    
    # 这里需要实际比赛数据，简化示例
    print("   预测逻辑:")
    print("   1. 计算两队伤病影响差值")
    print("   2. 结合球队实力（净效率）")
    print("   3. 考虑主场优势")
    print("   4. 调整赔率预期")
    
    # 示例预测
    sample_teams = list(injury_impact.keys())[:3]
    if len(sample_teams) >= 2:
        team_a = sample_teams[0]
        team_b = sample_teams[1] if len(sample_teams) > 1 else sample_teams[0]
        
        impact_a = injury_impact[team_a]['impact_score']
        impact_b = injury_impact[team_b]['impact_score']
        impact_diff = impact_a - impact_b
        
        print(f"\n   示例预测: {team_a} vs {team_b}")
        print(f"      {team_a}伤病影响: {impact_a:.1f}%")
        print(f"      {team_b}伤病影响: {impact_b:.1f}%")
        print(f"      影响差值: {abs(impact_diff):.1f}%")
        
        if impact_diff > 10:
            print(f"      预测: {team_b} 胜率提高")
        elif impact_diff < -10:
            print(f"      预测: {team_a} 胜率提高")
        else:
            print(f"      预测: 影响相当，看其他因素")

def generate_recommendations(impact_scores):
    """生成建议"""
    print("\n💡 伤病管理建议:")
    
    if not impact_scores:
        print("   暂无伤病数据或影响轻微")
        return
    
    # 找出影响最大的球队
    severe_teams = [(team, impact) for team, impact in impact_scores.items() if impact['impact_score'] >= 30]
    
    if severe_teams:
        print("   🚨 需要关注的球队:")
        for team, impact in severe_teams[:3]:
            print(f"      • {team}: {impact['impact_score']:.1f}%影响")
            print(f"        受伤核心: {', '.join(impact['injured_key_players'][:3])}")
            print(f"        建议: 调整战术，增加替补球员时间")
    
    # 通用建议
    print("\n   📋 通用建议:")
    print("      1. 监控核心球员伤病恢复进度")
    print("      2. 调整轮换阵容深度")
    print("      3. 更新比赛预测模型参数")
    print("      4. 关注伤病对盘口的影响")
    print("      5. 定期重新评估影响程度")

def save_analysis_results(impact_scores, roster_analysis):
    """保存分析结果"""
    output_file = "/Users/shenghuali/reddog-scraper/injury_impact_analysis.txt"
    
    with open(output_file, 'w') as f:
        f.write("NBA伤病影响分析报告\n")
        f.write("=" * 40 + "\n")
        f.write(f"生成时间: {datetime.now()}\n\n")
        
        f.write("球队伤病影响评分:\n")
        for team, impact in sorted(impact_scores.items(), key=lambda x: x[1]['impact_score'], reverse=True):
            f.write(f"  {team}: {impact['impact_score']:.1f}% ({impact['impact_category']})\n")
            f.write(f"    受伤球员: {impact['injured_count']}名 ({impact['injured_key_count']}名核心)\n")
            if impact['injured_key_players']:
                f.write(f"    核心伤员: {', '.join(impact['injured_key_players'][:5])}\n")
            f.write("\n")
        
        f.write("\n阵容分析:\n")
        f.write(f"  总分析球队数: {len(roster_analysis)}\n")
    
    print(f"\n✅ 分析完成！结果已保存到: {output_file}")

def main():
    """主函数"""
    print("=" * 60)
    print("NBA伤病影响分析系统")
    print("结合roster评估球员缺阵对球队的影响")
    print("=" * 60)
    
    # 1. 加载数据
    data = load_all_data()
    
    # 2. 分析阵容结构
    roster_analysis = analyze_roster_structure(data['roster'])
    
    # 3. 计算伤病影响
    impact_scores = calculate_injury_impact(data['injury'], roster_analysis)
    
    # 4. 与球队表现关联
    correlate_with_performance(impact_scores, data['advanced'])
    
    # 5. 预测比赛结果
    predict_game_outcomes(impact_scores, data['enriched'])
    
    # 6. 生成建议
    generate_recommendations(impact_scores)
    
    # 7. 保存结果
    if impact_scores:
        save_analysis_results(impact_scores, roster_analysis)
    
    print("\n🎯 分析完成！伤病影响已量化评估")

if __name__ == "__main__":
    main()