#!/usr/bin/env python3
"""
直接测试xdotool命令
"""

import subprocess
import time

def run_command(cmd, timeout=5):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timeout"
    except Exception as e:
        return False, "", str(e)

def main():
    print("=== 直接测试xdotool命令 ===")
    
    # 检查xdotool是否可用
    success, stdout, stderr = run_command("which xdotool")
    if not success:
        print("❌ xdotool不可用")
        print("请安装xdotool: sudo pacman -S xdotool")
        return
    
    print(f"✅ xdotool可用: {stdout.strip()}")
    
    # 测试鼠标移动
    print("\n=== 测试鼠标移动 ===")
    test_x, test_y = 500, 500
    
    print(f"移动鼠标到 ({test_x}, {test_y})...")
    success, stdout, stderr = run_command(f"xdotool mousemove {test_x} {test_y}")
    
    if success:
        print("✅ 鼠标移动成功")
    else:
        print(f"❌ 鼠标移动失败: {stderr}")
    
    # 测试鼠标点击
    print("\n=== 测试鼠标点击 ===")
    print("点击鼠标左键...")
    success, stdout, stderr = run_command("xdotool click 1")
    
    if success:
        print("✅ 鼠标点击成功")
    else:
        print(f"❌ 鼠标点击失败: {stderr}")
    
    # 测试窗口激活
    print("\n=== 测试窗口激活 ===")
    success, stdout, stderr = run_command("xdotool search --class 'wechat'")
    
    if success:
        window_ids = stdout.strip().split('\n')
        if window_ids and window_ids[0]:
            window_id = window_ids[0]
            print(f"找到微信窗口: {window_id}")
            
            print(f"激活窗口 {window_id}...")
            success, stdout, stderr = run_command(f"xdotool windowactivate {window_id}")
            
            if success:
                print("✅ 窗口激活成功")
            else:
                print(f"❌ 窗口激活失败: {stderr}")
        else:
            print("❌ 没有找到微信窗口")
    else:
        print(f"❌ 搜索微信窗口失败: {stderr}")
    
    print("\n=== 总结 ===")
    print("如果xdotool测试失败，可能的原因:")
    print("1. X11权限问题")
    print("2. 显示服务器问题")
    print("3. 微信阻止自动化工具")
    print("\n建议:")
    print("1. 检查X11权限: xhost +")
    print("2. 尝试以root权限运行")
    print("3. 检查微信是否响应自动化")

if __name__ == "__main__":
    main()