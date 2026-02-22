#!/usr/bin/env python3
"""
测试微信窗口激活
"""

import subprocess
import time

def run_command(cmd, timeout=5):
    """运行命令并返回结果"""
    print(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, timeout=timeout, 
                              capture_output=True, text=True)
        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"标准输出:\n{result.stdout}")
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("命令执行超时!")
        return "", "Timeout"
    except Exception as e:
        print(f"执行命令出错: {e}")
        return "", str(e)

def main():
    print("=== 测试微信窗口激活 ===")
    
    # 1. 获取微信窗口ID
    print("\n1. 获取微信窗口ID:")
    wechat_ids, _ = run_command("xdotool search --name '微信'")
    wechat_ids = wechat_ids.strip().split('\n')
    print(f"找到的微信窗口ID: {wechat_ids}")
    
    # 2. 获取每个微信窗口的详细信息
    for i, window_id in enumerate(wechat_ids):
        if not window_id.strip():
            continue
            
        print(f"\n2.{i+1} 微信窗口 {window_id} 的详细信息:")
        
        # 获取窗口名称
        name, _ = run_command(f"xdotool getwindowname {window_id}")
        print(f"窗口名称: {name.strip()}")
        
        # 获取窗口几何信息
        geometry, _ = run_command(f"xdotool getwindowgeometry {window_id}")
        print(f"窗口几何信息:\n{geometry}")
        
        # 获取窗口类
        window_class, _ = run_command(f"xprop -id {window_id} WM_CLASS")
        print(f"窗口类: {window_class}")
        
        # 获取窗口类型
        window_type, _ = run_command(f"xprop -id {window_id} _NET_WM_WINDOW_TYPE")
        print(f"窗口类型: {window_type}")
    
    # 3. 测试激活微信窗口
    if wechat_ids and wechat_ids[0].strip():
        wechat_id = wechat_ids[0].strip()
        print(f"\n3. 测试激活微信窗口 {wechat_id}:")
        
        # 获取当前活动窗口
        current_id, _ = run_command("xdotool getactivewindow")
        print(f"当前活动窗口ID: {current_id.strip()}")
        
        # 尝试激活微信窗口
        print("尝试激活微信窗口...")
        result, _ = run_command(f"xdotool windowactivate --sync {wechat_id}", timeout=10)
        
        # 检查是否成功激活
        time.sleep(1)
        active_id, _ = run_command("xdotool getactivewindow")
        print(f"激活后的活动窗口ID: {active_id.strip()}")
        
        if active_id.strip() == wechat_id:
            print("✅ 微信窗口激活成功!")
        else:
            print("❌ 微信窗口激活失败!")
            
        # 恢复原来的活动窗口
        if current_id.strip():
            run_command(f"xdotool windowactivate {current_id.strip()}")
    
    # 4. 使用wmctrl测试
    print("\n4. 使用wmctrl测试:")
    wmctrl_list, _ = run_command("wmctrl -l")
    print("所有窗口列表:")
    print(wmctrl_list)
    
    # 查找微信窗口
    for line in wmctrl_list.strip().split('\n'):
        if '微信' in line:
            print(f"找到微信窗口: {line}")
            # 提取窗口ID
            parts = line.split()
            if parts:
                hex_id = parts[0]
                print(f"尝试使用wmctrl激活窗口 {hex_id}:")
                run_command(f"wmctrl -ia {hex_id}")
                time.sleep(1)
                
                # 检查是否成功
                active_id, _ = run_command("xdotool getactivewindow")
                print(f"激活后的活动窗口ID: {active_id.strip()}")

if __name__ == "__main__":
    main()