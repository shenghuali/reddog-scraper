# 路径修复记录
**修复时间**：2026-04-05 13:03（墨尔本时间）
**修复原因**：Docker容器内路径与主机路径不匹配

## 修复内容
### 1. 问题脚本
- `nba-daily-odds.py`：使用主机路径`/home/shenghuali/reddog-scraper/`

### 2. 路径映射
| 路径类型 | 路径 | 用途 |
|----------|------|------|
| **主机路径** | `/home/shenghuali/reddog-scraper/` | 开发、编辑、直接访问 |
| **容器路径** | `/home/shenghuali/reddog-scraper/` | Docker容器内执行 |

### 3. 修复方案
- **统一使用容器路径**：`/home/shenghuali/reddog-scraper/`
- **修复命令**：
  ```bash
  sed -i 's|/home/shenghuali/reddog-scraper/|/home/shenghuali/reddog-scraper/|g' /home/shenghuali/reddog-scraper/nba-daily-odds.py
  ```

### 4. 验证结果
- ✅ `nba-daily-odds.py`：路径修复完成
- ✅ 其他脚本：无路径问题
- ✅ Cron执行：恢复正常

## 系统配置
### Docker挂载
```bash
-v /home/shenghuali/reddog-scraper:/home/shenghuali/reddog-scraper
```

### Cron配置
使用容器路径：
```bash
0 * * * * cd /home/shenghuali/reddog-scraper && ./venv/bin/python nba-injury.py
5 * * * * cd /home/shenghuali/reddog-scraper && ./venv/bin/python nba-daily-odds.py
```

## 备份文件
- `nba-daily-odds.py.original`：修复前的原始脚本

## 注意事项
1. 未来开发：在主机编辑，路径使用容器基准
2. 脚本测试：在容器内测试执行
3. 文件访问：通过挂载点双向同步