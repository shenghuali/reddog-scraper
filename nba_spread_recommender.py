#!/usr/bin/env python3
"""
NBA盘口推荐系统（逻辑重构版）
- 统一内部口径：模型先预测主队预期净胜分，再映射为主队盘口
- 市场盘口优先级：spread -> current_spread -> handicap -> close_spread
- 推荐层与预测层拆开：预测分差 / 市场映射 / edge评分 / 下注建议分离
- 增加 no-bet 逻辑，避免轻微优势也硬推
- 输出明确 market_spread_source
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd


class SpreadRecommender:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = os.path.abspath(data_dir or os.path.dirname(__file__))
        self.team_stats_df = None
        self.market_data_df = None
        self.player_data_df = None
        self.injury_data_df = None  # 新增伤病数据
        self.home_advantage_base = 3.5
        self.min_edge_to_bet = 1.0
        self.team_aliases = {'WSH': 'WAS'}
        
        # 投注量分析相关
        self.wager_rules = []
        self.wager_data_loaded = False

    @staticmethod
    def _find_wager_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
        preferred_pairs = [
            ('home_wagers_pct', 'away_wagers_pct'),
            ('home wager', 'away wager'),
        ]
        cols = set(df.columns)
        for home_col, away_col in preferred_pairs:
            if home_col in cols and away_col in cols:
                return home_col, away_col

        home_wager_col = None
        away_wager_col = None
        for col in df.columns:
            col_lower = col.lower()
            if 'wager' not in col_lower:
                continue
            if 'home' in col_lower and home_wager_col is None:
                home_wager_col = col
            elif 'away' in col_lower and away_wager_col is None:
                away_wager_col = col
        return home_wager_col, away_wager_col

    def _analyze_wager_patterns(self):
        """分析投注量与盘口胜率的关系，生成轻量调整规则"""
        self.wager_rules = []
        self.wager_data_loaded = False

        if self.market_data_df is None or self.market_data_df.empty:
            return

        df = self.market_data_df.copy()
        home_wager_col, away_wager_col = self._find_wager_columns(df)
        if not home_wager_col or not away_wager_col or 'current_spread' not in df.columns:
            return

        for col in ['current_spread', 'home_score', 'away_score']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['home_wager_pct'] = pd.to_numeric(df[home_wager_col], errors='coerce')
        df['away_wager_pct'] = pd.to_numeric(df[away_wager_col], errors='coerce')

        wager_df = df.dropna(subset=['current_spread', 'home_wager_pct', 'away_wager_pct', 'home_score', 'away_score']).copy()
        if len(wager_df) < 50:
            return

        wager_df['actual_margin'] = wager_df['home_score'] - wager_df['away_score']
        wager_df['home_cover_margin'] = wager_df['actual_margin'] + wager_df['current_spread']
        wager_df['home_cover'] = wager_df['home_cover_margin'] > 0
        wager_df['away_cover'] = wager_df['home_cover_margin'] < 0
        wager_df['wager_bias'] = wager_df['home_wager_pct'] - 50.0

        bias_groups = [
            ('away_heavy', -50, -8),
            ('balanced', -8, 8),
            ('home_heavy', 8, 50),
        ]

        for group_name, min_bias, max_bias in bias_groups:
            group = wager_df[(wager_df['wager_bias'] >= min_bias) & (wager_df['wager_bias'] < max_bias)].copy()
            if len(group) < 12:
                continue

            home_cover_rate = float(group['home_cover'].mean())
            away_cover_rate = float(group['away_cover'].mean())
            cover_margin_mean = float(group['home_cover_margin'].mean())
            edge_side = 'home' if cover_margin_mean > 0 else 'away' if cover_margin_mean < 0 else 'pass'
            edge_strength = abs(cover_margin_mean)

            adjustment = 0.0
            if edge_strength >= 1.5:
                adjustment = max(min(cover_margin_mean * 0.35, 1.25), -1.25)
            elif edge_strength >= 0.75:
                adjustment = max(min(cover_margin_mean * 0.2, 0.75), -0.75)

            self.wager_rules.append({
                'group': group_name,
                'min_bias': min_bias,
                'max_bias': max_bias,
                'sample_size': int(len(group)),
                'home_cover_rate': round(home_cover_rate, 4),
                'away_cover_rate': round(away_cover_rate, 4),
                'avg_home_cover_margin': round(cover_margin_mean, 3),
                'edge_side': edge_side,
                'adjustment': round(adjustment, 2),
            })

        self.wager_data_loaded = bool(self.wager_rules)
        if self.wager_rules:
            print(f"✅ 投注量分析完成: 基于 {len(wager_df)} 场比赛")
            for rule in self.wager_rules:
                print(
                    f"  {rule['group']}: {rule['edge_side']} edge {rule['avg_home_cover_margin']:+.2f}, "
                    f"adjustment {rule['adjustment']:+.2f}, 样本 {rule['sample_size']}"
                )

    def get_wager_adjustment(self, home_wager_pct: Optional[float], away_wager_pct: Optional[float]) -> float:
        """根据投注量给出对主队预测净胜分的微调值"""
        if not self.wager_rules or home_wager_pct is None or pd.isna(home_wager_pct):
            return 0.0

        try:
            wager_bias = float(home_wager_pct) - 50.0
        except (TypeError, ValueError):
            return 0.0

        for rule in self.wager_rules:
            if rule['min_bias'] <= wager_bias < rule['max_bias']:
                return float(rule['adjustment'])
        return 0.0

    def _path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    @staticmethod
    def _find_first_existing(paths: List[str]) -> Optional[str]:
        for path in paths:
            if os.path.exists(path):
                return path
        return None

    @staticmethod
    def _get_value(row: pd.Series, aliases: List[str], default=0.0) -> float:
        for col in aliases:
            if col in row and pd.notna(row[col]):
                try:
                    return float(str(row[col]).replace('+', ''))
                except (TypeError, ValueError):
                    continue
        return float(default)

    @staticmethod
    def margin_to_home_spread(predicted_margin: float) -> float:
        return round(-predicted_margin, 1)

    @staticmethod
    def classify_bet_side(edge: float) -> Tuple[str, str]:
        if edge > 0:
            return '主队让分', 'home'
        return '客队受让', 'away'

    @staticmethod
    def classify_edge_strength(edge: float) -> str:
        abs_edge = abs(edge)
        if abs_edge >= 5:
            return '极强'
        if abs_edge >= 3:
            return '较强'
        if abs_edge >= 1.5:
            return '中等'
        return '轻微'

    def load_data(self) -> bool:
        try:
            team_stats_path = self._path("nba-advanced-stats.csv")
            if not os.path.exists(team_stats_path):
                print(f"❌ 球队统计文件不存在: {team_stats_path}")
                return False

            self.team_stats_df = pd.read_csv(team_stats_path, encoding='utf-8-sig')
            print(f"✅ 加载球队效率数据: {len(self.team_stats_df)} 支球队")

            market_path = self._find_first_existing([
                self._path("nba_enriched_data.csv"),
                self._path("nba-latest-odds.csv"),
                self._path("nba-daily-odds.csv"),
            ])
            if market_path:
                self.market_data_df = pd.read_csv(market_path)
                print(f"✅ 加载市场数据: {os.path.basename(market_path)} ({len(self.market_data_df)} 场比赛)")
            else:
                print("⚠️ 未找到市场数据文件")

            roster_path = self._path("nba-roster.csv")
            if os.path.exists(roster_path):
                self.player_data_df = pd.read_csv(roster_path)
                print(f"✅ 加载球员数据: {len(self.player_data_df)} 名球员")
            else:
                print(f"⚠️ 球员数据文件不存在: {roster_path}")
            
            # 加载伤病数据
            injury_path = self._path("nba-injury-latest.csv")
            if os.path.exists(injury_path):
                self.injury_data_df = pd.read_csv(injury_path)
                print(f"✅ 加载伤病数据: {len(self.injury_data_df)} 条记录")
            else:
                print(f"⚠️ 伤病数据文件不存在: {injury_path}")
                self.injury_data_df = None
            
            # 数据加载完成后进行投注量分析
            self._analyze_wager_patterns()

            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False

    def _normalize_team_code(self, team: str) -> str:
        return self.team_aliases.get(team, team)

    def _get_team_row(self, team: str) -> Optional[pd.Series]:
        if self.team_stats_df is None:
            return None
        team_col = 'team' if 'team' in self.team_stats_df.columns else '\ufeffteam' if '\ufeffteam' in self.team_stats_df.columns else None
        if not team_col:
            return None
        normalized_team = self._normalize_team_code(team)
        rows = self.team_stats_df[self.team_stats_df[team_col] == normalized_team]
        if rows.empty:
            return None
        return rows.iloc[0]

    def calculate_dynamic_home_advantage(self, home_team: str, away_team: str) -> float:
        home_row = self._get_team_row(home_team)
        away_row = self._get_team_row(away_team)
        if home_row is None or away_row is None:
            return self.home_advantage_base

        advantage = self.home_advantage_base
        away_def = self._get_value(away_row, ['drtg', 'def_rating'], 110)
        if away_def > 115:
            advantage += 1.0
        elif away_def < 108:
            advantage -= 0.5

        home_off = self._get_value(home_row, ['ortg', 'off_rating'], 110)
        if home_off > 115:
            advantage += 0.5
        elif home_off < 105:
            advantage -= 0.5

        home_pace = self._get_value(home_row, ['pace'], 100)
        away_pace = self._get_value(away_row, ['pace'], 100)
        advantage += (home_pace - away_pace) * 0.05

        return round(max(min(advantage, 5.0), 2.0), 1)

    def calculate_injury_impact(self, team: str) -> Tuple[float, List[Dict]]:
        """计算球队伤病影响（负值表示负面影响），结合伤病数据和球员数据
        返回: (总影响分, 伤病详情列表)
        """
        if self.injury_data_df is None or self.injury_data_df.empty:
            return 0.0, []
        
        # 获取该队伤病球员
        team_injuries = self.injury_data_df[self.injury_data_df['team'] == team]
        if team_injuries.empty:
            return 0.0, []
        
        impact = 0.0
        injury_details = []
        
        for _, injury in team_injuries.iterrows():
            player = injury.get('player', '')
            status = str(injury.get('status', '')).lower()
            
            # 在球员数据中查找该球员
            player_impact = 0.0
            player_min = 0.0
            player_pts = 0.0
            player_pos = ''
            
            if self.player_data_df is not None:
                player_rows = self.player_data_df[
                    (self.player_data_df['team'] == team) & 
                    (self.player_data_df['player'].str.contains(player, case=False, na=False))
                ]
                
                if not player_rows.empty:
                    player_row = player_rows.iloc[0]
                    
                    # 基于上场时间、得分、位置计算影响
                    try:
                        min_per_game = float(player_row.get('min', 0))
                        pts_per_game = float(player_row.get('pts', 0))
                        pos = str(player_row.get('pos', '')).upper()
                        gp = int(player_row.get('gp', 0))
                        
                        player_min = min_per_game
                        player_pts = pts_per_game
                        player_pos = pos
                        
                        # 基础影响：上场时间权重（分钟/48）* 得分贡献
                        time_factor = min_per_game / 48.0  # 0-1范围
                        pts_factor = pts_per_game / 30.0   # 假设30分为顶
                        
                        # 位置权重：中锋/前锋影响更大
                        pos_weight = 1.0
                        if 'C' in pos:
                            pos_weight = 1.4  # 中锋对防守影响大
                        elif 'F' in pos:
                            pos_weight = 1.2  # 前锋全能影响
                        
                        # 出场次数权重：常规首发影响更大
                        gp_weight = 1.0 + min(gp / 82.0, 0.3)  # 最多增加30%
                        
                        # 伤病状态权重
                        status_weight = 1.0
                        if 'out' in status or 'doubtful' in status:
                            status_weight = 1.5  # 确定缺阵影响大
                        elif 'questionable' in status:
                            status_weight = 1.2  # 可能缺阵
                        
                        # 综合影响（负值表示负面影响）
                        player_impact = -(time_factor * pts_factor * pos_weight * gp_weight * status_weight * 2.5)
                        
                    except (ValueError, TypeError) as e:
                        # 如果解析失败，使用简化逻辑
                        if 'out' in status or 'doubtful' in status:
                            player_impact = -1.5
                        elif 'questionable' in status:
                            player_impact = -0.5
                        else:
                            player_impact = -0.3
            else:
                # 没有球员数据，使用简化逻辑
                if 'out' in status or 'doubtful' in status:
                    player_impact = -1.5
                elif 'questionable' in status:
                    player_impact = -0.5
                else:
                    player_impact = -0.3
            
            impact += player_impact
            
            # 记录详细影响
            injury_details.append({
                'team': team,
                'player': player,
                'status': status,
                'min_per_game': player_min,
                'pts_per_game': player_pts,
                'pos': player_pos,
                'impact': player_impact
            })
        
        total_impact = max(round(impact, 1), -8.0)  # 最大影响 -8分
        return total_impact, injury_details
    
    def calculate_confidence(self, home_row: pd.Series, away_row: pd.Series, net_diff: float, home_advantage: float) -> float:
        confidence = 0.6

        home_games = self._get_value(home_row, ['games_played', 'g'], 0)
        away_games = self._get_value(away_row, ['games_played', 'g'], 0)
        confidence += min(min(home_games, away_games) / 20.0, 1.0) * 0.2

        rating_diff = abs(net_diff)
        if rating_diff > 10:
            confidence += 0.15
        elif rating_diff > 5:
            confidence += 0.1
        elif rating_diff > 2:
            confidence += 0.05

        home_off = self._get_value(home_row, ['ortg', 'off_rating'], 110)
        home_def = self._get_value(home_row, ['drtg', 'def_rating'], 110)
        away_off = self._get_value(away_row, ['ortg', 'off_rating'], 110)
        away_def = self._get_value(away_row, ['drtg', 'def_rating'], 110)

        if home_off > 115 and home_def < 110:
            confidence += 0.05
        if away_off < 110 and away_def > 115:
            confidence += 0.05
        if 2.5 <= home_advantage <= 4.5:
            confidence += 0.05

        return min(confidence, 0.95)

    def predict_spread(self, home_team: str, away_team: str) -> Optional[Dict]:
        home_row = self._get_team_row(home_team)
        away_row = self._get_team_row(away_team)
        if home_row is None or away_row is None:
            print(f"⚠️ 找不到球队数据: {home_team} 或 {away_team}")
            return None

        home_net = self._get_value(home_row, ['nrtg', 'net_rating'], 0)
        away_net = self._get_value(away_row, ['nrtg', 'net_rating'], 0)
        net_diff = home_net - away_net

        home_advantage = self.calculate_dynamic_home_advantage(home_team, away_team)
        home_off = self._get_value(home_row, ['ortg', 'off_rating'], 110)
        away_def = self._get_value(away_row, ['drtg', 'def_rating'], 110)
        off_def_advantage = home_off - away_def

        home_def = self._get_value(home_row, ['drtg', 'def_rating'], 110)
        away_off = self._get_value(away_row, ['ortg', 'off_rating'], 110)
        def_off_advantage = away_off - home_def

        home_pace = self._get_value(home_row, ['pace'], 100)
        away_pace = self._get_value(away_row, ['pace'], 100)
        pace_factor = (home_pace - away_pace) * 0.05

        # 计算伤病影响
        home_injury_impact, home_injury_details = self.calculate_injury_impact(home_team)
        away_injury_impact, away_injury_details = self.calculate_injury_impact(away_team)
        net_injury_impact = home_injury_impact - away_injury_impact
        
        predicted_margin = (
            net_diff * 0.35 +
            home_advantage * 0.25 +
            off_def_advantage * 0.15 +
            pace_factor * 0.05 +
            net_injury_impact * 0.2  # 伤病影响占20%权重
        )

        confidence = self.calculate_confidence(home_row, away_row, net_diff, home_advantage)
        predicted_home_spread = self.margin_to_home_spread(predicted_margin)

        return {
            'home_team': home_team,
            'away_team': away_team,
            'net_rating_diff': round(net_diff, 1),
            'home_advantage': home_advantage,
            'off_def_advantage': round(off_def_advantage, 1),
            'def_off_advantage': round(def_off_advantage, 1),
            'pace_factor': round(pace_factor, 2),
            'home_injury_impact': round(home_injury_impact, 1),
            'home_injury_details': home_injury_details,
            'away_injury_impact': round(away_injury_impact, 1),
            'away_injury_details': away_injury_details,
            'net_injury_impact': round(net_injury_impact, 1),
            'predicted_margin': round(predicted_margin, 1),
            'predicted_spread_raw': round(predicted_margin, 1),
            'predicted_home_spread': predicted_home_spread,
            'predicted_spread_display': predicted_home_spread,
            'confidence': round(confidence, 2),
        }

    def analyze_market_value(self, prediction: Dict, market_spread: float, market_spread_source: Optional[str] = None) -> Dict:
        predicted_margin = prediction['predicted_margin']
        predicted_spread = prediction['predicted_home_spread']
        edge = predicted_margin + market_spread
        confidence = prediction['confidence']
        std_error = max((1.0 - confidence) * 2.5, 0.5)
        z_score = abs(edge) / std_error

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

        if abs(edge) > 8.0:
            value_score = max(0, value_score - 20)
        elif abs(edge) < self.min_edge_to_bet:
            value_score = max(0, value_score - 15)

        recommendation, side = self.classify_bet_side(edge)
        no_bet = abs(edge) < self.min_edge_to_bet or value_score == 0
        if no_bet:
            recommendation = '不下注'
            side = 'pass'

        return {
            'predicted_margin': round(predicted_margin, 1),
            'predicted_home_spread': predicted_spread,
            'predicted_spread_raw': round(predicted_margin, 1),
            'predicted_spread_display': predicted_spread,
            'market_spread': market_spread,
            'market_spread_source': market_spread_source,
            'edge': round(edge, 1),
            'value_diff': round(edge, 1),
            'edge_strength': self.classify_edge_strength(edge),
            'z_score': round(z_score, 2),
            'value_score': value_score,
            'recommendation': recommendation,
            'side': side,
            'bet_spread': round(predicted_spread, 1),
            'confidence': confidence,
            'no_bet': no_bet,
        }

    @staticmethod
    def kelly_bet_size(edge: float, odds: float = 1.91) -> float:
        if edge <= 0:
            return 0.0
        b = odds - 1
        p = min(max(0.5 + edge / 2, 0.01), 0.99)
        q = 1 - p
        full_kelly = (b * p - q) / b
        half_kelly = full_kelly / 2
        return min(max(half_kelly, 0.01), 0.05)

    @staticmethod
    def calculate_edge_from_value(value_score: int, edge_points: float) -> float:
        base_edge = value_score / 100.0 * 0.3
        diff_factor = min(abs(edge_points) / 10.0, 1.0) * 0.2
        return base_edge + diff_factor

    def generate_reasoning(self, prediction: Dict, value_analysis: Dict) -> str:
        reasons = []
        net_diff = prediction['net_rating_diff']
        if abs(net_diff) > 5:
            reasons.append(f"显著实力差距 (净效率差: {net_diff:.1f})")
        elif abs(net_diff) > 2:
            reasons.append(f"明显实力差距 (净效率差: {net_diff:.1f})")
        else:
            reasons.append(f"实力相近 (净效率差: {net_diff:.1f})")

        home_advantage = prediction['home_advantage']
        if home_advantage > 4.0:
            reasons.append(f"强主场优势 (+{home_advantage}分)")
        elif home_advantage < 3.0:
            reasons.append(f"弱主场优势 (+{home_advantage}分)")
        else:
            reasons.append(f"标准主场优势 (+{home_advantage}分)")

        edge = value_analysis['edge']
        z_score = value_analysis['z_score']
        if abs(edge) > 3.0 and z_score > 1.5:
            reasons.append(f"高统计价值 (edge: {edge:.1f}分, Z-score: {z_score:.2f})")
        elif abs(edge) > 2.0:
            reasons.append(f"中等统计价值 (edge: {edge:.1f}分, Z-score: {z_score:.2f})")
        else:
            reasons.append(f"有限统计价值 (edge: {edge:.1f}分, Z-score: {z_score:.2f})")

        reasons.append(f"盘口强度: {value_analysis['edge_strength']}")

        confidence = prediction['confidence']
        if confidence > 0.8:
            reasons.append("高置信度预测")
        elif confidence > 0.6:
            reasons.append("中等置信度预测")
        else:
            reasons.append("低置信度预测")

        if value_analysis['no_bet']:
            reasons.append("优势不足，跳过")

        wager_adjustment = prediction.get('wager_adjustment', 0.0)
        home_wager_pct = prediction.get('home_wager_pct')
        away_wager_pct = prediction.get('away_wager_pct')
        if wager_adjustment and home_wager_pct is not None and away_wager_pct is not None:
            reasons.append(
                f"投注量微调: 主{float(home_wager_pct):.0f}%/客{float(away_wager_pct):.0f}% -> {wager_adjustment:+.1f}分"
            )

        # 添加伤病信息
        home_injury_impact = prediction.get('home_injury_impact', 0)
        away_injury_impact = prediction.get('away_injury_impact', 0)
        
        if home_injury_impact < 0 or away_injury_impact < 0:
            injury_text = "伤病影响: "
            injury_parts = []
            if home_injury_impact < 0:
                injury_parts.append(f"主队{-home_injury_impact:.1f}分")
            if away_injury_impact < 0:
                injury_parts.append(f"客队{-away_injury_impact:.1f}分")
            
            if injury_parts:
                injury_text += ", ".join(injury_parts)
                reasons.append(injury_text)

        return " | ".join(reasons)

    def generate_recommendation(self, home_team: str, away_team: str, market_spread: float, market_spread_source: Optional[str] = None, home_wager_pct: Optional[float] = None, away_wager_pct: Optional[float] = None) -> Dict:
        prediction = self.predict_spread(home_team, away_team)
        if not prediction:
            return {}

        wager_adjustment = self.get_wager_adjustment(home_wager_pct, away_wager_pct)
        prediction['wager_adjustment'] = round(wager_adjustment, 2)
        prediction['home_wager_pct'] = home_wager_pct
        prediction['away_wager_pct'] = away_wager_pct

        if wager_adjustment:
            prediction['predicted_margin'] = round(prediction['predicted_margin'] + wager_adjustment, 1)
            prediction['predicted_spread_raw'] = prediction['predicted_margin']
            prediction['predicted_home_spread'] = self.margin_to_home_spread(prediction['predicted_margin'])
            prediction['predicted_spread_display'] = prediction['predicted_home_spread']

        value_analysis = self.analyze_market_value(prediction, market_spread, market_spread_source)
        confidence_level = '高' if value_analysis['confidence'] > 0.8 else '中' if value_analysis['confidence'] > 0.6 else '低'

        if value_analysis['no_bet']:
            return {
                'matchup': f"{home_team} vs {away_team}",
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'prediction': prediction,
                'market_analysis': value_analysis,
                'betting_advice': {
                    'action': '不下注',
                    'side': 'pass',
                    'bet_spread': value_analysis['bet_spread'],
                    'value_score': value_analysis['value_score'],
                    'confidence_level': confidence_level,
                    'bet_size_percent': 0.0,
                    'reasoning': self.generate_reasoning(prediction, value_analysis),
                },
            }

        edge_pct = self.calculate_edge_from_value(value_analysis['value_score'], value_analysis['edge'])
        bet_size = self.kelly_bet_size(edge_pct)

        return {
            'matchup': f"{home_team} vs {away_team}",
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'prediction': prediction,
            'market_analysis': value_analysis,
            'betting_advice': {
                'action': value_analysis['recommendation'],
                'side': value_analysis['side'],
                'bet_spread': value_analysis['bet_spread'],
                'value_score': value_analysis['value_score'],
                'confidence_level': confidence_level,
                'bet_size_percent': round(bet_size * 100, 1),
                'reasoning': self.generate_reasoning(prediction, value_analysis),
            },
        }

    def _resolve_market_columns(self, today_df: Optional[pd.DataFrame] = None) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        if self.market_data_df is None:
            return None, None, None, None, None
        
        cols = set(self.market_data_df.columns)
        # 优先使用 home_team/away_team，然后是 home/away
        home_col = None
        for col in ['home_team', 'home']:
            if col in cols:
                home_col = col
                break
        away_col = None
        for col in ['away_team', 'away']:
            if col in cols:
                away_col = col
                break
        
        # 如果提供了今天的数据子集，使用它来检测字段
        target_df = today_df if today_df is not None and not today_df.empty else self.market_data_df
        
        # 盘口字段优先级：current_spread → close_spread → handicap → open_spread
        # spread 字段在数据中是 nan，跳过
        # 检查每个字段在今天比赛中是否有非空值
        current_col = None
        for field in ['current_spread', 'close_spread', 'handicap', 'open_spread']:
            if field in target_df.columns and target_df[field].notna().any():
                current_col = field
                break
        
        close_col = 'close_spread' if 'close_spread' in cols else None
        open_col = 'open_spread' if 'open_spread' in cols else None
        return home_col, away_col, current_col, open_col, close_col

    def find_todays_best_spread_bets(self, matchups: Optional[List[Tuple[str, str, float]]] = None) -> List[Dict]:
        recommendations = []
        if matchups:
            for home, away, market_spread in matchups:
                rec = self.generate_recommendation(home, away, market_spread)
                if rec and not rec['market_analysis']['no_bet'] and rec['market_analysis']['value_score'] >= 50:
                    recommendations.append(rec)
        else:
            if self.market_data_df is None or self.market_data_df.empty:
                print("⚠️ 市场数据未加载或为空，无法获取今日比赛")
                return []

            # 使用与 nba-daily-odds.py 相同的日期逻辑
            # 澳洲时间 18:00 之后，使用今天的美国日期；18:00 之前，使用昨天的美国日期
            aus_now = datetime.now()
            if aus_now.hour >= 18:
                target_date = aus_now.strftime("%Y-%m-%d")
                date_label = "今天"
            else:
                target_date = (aus_now - timedelta(days=1)).strftime("%Y-%m-%d")
                date_label = "昨天（美国日期）"
            
            df = self.market_data_df.copy()
            date_cols = [col for col in ['date', 'data_date'] if col in df.columns]
            
            if date_cols:
                # 使用第一个找到的日期字段
                date_col = date_cols[0]
                # 转换为字符串比较
                df = df[df[date_col].astype(str).str.contains(target_date, na=False)]
                print(f"📅 找到 {len(df)} 场{date_label}（{target_date}）的比赛")
            else:
                # 如果没有日期字段，使用旧的 0-0 比分筛选
                if {'home_score', 'away_score'}.issubset(df.columns):
                    df = df[(df['home_score'].fillna(0) == 0) & (df['away_score'].fillna(0) == 0)]
                print(f"📅 找到 {len(df)} 场待分析比赛（无日期字段，使用比分筛选）")
            
            # 使用今天比赛的数据子集来检测字段
            home_col, away_col, current_col, open_col, close_col = self._resolve_market_columns(df)
            if not home_col or not away_col:
                print("⚠️ 市场数据缺少主客队字段")
                return []
            for _, game in df.iterrows():
                market_spread = None
                market_source = None
                if current_col and pd.notna(game.get(current_col)):
                    market_spread = float(game[current_col])
                    market_source = current_col
                elif open_col and pd.notna(game.get(open_col)):
                    market_spread = float(game[open_col])
                    market_source = open_col
                elif close_col and pd.notna(game.get(close_col)):
                    market_spread = float(game[close_col])
                    market_source = close_col
                if market_spread is None:
                    continue

                home_wager_pct = pd.to_numeric(game.get('home_wagers_pct'), errors='coerce') if 'home_wagers_pct' in game.index else None
                away_wager_pct = pd.to_numeric(game.get('away_wagers_pct'), errors='coerce') if 'away_wagers_pct' in game.index else None
                if home_wager_pct is not None and pd.isna(home_wager_pct):
                    home_wager_pct = None
                if away_wager_pct is not None and pd.isna(away_wager_pct):
                    away_wager_pct = None

                rec = self.generate_recommendation(
                    game[home_col],
                    game[away_col],
                    market_spread,
                    market_source,
                    home_wager_pct=home_wager_pct,
                    away_wager_pct=away_wager_pct,
                )
                if rec and not rec['market_analysis']['no_bet'] and rec['market_analysis']['value_score'] >= 50:
                    recommendations.append(rec)

        recommendations.sort(key=lambda x: (x['market_analysis']['value_score'], abs(x['market_analysis']['edge'])), reverse=True)
        return recommendations

    def save_recommendation(self, recommendation: Dict, filename: Optional[str] = None) -> str:
        if not filename:
            filename = f"spread_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self._path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recommendation, f, indent=2, ensure_ascii=False)
        print(f"✅ 推荐已保存: {filepath}")
        return filepath



def main():
    print("🏀 NBA盘口推荐系统（逻辑重构版）启动...")
    print("=" * 50)
    recommender = SpreadRecommender()
    if not recommender.load_data():
        return

    recommendations = recommender.find_todays_best_spread_bets()
    print(f"\n📊 找到 {len(recommendations)} 个有价值盘口投注:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['matchup']}")
        print(f"   预测净胜分: {rec['prediction']['predicted_margin']:+.1f}")
        print(f"   预测盘口: {rec['prediction']['predicted_home_spread']:+.1f}")
        print(f"   市场盘口: {rec['market_analysis']['market_spread']:+.1f} ({rec['market_analysis'].get('market_spread_source')})")
        print(f"   Edge: {rec['market_analysis']['edge']:+.1f} [{rec['market_analysis']['edge_strength']}]")
        print(f"   价值评分: {rec['market_analysis']['value_score']}/100")
        print(f"   推荐: {rec['betting_advice']['action']}")
        print(f"   投注盘口: {rec['betting_advice']['bet_spread']:+.1f}")
        print(f"   投注规模: {rec['betting_advice']['bet_size_percent']}%")
        print(f"   理由: {rec['betting_advice']['reasoning']}")


if __name__ == "__main__":
    main()


def backtest_spread_field(data_dir: Optional[str] = None, spread_field: str = "current_spread", min_edge: float = 0.0) -> Dict:
    recommender = SpreadRecommender(data_dir=data_dir)
    if not recommender.load_data() or recommender.market_data_df is None or recommender.market_data_df.empty:
        return {'error': 'data_load_failed'}

    df = recommender.market_data_df.copy()
    if spread_field not in df.columns:
        return {'error': f'missing_field:{spread_field}'}

    results = []
    for _, game in df.iterrows():
        if pd.isna(game.get(spread_field)):
            continue
        if pd.isna(game.get('home_score')) or pd.isna(game.get('away_score')):
            continue
        try:
            market_spread = float(game[spread_field])
            home_score = float(game['home_score'])
            away_score = float(game['away_score'])
        except (TypeError, ValueError):
            continue

        rec = recommender.generate_recommendation(game['home_team'], game['away_team'], market_spread, spread_field)
        if not rec:
            continue

        edge = float(rec['market_analysis']['edge'])
        if abs(edge) < min_edge or rec['market_analysis']['no_bet']:
            continue

        pick = rec['betting_advice']['side']
        if pick not in ('home', 'away'):
            continue

        home_cover = (home_score - away_score) + market_spread > 0
        won = (pick == 'home' and home_cover) or (pick == 'away' and not home_cover)
        results.append({
            'date': game.get('date'),
            'home_team': game.get('home_team'),
            'away_team': game.get('away_team'),
            'edge': round(edge, 1),
            'market_spread': market_spread,
            'pick': pick,
            'won': won,
        })

    total = len(results)
    wins = sum(1 for r in results if r['won'])
    summary = {
        'spread_field': spread_field,
        'min_edge': min_edge,
        'games': total,
        'wins': wins,
        'win_rate': round(wins / total, 3) if total else None,
        'top_examples': sorted(results, key=lambda x: abs(x['edge']), reverse=True)[:10],
    }
    return summary


def compare_spread_backtests(data_dir: Optional[str] = None, min_edge: float = 0.0) -> Dict:
    out = {}
    for field in ['open_spread', 'current_spread', 'close_spread']:
        out[field] = backtest_spread_field(data_dir=data_dir, spread_field=field, min_edge=min_edge)
    return out
