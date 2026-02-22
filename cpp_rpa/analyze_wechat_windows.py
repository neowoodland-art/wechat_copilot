#!/usr/bin/env python3
"""
分析微信窗口结构
"""

import subprocess
import json

def run_command(cmd, timeout=5):
    """运行命令并返回结果"""
    print(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, timeout=timeout, 
                              capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def get_window_tree(window_id):
    """获取窗口的子窗口树"""
    ret, out, err = run_command(f"xwininfo -tree -id {window_id}")
    if ret == 0:
        return out
    return None

def get_window_info(window_id):
    """获取窗口的详细信息"""
    info = {}
    
    # 获取窗口名称
    ret, out, err = run_command(f"xdotool getwindowname {window_id}")
    if ret == 0:
        info['name'] = out.strip()
    
    # 获取窗口类
    ret, out, err = run_command(f"xprop -id {window_id} WM_CLASS")
    if ret == 0:
        info['class'] = out.strip()
    
    # 获取窗口类型
    ret, out, err = run_command(f"xprop -id {window_id} _NET_WM_WINDOW_TYPE")
    if ret == 0:
        info['type'] = out.strip()
    
    # 获取窗口状态
    ret, out, err = run_command(f"xprop -id {window_id} _NET_WM_STATE")
    if ret == 0:
        info['state'] = out.strip()
    
    # 获取窗口几何信息
    ret, out, err = run_command(f"xdotool getwindowgeometry {window_id}")
    if ret == 0:
        info['geometry'] = out.strip()
    
    # 获取窗口进程ID
    ret, out, err = run_command(f"xprop -id {window_id} _NET_WM_PID")
    if ret == 0:
        info['pid'] = out.strip()
    
    return info

def find_all_wechat_windows():
    """查找所有与微信相关的窗口"""
    wechat_windows = []
    
    # 搜索所有窗口
    ret, out, err = run_command("xdotool search --name .")
    if ret != 0:
        return wechat_windows
    
    window_ids = out.strip().split('\n')
    
    for window_id in window_ids:
        if not window_id.strip():
            continue
            
        # 获取窗口名称
        ret, name, err = run_command(f"xdotool getwindowname {window_id}")
        if ret != 0:
            continue
            
        name = name.strip()
        
        # 检查是否是微信相关窗口
        if '微信' in name or 'wechat' in name.lower() or 'WeChat' in name:
            wechat_windows.append(window_id)
    
    return wechat_windows

def main():
    print("=== 分析微信窗口结构 ===")
    
    # 1. 获取所有微信窗口
    print("\n1. 查找所有微信相关窗口:")
    wechat_windows = find_all_wechat_windows()
    
    if not wechat_windows:
        print("未找到微信窗口，请确保微信正在运行")
        return
    
    print(f"找到 {len(wechat_windows)} 个微信相关窗口:")
    
    # 2. 分析每个窗口
    window_details = {}
    for i, window_id in enumerate(wechat_windows):
        print(f"\n2.{i+1} 分析窗口 {window_id}:")
        
        info = get_window_info(window_id)
        window_details[window_id] = info
        
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # 获取窗口树
        tree = get_window_tree(window_id)
        if tree:
            print("  窗口树结构:")
            for line in tree.split('\n')[:10]:  # 只显示前10行
                print(f"    {line}")
    
    # 3. 识别主窗口和任务栏图标
    print("\n3. 窗口分类:")
    main_window = None
    tray_window = None
    
    for window_id, info in window_details.items():
        # 检查是否有WM_CLASS
        if 'class' in info and 'wechat' in info['class'].lower():
            if main_window is None:
                main_window = window_id
                print(f"  主窗口: {window_id} ({info.get('name', 'Unknown')})")
        
        # 检查窗口类型
        if 'type' in info and 'DOCK' in info['type']:
            tray_window = window_id
            print(f"  任务栏图标: {window_id} ({info.get('name', 'Unknown')})")
    
    # 4. 测试窗口激活
    if main_window:
        print(f"\n4. 测试激活主窗口 {main_window}:")
        
        # 获取当前活动窗口
        ret, current_id, err = run_command("xdotool getactivewindow")
        if ret == 0:
            print(f"  当前活动窗口: {current_id.strip()}")
        
        # 尝试激活主窗口
        print("  尝试激活主窗口...")
        ret, out, err = run_command(f"wmctrl -ia {int(main_window, 0):x}")
        
        # 检查结果
        ret, active_id, err = run_command("xdotool getactivewindow")
        if ret == 0:
            print(f"  激活后活动窗口: {active_id.strip()}")
            if active_id.strip() == main_window:
                print("  ✅ 主窗口激活成功")
            else:
                print("  ❌ 主窗口激活失败")
    
    # 5. 保存窗口信息
    print("\n5. 保存窗口信息到文件:")
    with open('wechat_windows.json', 'w', encoding='utf-8') as f:
        json.dump(window_details, f, ensure_ascii=False, indent=2)
    print("  窗口信息已保存到 wechat_windows.json")

if __name__ == "__main__":
    main()