#!/usr/bin/env python3
"""
NBA推荐Memo发布模块
将推荐结果格式化为memo并发布
"""

import json
import os
import sys
import datetime
from typing import Dict, List, Optional
import requests

class MemoPublisher:
    def __init__(self):
        self.data_dir = "/data/reddog-scraper"
        self.memo_url = os.getenv("MEMOS_URL", "http://localhost:5230")
        self.memo_token = os.getenv("MEMOS_TOKEN", "")
        
    def load_recommendation(self, filepath: str) -> Dict:
        """加载推荐结果文件"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载推荐文件失败: {e}")
            return {}
    
    def format_spread_memo(self, recommendation: Dict) -> str:
        """格式化盘口推荐为memo"""
        if not recommendation:
            return ""
            
        prediction = recommendation.get('prediction', {})
        market = recommendation.get('market_analysis', {})
        advice = recommendation.get('betting_advice', {})
        
        memo = f"""🏀 NBA盘口价值投注推荐

📅 日期: {recommendation.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))}
🎯 对阵: {recommendation.get('matchup', '')}

### 📊 数据分析
- **预测盘口**: {prediction.get('predicted_spread', 0):+.1f}
- **市场盘口**: {market.get('market_spread', 0):+.1f}
- **价值差异**: {market.get('value_diff', 0):+.1f}分
- **价值评分**: {market.get('value_score_100', 0)}/100
- **置信度**: {advice.get('confidence_level', '中')}

### 🎯 实力对比
- Net Rating差值: {prediction.get('net_rating_diff', 0):+.1f}
- 主场优势: +{prediction.get('home_advantage', 3.5)}分
- 节奏调整: {prediction.get('pace_factor', 0):+.2f}

### 💰 投注建议
- **推荐**: {advice.get('recommendation', '')}
- **投注规模**: {advice.get('bet_size_percent', 0)}% 资金
- **理由**: {advice.get('reasoning', '')}

### 📈 算法说明
基于球队效率数据(ORTG/DRTG/Net Rating)分析
应用CMU研究的价值评分算法
使用半凯利资金管理策略

#NBA #投注推荐 #数据分析"""
        
        return memo
    
    def format_total_memo(self, recommendation: Dict) -> str:
        """格式化大小分推荐为memo"""
        if not recommendation:
            return ""
            
        prediction = recommendation.get('prediction', {})
        market = recommendation.get('market_analysis', {})
        advice = recommendation.get('betting_advice', {})
        
        memo = f"""📊 NBA大小分价值投注推荐

📅 日期: {recommendation.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))}
🎯 对阵: {recommendation.get('matchup', '')}

### 📊 总分分析
- **预测总分**: {prediction.get('predicted_total', 0):.1f}
- **市场总分**: {market.get('market_total', 0):.1f}
- **价值差异**: {market.get('value_diff', 0):+.1f}分
- **价值评分**: {market.get('value_score_100', 0)}/100
- **总分类型**: {advice.get('total_type', '')}
- **置信度**: {advice.get('confidence_level', '中')}

### ⏱️ 比赛节奏
- **平均节奏**: {prediction.get('avg_pace', 0):.1f}
- **平均进攻效率**: {prediction.get('avg_offense', 0):.1f}
- **进攻调整**: {prediction.get('offense_adjustment', 0):+.1f}
- **防守调整**: {prediction.get('defense_adjustment', 0):+.1f}

### 💰 投注建议
- **推荐**: {advice.get('recommendation', '')}
- **投注规模**: {advice.get('bet_size_percent', 0)}% 资金
- **理由**: {advice.get('reasoning', '')}

### 📈 算法说明
基于比赛节奏(Pace)和进攻防守效率(ORTG/DRTG)
应用CMU研究的总分价值评分算法
使用1/3凯利资金管理策略（更保守）

#NBA #大小分 #数据分析"""
        
        return memo
    
    def post_to_memos(self, content: str, visibility: str = "PUBLIC") -> bool:
        """发布到Memos"""
        if not self.memo_token:
            print("⚠️ MEMOS_TOKEN未设置，保存到本地文件")
            self.save_to_local(content)
            return False
            
        headers = {
            "Authorization": f"Bearer {self.memo_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "content": content,
            "visibility": visibility,
            "resourceList": []
        }
        
        try:
            response = requests.post(
                f"{self.memo_url}/api/v1/memo",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Memo发布成功: {response.json().get('id', '')}")
                return True
            else:
                print(f"❌ Memo发布失败: {response.status_code} - {response.text}")
                self.save_to_local(content)
                return False
                
        except Exception as e:
            print(f"❌ Memo发布异常: {e}")
            self.save_to_local(content)
            return False
    
    def save_to_local(self, content: str):
        """保存到本地文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memo_output_{timestamp}.md"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Memo已保存到本地: {filepath}")
    
    def publish_spread_recommendation(self, filepath: str = None):
        """发布盘口推荐"""
        if not filepath:
            # 查找最新的盘口推荐文件
            spread_files = [f for f in os.listdir(self.data_dir) 
                          if f.startswith("spread_recommendation_") and f.endswith(".json")]
            if not spread_files:
                print("❌ 未找到盘口推荐文件")
                return
            spread_files.sort(reverse=True)
            filepath = os.path.join(self.data_dir, spread_files[0])
        
        print(f"📤 发布盘口推荐: {filepath}")
        recommendation = self.load_recommendation(filepath)
        if not recommendation:
            return
            
        memo_content = self.format_spread_memo(recommendation)
        self.post_to_memos(memo_content)
    
    def publish_total_recommendation(self, filepath: str = None):
        """发布大小分推荐"""
        if not filepath:
            # 查找最新的大小分推荐文件
            total_files = [f for f in os.listdir(self.data_dir) 
                          if f.startswith("total_recommendation_") and f.endswith(".json")]
            if not total_files:
                print("❌ 未找到大小分推荐文件")
                return
            total_files.sort(reverse=True)
            filepath = os.path.join(self.data_dir, total_files[0])
        
        print(f"📤 发布大小分推荐: {filepath}")
        recommendation = self.load_recommendation(filepath)
        if not recommendation:
            return
            
        memo_content = self.format_total_memo(recommendation)
        self.post_to_memos(memo_content)
    
    def publish_combined_recommendation(self):
        """发布综合推荐（盘口+大小分）"""
        # 查找最新的两个推荐文件
        spread_files = [f for f in os.listdir(self.data_dir) 
                      if f.startswith("spread_recommendation_") and f.endswith(".json")]
        total_files = [f for f in os.listdir(self.data_dir) 
                      if f.startswith("total_recommendation_") and f.endswith(".json")]
        
        if not spread_files or not total_files:
            print("❌ 未找到完整的推荐文件")
            return
            
        spread_files.sort(reverse=True)
        total_files.sort(reverse=True)
        
        spread_path = os.path.join(self.data_dir, spread_files[0])
        total_path = os.path.join(self.data_dir, total_files[0])
        
        spread_rec = self.load_recommendation(spread_path)
        total_rec = self.load_recommendation(total_path)
        
        if not spread_rec or not total_rec:
            return
        
        # 创建综合memo
        memo = f"""🏀 NBA今日价值投注综合推荐

📅 日期: {datetime.datetime.now().strftime('%Y-%m-%d')}

## 🎯 盘口推荐
**对阵**: {spread_rec.get('matchup', '')}
- 预测: {spread_rec['prediction'].get('predicted_spread', 0):+.1f}
- 市场: {spread_rec['market_analysis'].get('market_spread', 0):+.1f}
- 价值: {spread_rec['market_analysis'].get('value_diff', 0):+.1f}分
- 评分: {spread_rec['market_analysis'].get('value_score_100', 0)}/100
- 建议: {spread_rec['betting_advice'].get('recommendation', '')}

## 📊 大小分推荐
**对阵**: {total_rec.get('matchup', '')}
- 预测: {total_rec['prediction'].get('predicted_total', 0):.1f}
- 市场: {total_rec['market_analysis'].get('market_total', 0):.1f}
- 价值: {total_rec['market_analysis'].get('value_diff', 0):+.1f}分
- 评分: {total_rec['market_analysis'].get('value_score_100', 0)}/100
- 建议: {total_rec['betting_advice'].get('recommendation', '')}

## 💰 资金管理建议
- 盘口投注: {spread_rec['betting_advice'].get('bet_size_percent', 0)}% (半凯利)
- 大小分投注: {total_rec['betting_advice'].get('bet_size_percent', 0)}% (1/3凯利)

## 📈 算法说明
基于CMU研究的价值投注框架
数据驱动决策，避免主观判断
科学资金管理，控制风险

#NBA #投注推荐 #数据分析 #价值投注"""
        
        self.post_to_memos(memo)

def main():
    """主函数"""
    print("📤 NBA推荐Memo发布系统启动...")
    
    publisher = MemoPublisher()
    
    # 检查环境变量
    if not publisher.memo_token:
        print("⚠️ MEMOS_TOKEN环境变量未设置")
        print("✅ 系统将保存memo到本地文件")
    
    # 发布示例（可以根据需要调整）
    print("\n1. 发布盘口推荐...")
    publisher.publish_spread_recommendation()
    
    print("\n2. 发布大小分推荐...")
    publisher.publish_total_recommendation()
    
    print("\n3. 发布综合推荐...")
    publisher.publish_combined_recommendation()
    
    print("\n✅ Memo发布系统完成")

if __name__ == "__main__":
    main()