#!/bin/bash
# 日志记录工具 - 统一日志格式

LOG_FILE="/Users/shenghuali/reddog-scraper/cron.log"

# 日志级别
LOG_INFO="INFO"
LOG_SUCCESS="SUCCESS"
LOG_ERROR="ERROR"
LOG_WARN="WARN"
LOG_DEBUG="DEBUG"

# 基础日志函数
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $level: $message" >> "$LOG_FILE"
}

# 具体日志函数
log_info() {
    log_message "$LOG_INFO" "$1"
}

log_success() {
    log_message "$LOG_SUCCESS" "✅ $1"
}

log_error() {
    log_message "$LOG_ERROR" "❌ $1"
}

log_warn() {
    log_message "$LOG_WARN" "⚠️  $1"
}

log_debug() {
    log_message "$LOG_DEBUG" "🔍 $1"
}

# 记录脚本开始
log_script_start() {
    local script_name="$1"
    log_info "脚本开始执行: $script_name"
}

# 记录脚本结束
log_script_end() {
    local script_name="$1"
    local status="$2"
    if [ "$status" -eq 0 ]; then
        log_success "脚本执行成功: $script_name"
    else
        log_error "脚本执行失败: $script_name (退出码: $status)"
    fi
}

# 记录任务执行
log_task() {
    local task_name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        log_success "任务完成: $task_name"
    else
        log_error "任务失败: $task_name"
    fi
}

# 初始化日志文件
init_log() {
    if [ ! -f "$LOG_FILE" ]; then
        touch "$LOG_FILE"
        log_info "日志文件初始化"
    fi
}

# 清理旧日志（保留最近7天）
cleanup_log() {
    local keep_days=7
    local temp_file="/tmp/cron_log_clean.$(date +%s)"
    
    # 提取最近7天的日志
    awk -v keep="$keep_days" '
    BEGIN {
        cutoff = systime() - (keep * 24 * 60 * 60)
    }
    /^\[[0-9]{4}-[0-9]{2}-[0-9]{2} / {
        split($0, parts, /[\[\]]/)
        date_str = parts[2]
        gsub(/-/, " ", date_str)
        gsub(/:/, " ", date_str)
        log_time = mktime(date_str)
        if (log_time > cutoff) {
            print $0
        }
    }
    ' "$LOG_FILE" > "$temp_file"
    
    mv "$temp_file" "$LOG_FILE"
    log_info "日志清理完成，保留最近${keep_days}天记录"
}

# 主函数
main() {
    if [ "$1" = "cleanup" ]; then
        cleanup_log
    else
        echo "用法: $0 {cleanup}"
        echo "  cleanup - 清理旧日志，保留最近7天"
    fi
}

# 如果直接执行，运行主函数
if [ "$0" = "$BASH_SOURCE" ]; then
    main "$@"
fi