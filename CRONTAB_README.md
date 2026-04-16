# NBA数据抓取Crontab配置指南

## 📋 概述

本文档详细说明了NBA数据抓取系统的crontab配置，包括定时任务设置、Docker重启恢复方案、数据同步流程和故障排除指南。

## 🎯 执行计划

### 定时任务频率

| 任务 | 脚本 | 频率 | 墨尔本时间 | 说明 |
|------|------|------|------------|------|
| 伤病数据 | `nba-injury.py` | 每小时 | 整点 (0分) | 实时更新伤病信息 |
| 赔率数据 | `nba-daily-odds.py` | 每小时 | 第5分钟 | 赔率数据 + 自动同步 |
| 高级统计 | `nba-advanced-stats.py` | 每周 | 周一 9:00 AM | 球队高级统计数据 |
| 数据同步 | `sync_daily_odds.py` | 自动 | 赔率执行后 | 同步到enriched data |

### 维护任务

| 任务 | 频率 | 时间 | 说明 |
|------|------|------|------|
| 日志清理 | 每天 | 3:00 AM | 删除7天前的日志 |
| 数据备份 | 每周 | 周日 2:00 AM | 备份所有CSV和脚本 |
| 备份清理 | 每月 | 1号 4:00 AM | 删除30天前的备份 |
| 状态报告 | 每天 | 12:00 PM | 生成状态报告 |

## 🛠️ 配置文件

### 主要配置文件

1. **`crontab-final-schedule.txt`** - 最终版crontab配置
2. **`crontab-template.txt`** - 标准配置模板
3. **`crontab-backup.txt`** - 当前配置备份

### 脚本文件

1. **`daily_odds_with_sync.sh`** - 赔率抓取+同步wrapper脚本
2. **`sync_to_enriched.py`** - 数据同步脚本
3. **`restore-after-docker-restart.sh`** - Docker重启恢复脚本
4. **`setup-nba-cron.sh`** - 快速设置脚本

## 🚀 快速开始

### 初始设置

```bash
# 1. 应用最终配置
crontab /home/shenghuali/reddog-scraper/crontab-final-schedule.txt

# 2. 备份配置
crontab -l > /home/shenghuali/reddog-scraper/crontab-backup.txt

# 3. 验证配置
crontab -l
```

### 使用快速设置脚本

```bash
bash /home/shenghuali/reddog-scraper/setup-nba-cron.sh
```

## 🐳 Docker重启保护

### 问题分析

- **会丢失**: crontab配置、容器内安装的软件、临时系统配置
- **会保留**: `/home/shenghuali/reddog-scraper/`目录所有内容（ext4挂载）

### 恢复流程

1. **重启前**: 确保配置已备份到`/home/shenghuali/reddog-scraper/crontab-backup.txt`
2. **重启后**: 运行恢复脚本

```bash
bash /home/shenghuali/reddog-scraper/restore-after-docker-restart.sh
```

### 自动恢复内容

1. ✅ 设置墨尔本时区 (Australia/Melbourne)
2. ✅ 恢复crontab配置
3. ✅ 验证Python虚拟环境
4. ✅ 检查NBA脚本完整性
5. ✅ 检查数据目录状态

## 📊 数据流

### 赔率数据同步流程

```
nba-daily-odds.py (抓取)
        ↓
nba-daily-odds.csv (原始数据)
        ↓
sync_to_enriched.py (同步)
        ↓
nba_enriched_data.csv (丰富数据)
```

### 数据文件说明

| 文件 | 描述 | 更新频率 |
|------|------|----------|
| `nba-injury-latest.csv` | 最新伤病数据 | 每小时 |
| `nba-daily-odds.csv` | 每日赔率数据 | 每小时 |
| `nba_enriched_data.csv` | 合并后的丰富数据 | 每小时 |
| `nba-advanced-stats.csv` | 高级统计数据 | 每周 |
| `nba injury/nba-injury_YYYY-MM-DD.csv` | 历史伤病数据 | 每天 |

## 📝 日志管理

### 日志文件

1. **`cron.log`** - 所有cron任务输出（主要日志）
2. **`error.log`** - 错误日志
3. **`status.log`** - 状态报告日志

### 日志查看命令

```bash
# 查看实时日志
tail -f /home/shenghuali/reddog-scraper/cron.log

# 查看最后100行
tail -100 /home/shenghuali/reddog-scraper/cron.log

# 查看特定任务的日志
grep "nba-injury" /home/shenghuali/reddog-scraper/cron.log

# 查看错误日志
cat /home/shenghuali/reddog-scraper/error.log
```

### 日志清理

- 自动清理: 每天凌晨3点删除7天前的日志
- 手动清理: `find /home/shenghuali/reddog-scraper -name "*.log" -type f -mtime +7 -delete`

## 🔧 故障排除

### 常见问题

#### 1. Crontab任务不执行

```bash
# 检查cron服务状态
service cron status

# 检查crontab配置
crontab -l

# 检查日志
tail -f /home/shenghuali/reddog-scraper/cron.log
```

#### 2. Python环境问题

```bash
# 检查Python虚拟环境
ls -la /home/shenghuali/reddog-scraper/venv/

# 测试Python导入
/home/shenghuali/reddog-scraper/venv/bin/python -c "import bs4; print('BeautifulSoup OK')"

# 检查依赖
/home/shenghuali/reddog-scraper/venv/bin/pip list
```

#### 3. 时区问题

```bash
# 检查当前时区
date
cat /etc/timezone

# 设置墨尔本时区
ln -sf /usr/share/zoneinfo/Australia/Melbourne /etc/localtime
echo "Australia/Melbourne" > /etc/timezone
export TZ=Australia/Melbourne
```

#### 4. 数据同步失败

```bash
# 检查源文件
ls -la /home/shenghuali/reddog-scraper/nba-daily-odds.csv

# 手动运行同步脚本
cd /home/shenghuali/reddog-scraper
/home/shenghuali/reddog-scraper/venv/bin/python sync_to_enriched.py

# 检查enriched文件
ls -la /home/shenghuali/reddog-scraper/nba_enriched_data.csv
```

### 手动测试

```bash
# 测试伤病抓取
cd /home/shenghuali/reddog-scraper
/home/shenghuali/reddog-scraper/venv/bin/python nba-injury.py

# 测试赔率抓取+同步
bash daily_odds_with_sync.sh

# 测试高级统计
/home/shenghuali/reddog-scraper/venv/bin/python nba-advanced-stats.py
```

## 🔄 更新和维护

### 更新crontab配置

```bash
# 1. 编辑配置
crontab -e

# 2. 或从模板更新
crontab /home/shenghuali/reddog-scraper/crontab-template.txt

# 3. 备份新配置
crontab -l > /home/shenghuali/reddog-scraper/crontab-backup.txt
```

### 添加新任务

1. 在`crontab-template.txt`中添加新任务
2. 更新`crontab-final-schedule.txt`
3. 应用新配置并备份

### 监控和维护

```bash
# 查看当前运行的任务
ps aux | grep python

# 查看磁盘使用情况
df -h /home/shenghuali/reddog-scraper/

# 查看数据文件大小
du -sh /home/shenghuali/reddog-scraper/*.csv

# 检查最近修改的文件
find /home/shenghuali/reddog-scraper -name "*.csv" -type f -mtime -1
```

## 📁 文件结构

```
/home/shenghuali/reddog-scraper/
├── *.py                          # Python脚本
├── *.csv                         # 数据文件
├── *.sh                          # Shell脚本
├── venv/                         # Python虚拟环境
├── backup/                       # 数据备份目录
├── nba injury/                   # 历史伤病数据
├── crontab-final-schedule.txt    # 最终crontab配置
├── crontab-template.txt          # 配置模板
├── crontab-backup.txt            # 配置备份
├── restore-after-docker-restart.sh # Docker恢复脚本
├── setup-nba-cron.sh             # 快速设置脚本
├── daily_odds_with_sync.sh       # 赔率抓取+同步脚本
├── sync_to_enriched.py           # 数据同步脚本
├── cron.log                      # 主日志文件
├── error.log                     # 错误日志
└── status.log                    # 状态日志
```

## ⏰ 时区说明

- **系统时区**: Australia/Melbourne (墨尔本时间)
- **时区设置**: 已永久配置在系统
- **时间格式**: AEDT (澳大利亚东部夏令时间) / AEST (标准时间)
- **验证命令**: `date` 应显示墨尔本时间

## 📞 支持

### 紧急恢复

1. Docker重启后运行: `bash /home/shenghuali/reddog-scraper/restore-after-docker-restart.sh`
2. 手动恢复crontab: `crontab /home/shenghuali/reddog-scraper/crontab-backup.txt`
3. 重新设置时区: 参考故障排除第3节

### 监控检查点

1. ✅ 每小时应有伤病数据更新
2. ✅ 每小时应有赔率数据更新和同步
3. ✅ 每周一应有高级统计数据更新
4. ✅ 日志文件应持续增长
5. ✅ 无错误日志记录

### 性能指标

- 伤病抓取: 约1-2分钟/次
- 赔率抓取+同步: 约3-5分钟/次
- 高级统计抓取: 约5-10分钟/次
- 磁盘使用: 监控`/home/shenghuali/reddog-scraper/`目录

---

**最后更新**: 2026-04-04  
**维护者**: NBA数据抓取系统  
**文档版本**: v1.0
