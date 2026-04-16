# NBA推荐Memo系统使用指南

## 📋 系统概述

这是一个完整的NBA价值投注推荐系统，包含：
1. **盘口推荐系统** (`nba_spread_recommender.py`) - 基于球队效率数据
2. **大小分推荐系统** (`nba_total_recommender.py`) - 基于比赛节奏数据
3. **Memo发布系统** (`memo_publisher.py`) - 格式化并发布推荐
4. **自动化流水线** (`daily_nba_pipeline.sh`) - 一键执行完整流程

## 🚀 快速开始

### 1. 环境设置
```bash
# 确保虚拟环境已激活
cd /data/reddog-scraper
source venv/bin/activate

# 设置Memos环境变量（可选）
export MEMOS_URL="http://localhost:5230"
export MEMOS_TOKEN="your_memo_token_here"
```

### 2. 运行推荐系统
```bash
# 单独运行盘口推荐
python nba_spread_recommender.py

# 单独运行大小分推荐
python nba_total_recommender.py

# 运行完整流水线
./daily_nba_pipeline.sh
```

### 3. 发布Memo
```bash
# 手动发布推荐到Memos
python memo_publisher.py
```

## 📊 系统输出

### 推荐文件
- `spread_recommendation_YYYYMMDD_HHMMSS.json` - 盘口推荐结果
- `total_recommendation_YYYYMMDD_HHMMSS.json` - 大小分推荐结果
- `memo_output_YYYYMMDD_HHMMSS.md` - 本地保存的memo
- `daily_report_YYYYMMDD_HHMMSS.txt` - 每日执行报告

### Memo格式示例
```
🏀 NBA盘口价值投注推荐

📅 日期: 2026-04-06
🎯 对阵: BOS vs GSW

### 📊 数据分析
- 预测盘口: -7.5
- 市场盘口: -6.5
- 价值差异: +1.0分
- 价值评分: 65/100
- 置信度: 高

### 🎯 实力对比
- Net Rating差值: +7.9
- 主场优势: +3.5分
- 节奏调整: +0.05

### 💰 投注建议
- 推荐: 主队让分
- 投注规模: 2.5% 资金
- 理由: 实力差距明显 | 主场优势 | 中等价值差异 | 高置信度预测

#NBA #投注推荐 #数据分析
```

## 🔧 配置说明

### 环境变量
```bash
# 必需：Memos API配置
export MEMOS_URL="http://localhost:5230"  # Memos服务地址
export MEMOS_TOKEN="your_token"           # Memos访问令牌

# 可选：系统路径
export NBA_DATA_DIR="/data/reddog-scraper"  # 数据目录
```

### 数据文件要求
系统需要以下数据文件：
- `nba-advanced-stats.csv` - 球队效率数据 (ORTG/DRTG/Net Rating等)
- `nba_enriched_data.csv` - 富化市场数据 (开盘收盘盘口等)
- `nba-roster.csv` - 球员名单数据 (可选)

## 🎯 算法特点

### 1. 数据驱动
- 基于真实球队效率数据
- 使用多维度特征分析
- 避免主观判断

### 2. 价值投注
- 识别市场定价错误
- 应用CMU研究算法
- 价值评分阈值过滤

### 3. 风险管理
- 半凯利资金管理
- 保守投注规模
- 严格风险控制

## 🔄 自动化部署

### 定时执行（Cron）
```bash
# 每天下午5点执行（比赛开始前）
0 17 * * * cd /data/reddog-scraper && ./daily_nba_pipeline.sh >> /var/log/nba_recommendation.log 2>&1
```

### 系统日志
- 检查 `/var/log/nba_recommendation.log`
- 查看每日报告文件
- 监控memo发布状态

## 🛠️ 故障排除

### 常见问题
1. **虚拟环境问题**
   ```bash
   # 重新创建虚拟环境
   python -m venv venv
   source venv/bin/activate
   pip install pandas numpy requests
   ```

2. **数据文件缺失**
   - 确保CSV文件在正确位置
   - 检查文件权限
   - 验证数据格式

3. **Memos连接失败**
   - 检查MEMOS_URL和MEMOS_TOKEN
   - 验证Memos服务状态
   - 查看网络连接

### 调试模式
```bash
# 详细输出
python -m pdb nba_spread_recommender.py

# 日志记录
./daily_nba_pipeline.sh 2>&1 | tee debug.log
```

## 📚 相关文档

- `infra.md` - 系统基础设施说明
- `NBA_SOP.md` - NBA数据分析标准操作流程
- `memory/lessons.md` - 经验教训记录

## 🎉 使用建议

1. **每日执行** - 比赛开始前运行推荐系统
2. **结果验证** - 记录推荐与实际结果对比
3. **参数优化** - 根据表现调整算法参数
4. **持续改进** - 基于数据反馈优化系统

## 📞 支持

如有问题，请检查：
1. 系统日志文件
2. 错误报告
3. 环境配置
4. 数据完整性