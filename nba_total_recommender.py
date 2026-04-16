#!/usr/bin/env python3
"""
NBA总分盘推荐系统（整理优化版）
- 统一数据目录处理：默认脚本所在目录，可传 data_dir
- 优先读取最新历史/盘口文件
- 统一主客队列名兼容
- 默认只筛未开赛且有总分盘口的比赛
- 保留节奏 + 攻防效率 + 历史对阵 + 轻量凯利
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd


class TotalRecommender:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = os.path.abspath(data_dir or os.path.dirname(__file__))
        self.team_stats_df = None
        self.market_data_df = None
        self.player_data_df = None
        self.injury_data_df = None
        self.min_edge_to_bet = 4.5
        self.min_value_score = 60

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
                    return float(row[col])
                except (TypeError, ValueError):
                    continue
        return float(default)

    @staticmethod
    def _find_team_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
        home_col = 'home_team' if 'home_team' in df.columns else 'home' if 'home' in df.columns else None
        away_col = 'away_team' if 'away_team' in df.columns else 'away' if 'away' in df.columns else None
        return home_col, away_col

    @staticmethod
    def _find_market_total_column(df: pd.DataFrame) -> Optional[str]:
        candidates = ['total', 'close_total', 'open_total', 'opener_total']
        for col in candidates:
            if col in df.columns:
                numeric = pd.to_numeric(df[col], errors='coerce')
                if numeric.notna().any():
                    return col
        return None

    @staticmethod
    def _current_target_date() -> str:
        aus_now = datetime.now()
        if aus_now.hour >= 18:
            return aus_now.strftime('%Y-%m-%d')
        return (aus_now - timedelta(days=1)).strftime('%Y-%m-%d')

    def load_data(self) -> bool:
        try:
            team_stats_path = self._path("nba-advanced-stats.csv")
            if not os.path.exists(team_stats_path):
                print(f"❌ 球队效率文件不存在: {team_stats_path}")
                return False
            self.team_stats_df = pd.read_csv(team_stats_path)
            print(f"✅ 加载球队效率数据: {len(self.team_stats_df)} 支球队")

            market_path = self._find_first_existing([
                self._path("nba_enriched_data.csv"),
                self._path("nba-latest-odds.csv"),
                self._path("nba-daily-odds.csv"),
            ])
            if market_path:
                self.market_data_df = pd.read_csv(market_path)
                self.extract_total_history()
                print(f"✅ 加载市场/历史数据: {os.path.basename(market_path)} ({len(self.market_data_df)} 场比赛)")
            else:
                print("⚠️ 未找到市场数据文件")

            roster_path = self._path("nba-roster.csv")
            if os.path.exists(roster_path):
                self.player_data_df = pd.read_csv(roster_path)
                print(f"✅ 加载球员数据: {len(self.player_data_df)} 名球员")
            else:
                print(f"⚠️ 球员数据文件不存在: {roster_path}")

            injury_path = self._path("nba-injury-latest.csv")
            if os.path.exists(injury_path):
                self.injury_data_df = pd.read_csv(injury_path)
                print(f"✅ 加载伤病数据: {len(self.injury_data_df)} 条记录")
            else:
                print(f"⚠️ 伤病数据文件不存在: {injury_path}")
                self.injury_data_df = None

            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False

    def extract_total_history(self):
        if self.market_data_df is None or self.market_data_df.empty:
            return

        df = self.market_data_df.copy()
        home_col, away_col = self._find_team_columns(df)
        total_col = self._find_market_total_column(df)
        if not home_col or not away_col or not total_col:
            self.market_data_df = df
            return

        for col in ['home_score', 'away_score', total_col]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        score_cols_ok = {'home_score', 'away_score'}.issubset(df.columns)
        if not score_cols_ok:
            self.market_data_df = df
            return

        df['actual_total'] = df['home_score'] + df['away_score']
        completed_mask = (
            df['actual_total'].notna() &
            df[total_col].notna() &
            (df['actual_total'] > 0) &
            df[home_col].notna() &
            df[away_col].notna()
        )

        df.loc[completed_mask, 'total_diff'] = df.loc[completed_mask, 'actual_total'] - df.loc[completed_mask, total_col]
        df.loc[completed_mask, 'over_result'] = (df.loc[completed_mask, 'actual_total'] > df.loc[completed_mask, total_col]).astype(int)
        self.market_data_df = df

    def calculate_injury_impact(self, team: str) -> Tuple[float, List[Dict]]:
        if self.injury_data_df is None or self.injury_data_df.empty:
            return 0.0, []

        team_injuries = self.injury_data_df[self.injury_data_df['team'] == team]
        if team_injuries.empty:
            return 0.0, []

        impact = 0.0
        injury_details = []

        for _, injury in team_injuries.iterrows():
            player = injury.get('player', '')
            status = str(injury.get('status', '')).lower()

            player_impact = 0.0
            if self.player_data_df is not None:
                player_rows = self.player_data_df[
                    (self.player_data_df['team'] == team) &
                    (self.player_data_df['player'].str.contains(player, case=False, na=False))
                ]

                if not player_rows.empty:
                    player_row = player_rows.iloc[0]
                    try:
                        min_per_game = float(player_row.get('min', 0))
                        pts_per_game = float(player_row.get('pts', 0))
                        time_factor = min_per_game / 48.0
                        pts_factor = pts_per_game / 25.0

                        status_weight = 1.0
                        if 'out' in status or 'doubtful' in status:
                            status_weight = 1.5
                        elif 'questionable' in status:
                            status_weight = 1.2

                        player_impact = -(time_factor * pts_factor * status_weight * 1.5)
                        injury_details.append({
                            'team': team,
                            'player': player,
                            'status': status,
                            'min_per_game': min_per_game,
                            'pts_per_game': pts_per_game,
                            'impact': player_impact,
                        })
                    except (ValueError, TypeError):
                        if 'out' in status or 'doubtful' in status:
                            player_impact = -0.8
                        elif 'questionable' in status:
                            player_impact = -0.3
                else:
                    if 'out' in status or 'doubtful' in status:
                        player_impact = -0.8
                    elif 'questionable' in status:
                        player_impact = -0.3
            else:
                if 'out' in status or 'doubtful' in status:
                    player_impact = -0.8
                elif 'questionable' in status:
                    player_impact = -0.3

            impact += player_impact

        total_impact = max(round(impact, 1), -5.0)
        return total_impact, injury_details

    def get_team_stats(self, team: str) -> Dict:
        if self.team_stats_df is None or 'team' not in self.team_stats_df.columns:
            return {}
        rows = self.team_stats_df[self.team_stats_df['team'] == team]
        if rows.empty:
            return {}
        row = rows.iloc[0]
        pace = self._get_value(row, ['pace'], 97)
        return {
            'team': team,
            'pace': pace,
            'ortg': self._get_value(row, ['ortg', 'off_rating'], 110),
            'drtg': self._get_value(row, ['drtg', 'def_rating'], 110),
            'off_efg': self._get_value(row, ['o-eFG%', 'off_efg', 'off_efg_pct'], 0.54),
            'def_efg': self._get_value(row, ['d-eFG%', 'def_efg', 'def_efg_pct'], 0.54),
            'pace_category': self.classify_pace(pace),
        }

    @staticmethod
    def classify_pace(pace: float) -> str:
        if pace > 100:
            return 'fast'
        if pace > 98:
            return 'above_average'
        if pace > 96:
            return 'average'
        if pace > 94:
            return 'below_average'
        return 'slow'

    def calculate_expected_total(self, home_team: str, away_team: str) -> Dict:
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        if not home_stats or not away_stats:
            return {}

        home_points = home_stats['ortg'] * (home_stats['pace'] / 100)
        away_points = away_stats['ortg'] * (away_stats['pace'] / 100)
        base_total = home_points + away_points

        offense_adjustment = (home_stats['off_efg'] + away_stats['off_efg'] - 1.04) * 20
        defense_adjustment = (home_stats['def_efg'] + away_stats['def_efg'] - 1.04) * 15
        pace_match_adjustment = self.calculate_pace_match_adjustment(home_stats, away_stats)
        historical_adjustment, historical_sample = self.get_historical_adjustment(home_team, away_team)

        home_injury_impact, home_injury_details = self.calculate_injury_impact(home_team)
        away_injury_impact, away_injury_details = self.calculate_injury_impact(away_team)
        net_injury_impact = home_injury_impact + away_injury_impact

        raw_total = (
            base_total + offense_adjustment + defense_adjustment +
            pace_match_adjustment + historical_adjustment +
            net_injury_impact * 0.25
        )
        predicted_total = 0.65 * raw_total + 0.35 * base_total
        confidence = self.calculate_total_confidence(home_stats, away_stats, historical_sample)

        return {
            'home_team': home_team,
            'away_team': away_team,
            'predicted_total': round(predicted_total, 1),
            'raw_total': round(raw_total, 1),
            'base_total': round(base_total, 1),
            'offense_adjustment': round(offense_adjustment, 1),
            'defense_adjustment': round(defense_adjustment, 1),
            'pace_match_adjustment': round(pace_match_adjustment, 1),
            'historical_adjustment': round(historical_adjustment, 1),
            'historical_sample': historical_sample,
            'avg_offense': round((home_stats['ortg'] + away_stats['ortg']) / 2, 1),
            'avg_pace': round((home_stats['pace'] + away_stats['pace']) / 2, 1),
            'home_injury_impact': round(home_injury_impact, 1),
            'away_injury_impact': round(away_injury_impact, 1),
            'net_injury_impact': round(net_injury_impact, 1),
            'home_injury_details': home_injury_details,
            'away_injury_details': away_injury_details,
            'confidence': round(confidence, 2),
        }

    @staticmethod
    def calculate_pace_match_adjustment(home_stats: Dict, away_stats: Dict) -> float:
        pace_diff = abs(home_stats['pace'] - away_stats['pace'])
        if pace_diff > 5:
            return pace_diff * 0.25
        if pace_diff > 3:
            return pace_diff * 0.15
        return 0.0

    def get_historical_adjustment(self, home_team: str, away_team: str) -> Tuple[float, int]:
        if self.market_data_df is None or 'total_diff' not in self.market_data_df.columns:
            return 0.0, 0

        df = self.market_data_df
        home_col, away_col = self._find_team_columns(df)
        if not home_col or not away_col:
            return 0.0, 0

        historical_games = df[
            (((df[home_col] == home_team) & (df[away_col] == away_team)) |
             ((df[home_col] == away_team) & (df[away_col] == home_team))) &
            df['total_diff'].notna()
        ].copy()
        sample_size = len(historical_games)
        if sample_size < 4:
            return 0.0, sample_size

        trimmed = historical_games['total_diff'].clip(
            lower=historical_games['total_diff'].quantile(0.2),
            upper=historical_games['total_diff'].quantile(0.8)
        )
        mean_diff = float(trimmed.mean())
        weight = 0.15 if sample_size < 6 else 0.22 if sample_size < 9 else 0.3
        adjustment = max(min(mean_diff * weight, 3.0), -3.0)
        return round(adjustment, 1), sample_size

    @staticmethod
    def calculate_total_confidence(home_stats: Dict, away_stats: Dict, historical_sample: int = 0) -> float:
        confidence = 0.60
        pace_diff = abs(home_stats['pace'] - away_stats['pace'])
        if pace_diff > 8:
            confidence -= 0.10
        elif pace_diff > 5:
            confidence -= 0.06
        elif pace_diff < 2:
            confidence += 0.03

        if home_stats['ortg'] > 115 and away_stats['ortg'] > 115:
            confidence += 0.06
        if home_stats['drtg'] > 115 or away_stats['drtg'] > 115:
            confidence += 0.03
        if historical_sample >= 6:
            confidence += 0.03

        return min(max(confidence, 0.38), 0.82)

    def analyze_total_value(self, prediction: Dict, market_total: float) -> Dict:
        predicted = prediction['predicted_total']
        value_diff = predicted - market_total
        abs_diff = abs(value_diff)

        if abs_diff < self.min_edge_to_bet:
            value_score = 0
        elif abs_diff < 6.0:
            value_score = 1
        elif abs_diff < 8.0:
            value_score = 2
        else:
            value_score = 3

        raw_score = (
            abs_diff * 6.5 +
            prediction['confidence'] * 28 +
            min(prediction.get('historical_sample', 0), 8) * 1.2
        )
        value_score_100 = max(0, min(100, round(raw_score)))
        recommendation = '大分 (Over)' if value_diff > 0 else '小分 (Under)'
        side = 'over' if value_diff > 0 else 'under'

        return {
            'predicted_total': predicted,
            'market_total': market_total,
            'value_diff': round(value_diff, 1),
            'value_score': value_score,
            'value_score_100': value_score_100,
            'recommendation': recommendation,
            'recommendation_side': side,
            'total_type': self.analyze_total_type(predicted),
            'confidence': prediction['confidence'],
        }

    @staticmethod
    def analyze_total_type(predicted_total: float) -> str:
        if predicted_total > 235:
            return '极高总分 (跑轰大战)'
        if predicted_total > 225:
            return '高总分 (进攻主导)'
        if predicted_total > 215:
            return '中等偏上总分'
        if predicted_total > 205:
            return '中等总分'
        if predicted_total > 195:
            return '中等偏下总分'
        return '低总分 (防守大战)'

    @staticmethod
    def kelly_bet_size(edge_points: float, odds: float = 1.91) -> float:
        if edge_points <= 0:
            return 0.0
        scaled_edge = min(edge_points / 24.0, 0.18)
        b = odds - 1
        p = min(max(0.5 + scaled_edge / 2, 0.503), 0.59)
        q = 1 - p
        full_kelly = (b * p - q) / b
        quarter_kelly = full_kelly / 4
        return min(max(quarter_kelly, 0.005), 0.015)

    def generate_total_reasoning(self, prediction: Dict, value_analysis: Dict) -> str:
        reasons = []
        pace_avg = prediction['avg_pace']
        if pace_avg > 100:
            reasons.append(f"快节奏比赛 (平均节奏: {pace_avg:.1f})")
        elif pace_avg > 98:
            reasons.append(f"节奏偏快 (平均节奏: {pace_avg:.1f})")
        elif pace_avg < 95:
            reasons.append(f"慢节奏比赛 (平均节奏: {pace_avg:.1f})")

        off_avg = prediction['avg_offense']
        if off_avg > 120:
            reasons.append(f"双方进攻火力强 (平均ORTG: {off_avg:.1f})")
        elif off_avg > 115:
            reasons.append("进攻效率良好")

        value_diff = value_analysis['value_diff']
        if abs(value_diff) >= 7:
            reasons.append(f"显著总分价值差异: {value_diff:+.1f}分")
        elif abs(value_diff) >= self.min_edge_to_bet:
            reasons.append(f"中等总分价值差异: {value_diff:+.1f}分")

        historical_adjustment = prediction.get('historical_adjustment', 0.0)
        historical_sample = prediction.get('historical_sample', 0)
        if historical_sample >= 4 and abs(historical_adjustment) >= 1.0:
            reasons.append(f"交手历史微调: {historical_adjustment:+.1f}分 ({historical_sample}场)")

        net_injury_impact = prediction.get('net_injury_impact', 0.0)
        if abs(net_injury_impact) >= 1.2:
            reasons.append(f"伤病总分影响: {net_injury_impact:+.1f}")

        reasons.append(f"预期: {value_analysis['total_type']}")
        if prediction['confidence'] > 0.76:
            reasons.append("高置信度预测")
        elif prediction['confidence'] > 0.62:
            reasons.append("中等置信度预测")
        else:
            reasons.append("低置信度预测")
        return ' | '.join(reasons)

    def generate_total_recommendation(self, home_team: str, away_team: str, market_total: float) -> Dict:
        prediction = self.calculate_expected_total(home_team, away_team)
        if not prediction:
            return {}

        value_analysis = self.analyze_total_value(prediction, market_total)
        if abs(value_analysis['value_diff']) < self.min_edge_to_bet:
            return {}

        bet_size = self.kelly_bet_size(abs(value_analysis['value_diff']))

        return {
            'matchup': f"{home_team} vs {away_team}",
            'date': datetime.now().strftime('%Y-%m-%d'),
            'prediction': prediction,
            'market_analysis': value_analysis,
            'betting_advice': {
                'recommendation': value_analysis['recommendation'],
                'side': value_analysis['recommendation_side'],
                'total_type': value_analysis['total_type'],
                'value_score': int(value_analysis['value_score_100']),
                'confidence_level': '高' if value_analysis['confidence'] > 0.76 else '中' if value_analysis['confidence'] > 0.62 else '低',
                'bet_size_percent': round(bet_size * 100, 1),
                'reasoning': self.generate_total_reasoning(prediction, value_analysis),
            },
        }

    def find_todays_best_total_bets(self, matchups: Optional[List[Tuple[str, str, float]]] = None) -> List[Dict]:
        recommendations = []
        if matchups is not None:
            for home, away, market_total in matchups:
                rec = self.generate_total_recommendation(home, away, market_total)
                if rec and rec['market_analysis']['value_score_100'] >= self.min_value_score:
                    recommendations.append(rec)
        else:
            if self.market_data_df is None or self.market_data_df.empty:
                print("⚠️ 市场数据未加载，无法获取今日比赛")
                return []

            df = self.market_data_df.copy()
            home_col, away_col = self._find_team_columns(df)
            total_col = self._find_market_total_column(df)
            if not home_col or not away_col or not total_col:
                print("⚠️ 市场数据缺少必要字段")
                return []

            target_date = self._current_target_date()
            date_cols = [col for col in ['date', 'data_date'] if col in df.columns]
            if date_cols:
                date_col = date_cols[0]
                df = df[df[date_col].astype(str).str.contains(target_date, na=False)]
                print(f"📅 找到 {len(df)} 场今天（美国日期）({target_date}) 的比赛")
            else:
                if {'home_score', 'away_score'}.issubset(df.columns):
                    df = df[(df['home_score'].fillna(0) == 0) & (df['away_score'].fillna(0) == 0)]
                print(f"📅 找到 {len(df)} 场待分析比赛（无日期字段，使用比分筛选）")

            if df.empty:
                print("📅 今天没有可分析的比赛")
                return []

            for _, game in df.iterrows():
                market_total = pd.to_numeric(pd.Series([game.get(total_col)]), errors='coerce').iloc[0]
                if pd.isna(market_total):
                    continue
                rec = self.generate_total_recommendation(game[home_col], game[away_col], float(market_total))
                if rec and rec['market_analysis']['value_score_100'] >= self.min_value_score:
                    recommendations.append(rec)

        recommendations.sort(key=lambda x: x['market_analysis']['value_score_100'], reverse=True)
        return recommendations

    def save_total_recommendation(self, recommendation: Dict, filename: Optional[str] = None) -> str:
        if not filename:
            filename = f"total_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self._path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recommendation, f, indent=2, ensure_ascii=False)
        print(f"✅ 总分推荐已保存: {filepath}")
        return filepath


def main():
    print("📊 NBA总分盘推荐系统（整理优化版）启动...")
    recommender = TotalRecommender()
    if not recommender.load_data():
        return

    recommendations = recommender.find_todays_best_total_bets()
    print(f"\n📊 找到 {len(recommendations)} 个有价值总分投注:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['matchup']}")
        print(f"   预测总分: {rec['prediction']['predicted_total']:.1f}")
        print(f"   市场总分: {rec['market_analysis']['market_total']:.1f}")
        print(f"   价值差异: {rec['market_analysis']['value_diff']:+.1f}")
        print(f"   价值评分: {rec['market_analysis']['value_score_100']}")
        print(f"   推荐: {rec['betting_advice']['recommendation']}")
        print(f"   投注规模: {rec['betting_advice']['bet_size_percent']}%")
        print(f"   理由: {rec['betting_advice']['reasoning']}")


if __name__ == '__main__':
    main()
