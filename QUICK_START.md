# NBA数据抓取系统 - 快速启动指南

## 🚀 一分钟设置

### 初始配置
```bash
# 应用最终配置
crontab /home/shenghuali/reddog-scraper/crontab-final-schedule.txt

# 备份配置
crontab -l > /home/shenghuali/reddog-scraper/crontab-backup.txt

# 验证
crontab -l
```

### 或使用一键脚本
```bash
bash /home/shenghuali/reddog-scraper/setup-nba-cron.sh
```

## 🔄 Docker重启恢复

### 重启前
```bash
# 确保配置已备份
ls -la /home/shenghuali/reddog-scraper/crontab-backup.txt
```

### 重启后
```bash
# 运行恢复脚本
bash /home/shenghuali/reddog-scraper/restore-after-docker-restart.sh
```

## 📊 任务状态检查

### 查看当前任务
```bash
crontab -l
```

### 查看执行日志
```bash
# 实时日志
tail -f /home/shenghuali/reddog-scraper/cron.log

# 最近100行
tail -100 /home/shenghuali/reddog-scraper/cron.log
```

### 检查数据文件
```bash
# 查看所有CSV文件
ls -lh /home/shenghuali/reddog-scraper/*.csv

# 查看文件行数
wc -l /home/shenghuali/reddog-scraper/*.csv
```

## 🛠️ 常用命令

### 手动执行测试
```bash
# 测试伤病抓取
cd /home/shenghuali/reddog-scraper
./venv/bin/python nba-injury.py

# 测试赔率抓取+同步
bash daily_odds_with_sync.sh

# 测试高级统计
./venv/bin/python nba-advanced-stats.py
```

### 环境检查
```bash
# 检查时区
date
cat /etc/timezone

# 检查Python环境
./venv/bin/python -c "import bs4; print('OK')"
```

### 故障排查
```bash
# 查看错误日志
cat /home/shenghuali/reddog-scraper/error.log

# 检查cron服务
service cron status

# 查看进程
ps aux | grep python
```

## ⚡ 紧急操作

### 重置crontab
```bash
# 从备份恢复
crontab /home/shenghuali/reddog-scraper/crontab-backup.txt

# 从模板恢复
crontab /home/shenghuali/reddog-scraper/crontab-template.txt
```

### 重置时区
```bash
ln -sf /usr/share/zoneinfo/Australia/Melbourne /etc/localtime
echo "Australia/Melbourne" > /etc/timezone
export TZ=Australia/Melbourne
```

## 📁 重要文件位置

| 文件 | 用途 | 位置 |
|------|------|------|
| 主配置 | crontab配置 | `crontab-final-schedule.txt` |
| 配置备份 | 恢复用备份 | `crontab-backup.txt` |
| 恢复脚本 | Docker重启恢复 | `restore-after-docker-restart.sh` |
| 主日志 | 所有任务日志 | `cron.log` |
| 错误日志 | 错误记录 | `error.log` |
| 赔率脚本 | 赔率+同步 | `daily_odds_with_sync.sh` |
| 同步脚本 | 数据同步 | `sync_to_enriched.py` |

## ⏰ 执行时间表（墨尔本时间）

- **伤病数据**: 每小时整点 (0分)
- **赔率数据**: 每小时第5分钟 (自动同步)
- **高级统计**: 每周一 9:00 AM
- **日志清理**: 每天 3:00 AM
- **数据备份**: 每周日 2:00 AM

## 📞 快速诊断

### 系统正常迹象
1. ✅ `cron.log`文件持续增长
2. ✅ CSV文件时间戳每小时更新
3. ✅ 无`error.log`错误记录
4. ✅ `date`命令显示墨尔本时间

### 常见问题解决
1. **任务不执行** → 检查`cron.log`和`service cron status`
2. **Python错误** → 检查`./venv/bin/python -c "import bs4"`
3. **时区错误** → 运行时区重置命令
4. **数据不同步** → 手动运行`bash daily_odds_with_sync.sh`

---

**提示**: 详细文档请查看 `CRONTAB_README.md`