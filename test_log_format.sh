#!/bin/bash
# 测试新的日志格式

# 加载日志工具
source /Users/shenghuali/reddog-scraper/log_utils.sh

echo "测试新的日志格式..."

# 初始化
init_log

# 记录各种日志级别
log_info "测试信息日志"
log_success "测试成功日志"
log_error "测试错误日志"
log_warn "测试警告日志"
log_debug "测试调试日志"

# 记录脚本执行
log_script_start "test_script.sh"

# 模拟任务执行
echo "执行任务1..."
sleep 1
log_task "任务1" 0

echo "执行任务2..."
sleep 1
log_task "任务2" 1

# 记录脚本结束
log_script_end "test_script.sh" 1

echo "测试完成，查看日志文件:"
tail -10 "$LOG_FILE"

echo "清理旧日志..."
cleanup_log
echo "清理后日志大小:"
ls -lh "$LOG_FILE"