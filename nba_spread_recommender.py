#!/usr/bin/env python3
"""
NBA盘口推荐系统（整理优化版）
- 统一列名兼容：nrtg/net_rating, ortg/off_rating, drtg/def_rating
- 统一数据目录处理：默认脚本所在目录，可传 data_dir
- 优先读取最新市场文件
- 过滤已开赛/无盘口比赛
- 保留动态主场优势 + 价值评分 + 半凯利资金管理
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd


class SpreadRecommender:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = os.path.abspath(data_dir or os.path.dirname(__file__))
        self.team_stats_df = None
        self.market_data_df = None
        self.player_data_df = None
        self.home_advantage_base = 3.5

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

    def load_data(self) -> bool:
        try:
            team_stats_path = self._path("nba-advanced-stats.csv")
            if not os.path.exists(team_stats_path):
                print(f"❌ 球队统计文件不存在: {team_stats_path}")
                return False

            self.team_stats_df = pd.read_csv(team_stats_path)
            print(f"✅ 加载球队效率数据: {len(self.team_stats_df)} 支球队")

            market_path = self._find_first_existing([
                self._path("nba-latest-odds.csv"),
                self._path("nba_enriched_data.csv"),
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

            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False

    def _get_team_row(self, team: str) -> Optional[pd.Series]:
        if self.team_stats_df is None or 'team' not in self.team_stats_df.columns:
            return None
        rows = self.team_stats_df[self.team_stats_df['team'] == team]
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

        predicted_spread = (
            net_diff * 0.4 +
            home_advantage * 0.3 +
            off_def_advantage * 0.2 +
            pace_factor * 0.1
        )

        confidence = self.calculate_confidence(home_row, away_row, net_diff, home_advantage)
        display_spread = -abs(predicted_spread) if predicted_spread > 0 else predicted_spread

        return {
            'home_team': home_team,
            'away_team': away_team,
            'net_rating_diff': round(net_diff, 1),
            'home_advantage': home_advantage,
            'off_def_advantage': round(off_def_advantage, 1),
            'def_off_advantage': round(def_off_advantage, 1),
            'pace_factor': round(pace_factor, 2),
            'predicted_spread_raw': round(predicted_spread, 1),
            'predicted_spread_display': round(display_spread, 1),
            'confidence': round(confidence, 2),
        }

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

    def analyze_market_value(self, prediction: Dict, market_spread: float) -> Dict:
        predicted_raw = prediction['predicted_spread_raw']
        value_diff = predicted_raw - market_spread
        confidence = prediction['confidence']
        std_error = max((1.0 - confidence) * 2.5, 0.5)
        z_score = abs(value_diff) / std_error

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

        if abs(value_diff) > 8.0:
            value_score = max(0, value_score - 20)
        elif abs(value_diff) < 1.0:
            value_score = max(0, value_score - 10)

        if value_diff > 0:
            recommendation = '主队让分' if predicted_raw > 0 else '客队受让'
            side = 'home' if predicted_raw > 0 else 'away'
            bet_spread = -abs(predicted_raw) if predicted_raw > 0 else predicted_raw
        else:
            recommendation = '客队受让' if predicted_raw > 0 else '主队让分'
            side = 'away' if predicted_raw > 0 else 'home'
            bet_spread = -predicted_raw if predicted_raw > 0 else predicted_raw

        return {
            'predicted_spread_raw': round(predicted_raw, 1),
            'predicted_spread_display': prediction['predicted_spread_display'],
            'market_spread': market_spread,
            'value_diff': round(value_diff, 1),
            'z_score': round(z_score, 2),
            'value_score': value_score,
            'recommendation': recommendation,
            'side': side,
            'bet_spread': round(bet_spread, 1),
            'confidence': confidence,
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
    def calculate_edge_from_value(value_score: int, value_diff: float) -> float:
        base_edge = value_score / 100.0 * 0.3
        diff_factor = min(abs(value_diff) / 10.0, 1.0) * 0.2
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

        value_diff = value_analysis['value_diff']
        z_score = value_analysis['z_score']
        if abs(value_diff) > 3.0 and z_score > 1.5:
            reasons.append(f"高统计价值 (差异: {value_diff:.1f}分, Z-score: {z_score:.2f})")
        elif abs(value_diff) > 2.0:
            reasons.append(f"中等统计价值 (差异: {value_diff:.1f}分, Z-score: {z_score:.2f})")
        else:
            reasons.append(f"有限统计价值 (差异: {value_diff:.1f}分, Z-score: {z_score:.2f})")

        confidence = prediction['confidence']
        if confidence > 0.8:
            reasons.append("高置信度预测")
        elif confidence > 0.6:
            reasons.append("中等置信度预测")
        else:
            reasons.append("低置信度预测")

        return " | ".join(reasons)

    def generate_recommendation(self, home_team: str, away_team: str, market_spread: float) -> Dict:
        prediction = self.predict_spread(home_team, away_team)
        if not prediction:
            return {}

        value_analysis = self.analyze_market_value(prediction, market_spread)
        edge = self.calculate_edge_from_value(value_analysis['value_score'], value_analysis['value_diff'])
        bet_size = self.kelly_bet_size(edge)

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
                'confidence_level': '高' if value_analysis['confidence'] > 0.8 else '中' if value_analysis['confidence'] > 0.6 else '低',
                'bet_size_percent': round(bet_size * 100, 1),
                'reasoning': self.generate_reasoning(prediction, value_analysis),
            },
        }

    def _resolve_market_columns(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        if self.market_data_df is None:
            return None, None, None, None
        cols = set(self.market_data_df.columns)
        home_col = 'home_team' if 'home_team' in cols else 'home' if 'home' in cols else None
        away_col = 'away_team' if 'away_team' in cols else 'away' if 'away' in cols else None
        close_col = 'close_spread' if 'close_spread' in cols else None
        open_col = 'open_spread' if 'open_spread' in cols else None
        return home_col, away_col, close_col, open_col

    def find_todays_best_spread_bets(self, matchups: Optional[List[Tuple[str, str, float]]] = None) -> List[Dict]:
        recommendations = []
        if matchups:
            for home, away, market_spread in matchups:
                rec = self.generate_recommendation(home, away, market_spread)
                if rec and rec['market_analysis']['value_score'] >= 50:
                    recommendations.append(rec)
        else:
            if self.market_data_df is None or self.market_data_df.empty:
                print("⚠️ 市场数据未加载或为空，无法获取今日比赛")
                return []

            home_col, away_col, close_col, open_col = self._resolve_market_columns()
            if not home_col or not away_col:
                print("⚠️ 市场数据缺少主客队字段")
                return []

            df = self.market_data_df.copy()
            if {'home_score', 'away_score'}.issubset(df.columns):
                df = df[(df['home_score'].fillna(0) == 0) & (df['away_score'].fillna(0) == 0)]

            print(f"📅 找到 {len(df)} 场待分析比赛")
            for _, game in df.iterrows():
                market_spread = None
                if close_col and pd.notna(game.get(close_col)):
                    market_spread = float(game[close_col])
                elif open_col and pd.notna(game.get(open_col)):
                    market_spread = float(game[open_col])
                if market_spread is None:
                    continue

                rec = self.generate_recommendation(game[home_col], game[away_col], market_spread)
                if rec and rec['market_analysis']['value_score'] >= 50:
                    recommendations.append(rec)

        recommendations.sort(key=lambda x: x['market_analysis']['value_score'], reverse=True)
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
    print("🏀 NBA盘口推荐系统（整理优化版）启动...")
    print("=" * 50)
    recommender = SpreadRecommender()
    if not recommender.load_data():
        return

    recommendations = recommender.find_todays_best_spread_bets()
    print(f"\n📊 找到 {len(recommendations)} 个有价值盘口投注:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['matchup']}")
        print(f"   预测盘口: {rec['prediction']['predicted_spread_display']}")
        print(f"   市场盘口: {rec['market_analysis']['market_spread']}")
        print(f"   价值差异: {rec['market_analysis']['value_diff']:+.1f}")
        print(f"   价值评分: {rec['market_analysis']['value_score']}/100")
        print(f"   推荐: {rec['betting_advice']['action']}")
        print(f"   投注盘口: {rec['betting_advice']['bet_spread']}")
        print(f"   投注规模: {rec['betting_advice']['bet_size_percent']}%")
        print(f"   理由: {rec['betting_advice']['reasoning']}")


if __name__ == "__main__":
    main()
