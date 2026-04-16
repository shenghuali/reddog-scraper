#!/usr/bin/env python3
"""
Discord报告发送脚本
使用OpenClaw的message工具或直接Webhook
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def send_via_openclaw(message):
    """使用OpenClaw CLI发送消息"""
    try:
        # 方法1: 使用当前会话的target
        cmd = ["openclaw", "message", "send", "--target", "discord", "--message", message]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 通过OpenClaw发送成功")
            return True
        else:
            print(f"⚠️ OpenClaw发送失败: {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"⚠️ OpenClaw发送异常: {e}")
        return False

def send_via_webhook(message, webhook_url):
    """使用Discord Webhook发送消息"""
    try:
        import requests
        # Discord消息限制2000字符
        if len(message) > 2000:
            message = message[:1900] + "...\n[消息太长，已截断]"
        
        data = {"content": message}
        response = requests.post(webhook_url, json=data, timeout=10)
        
        if response.status_code in [200, 204]:
            print("✅ 通过Webhook发送成功")
            return True
        else:
            print(f"⚠️ Webhook发送失败: HTTP {response.status_code}")
            return False
    except ImportError:
        print("⚠️ requests库未安装，无法使用Webhook")
        return False
    except Exception as e:
        print(f"⚠️ Webhook发送异常: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: send_to_discord.py <消息文件路径>")
        sys.exit(1)
    
    report_file = sys.argv[1]
    if not os.path.exists(report_file):
        print(f"❌ 报告文件不存在: {report_file}")
        sys.exit(1)
    
    # 读取报告内容
    with open(report_file, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    print(f"📄 报告长度: {len(report_content)} 字符")
    
    # 尝试发送方式
    success = False
    
    # 1. 尝试OpenClaw
    print("尝试通过OpenClaw发送...")
    success = send_via_openclaw(report_content)
    
    # 2. 如果失败，尝试Webhook
    if not success:
        webhook_config = Path("/Users/shenghuali/reddog-scraper/discord-webhook.config")
        if webhook_config.exists():
            with open(webhook_config, 'r') as f:
                for line in f:
                    if line.startswith("WEBHOOK_URL="):
                        webhook_url = line.split('=', 1)[1].strip().strip('"'"'")
                        print("尝试通过Webhook发送...")
                        success = send_via_webhook(report_content, webhook_url)
                        break
    
    if not success:
        print("❌ 所有发送方式都失败")
        print(f"📋 报告内容已保存到: {report_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()