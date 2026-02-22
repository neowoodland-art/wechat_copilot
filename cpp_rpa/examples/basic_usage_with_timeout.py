#!/usr/bin/env python3
"""
C++ RPA模块使用示例 - 带超时和详细日志
"""

import sys
import os
import time
import signal
import threading
from contextlib import contextmanager

# 添加C++ RPA模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

try:
    import wechat_rpa
    print("✅ 成功导入C++ RPA模块")
except ImportError as e:
    print(f"❌ 导入C++ RPA模块失败: {e}")
    print("请先编译C++ RPA模块")
    sys.exit(1)

@contextmanager
def timeout_context(seconds):
    """超时上下文管理器"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"操作超时 ({seconds}秒)")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def test_with_timeout(func, timeout_seconds, description):
    """带超时的测试函数"""
    print(f"\n开始测试: {description} (超时: {timeout_seconds}秒)")
    start_time = time.time()
    
    try:
        with timeout_context(timeout_seconds):
            result = func()
            elapsed = time.time() - start_time
            print(f"✅ {description} 成功 (耗时: {elapsed:.2f}秒)")
            return result
    except TimeoutError as e:
        elapsed = time.time() - start_time
        print(f"❌ {description} 超时 (已等待: {elapsed:.2f}秒)")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ {description} 失败 (耗时: {elapsed:.2f}秒): {e}")
        return None

def check_wechat_process():
    """检查微信进程是否运行"""
    import subprocess
    try:
        result = subprocess.run(['pgrep', '-f', 'wechat'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"找到 {len(pids)} 个微信进程: {pids}")
            return True
        else:
            print("未找到微信进程")
            return False
    except Exception as e:
        print(f"检查微信进程失败: {e}")
        return False

def check_wechat_windows():
    """检查微信窗口"""
    import subprocess
    try:
        result = subprocess.run(['xdotool', 'search', '--name', '微信'], capture_output=True, text=True)
        if result.returncode == 0:
            windows = result.stdout.strip().split('\n')
            print(f"找到 {len(windows)} 个微信窗口: {windows}")
            return windows
        else:
            print("未找到微信窗口")
            return []
    except Exception as e:
        print(f"检查微信窗口失败: {e}")
        return []

def main():
    """主函数"""
    print("=== C++ RPA模块使用示例 (带超时和详细日志) ===")
    
    # 1. 检查系统状态
    print("\n1. 检查系统状态:")
    check_wechat_process()
    check_wechat_windows()
    
    # 2. 创建微信管理器
    def create_manager():
        return wechat_rpa.WeChatManager()
    
    manager = test_with_timeout(create_manager, 5, "创建微信管理器")
    if manager is None:
        print("无法创建管理器，退出")
        return
    
    # 3. 初始化
    def initialize_manager():
        return manager.initialize()
    
    result = test_with_timeout(initialize_manager, 5, "初始化微信管理器")
    if result is None or not result:
        print("初始化失败，退出")
        return
    
    # 4. 检查微信是否激活
    def check_active():
        return manager.is_wechat_active()
    
    is_active = test_with_timeout(check_active, 3, "检查微信是否激活")
    
    # 5. 获取微信窗口信息
    def get_window():
        return manager.get_wechat_window()
    
    window = test_with_timeout(get_window, 3, "获取微信窗口信息")
    if window:
        print(f"窗口信息: ID={window.id}, 标题={window.title}, 大小={window.width}x{window.height}")
    
    # 6. 激活微信（使用较短超时）
    def activate_wechat():
        return manager.activate_wechat()
    
    result = test_with_timeout(activate_wechat, 10, "激活微信")
    if result is None:
        print("激活微信失败或超时")
        print("\n可能的原因:")
        print("1. 微信进程未运行")
        print("2. 窗口管理器权限不足")
        print("3. 微信窗口ID已变化")
        print("4. 激活命令卡住")
        
        print("\n建议:")
        print("1. 重启微信")
        print("2. 检查xdotool是否正常工作")
        print("3. 尝试手动激活微信窗口")
        return
    
    # 7. 再次检查激活状态
    is_active_after = test_with_timeout(check_active, 3, "激活后检查微信状态")
    
    # 8. 如果激活成功，尝试截图
    if is_active_after:
        def capture_screenshot():
            return manager.capture_message_area()
        
        screenshot = test_with_timeout(capture_screenshot, 5, "截图消息区域")
        if screenshot:
            print(f"截图成功，尺寸: {screenshot.shape}")
            
            # 保存截图
            try:
                import cv2
                filename = f"wechat_screenshot_{int(time.time())}.png"
                cv2.imwrite(filename, screenshot)
                print(f"截图已保存: {filename}")
            except ImportError:
                print("未安装opencv-python，无法保存截图")
            except Exception as e:
                print(f"保存截图失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()