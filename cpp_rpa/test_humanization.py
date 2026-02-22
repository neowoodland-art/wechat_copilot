#!/usr/bin/env python3
"""
测试拟人化功能
"""

import os
import sys
import time
import json

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

try:
    import wechat_rpa
    print("✅ 微信RPA模块导入成功")
except ImportError as e:
    print(f"❌ 微信RPA模块导入失败: {e}")
    sys.exit(1)

def test_humanized_click():
    """测试拟人化点击"""
    print("\n=== 测试拟人化点击 ===")
    
    try:
        # 创建管理器
        manager = wechat_rpa.WeChatManager()
        print("✅ 微信管理器创建成功")
        
        # 初始化
        result = manager.initialize()
        print(f"{'✅' if result else '❌'} 初始化结果: {result}")
        
        # 激活微信
        result = manager.activate_wechat()
        print(f"{'✅' if result else '❌'} 激活微信结果: {result}")
        
        # 获取窗口信息
        window = manager.get_wechat_window()
        print(f"✅ 微信窗口信息: {window}")
        
        # 测试拟人化点击
        print("\n测试拟人化点击...")
        
        # 点击窗口中心
        center_x = window.width // 2
        center_y = window.height // 2
        
        print(f"点击位置: ({center_x}, {center_y})")
        result = manager.humanized_click(center_x, center_y)
        print(f"{'✅' if result else '❌'} 拟人化点击结果: {result}")
        
        return True
    except Exception as e:
        print(f"❌ 拟人化点击测试失败: {e}")
        return False

def test_humanized_input():
    """测试拟人化输入"""
    print("\n=== 测试拟人化输入 ===")
    
    try:
        # 创建管理器
        manager = wechat_rpa.WeChatManager()
        print("✅ 微信管理器创建成功")
        
        # 初始化
        result = manager.initialize()
        print(f"{'✅' if result else '❌'} 初始化结果: {result}")
        
        # 激活微信
        result = manager.activate_wechat()
        print(f"{'✅' if result else '❌'} 激活微信结果: {result}")
        
        # 测试拟人化输入
        print("\n测试拟人化输入...")
        
        test_text = "这是一条测试消息"
        print(f"输入文本: {test_text}")
        result = manager.humanized_input(test_text)
        print(f"{'✅' if result else '❌'} 拟人化输入结果: {result}")
        
        return True
    except Exception as e:
        print(f"❌ 拟人化输入测试失败: {e}")
        return False

def test_combined_operations():
    """测试组合操作"""
    print("\n=== 测试组合操作 ===")
    
    try:
        # 创建管理器
        manager = wechat_rpa.WeChatManager()
        print("✅ 微信管理器创建成功")
        
        # 初始化
        result = manager.initialize()
        print(f"{'✅' if result else '❌'} 初始化结果: {result}")
        
        # 激活微信
        result = manager.activate_wechat()
        print(f"{'✅' if result else '❌'} 激活微信结果: {result}")
        
        # 获取窗口信息
        window = manager.get_wechat_window()
        print(f"✅ 微信窗口信息: {window}")
        
        # 组合操作：激活 -> 点击输入框 -> 输入消息 -> 点击发送
        print("\n执行组合操作...")
        
        # 1. 拟人化点击输入框（假设在窗口底部）
        input_x = window.width // 2
        input_y = window.height - 50
        print(f"点击输入框位置: ({input_x}, {input_y})")
        result = manager.humanized_click(input_x, input_y)
        print(f"{'✅' if result else '❌'} 点击输入框结果: {result}")
        
        # 短暂延迟
        time.sleep(1)
        
        # 2. 拟人化输入消息
        test_message = "这是一条拟人化测试消息"
        print(f"输入消息: {test_message}")
        result = manager.humanized_input(test_message)
        print(f"{'✅' if result else '❌'} 输入消息结果: {result}")
        
        # 短暂延迟
        time.sleep(1)
        
        # 3. 拟人化点击发送按钮（假设在输入框右侧）
        send_x = window.width - 50
        send_y = window.height - 50
        print(f"点击发送按钮位置: ({send_x}, {send_y})")
        result = manager.humanized_click(send_x, send_y)
        print(f"{'✅' if result else '❌'} 点击发送按钮结果: {result}")
        
        return True
    except Exception as e:
        print(f"❌ 组合操作测试失败: {e}")
        return False

def main():
    print("=== 微信RPA拟人化功能测试 ===")
    
    # 测试拟人化点击
    click_ok = test_humanized_click()
    
    # 测试拟人化输入
    input_ok = test_humanized_input()
    
    # 测试组合操作
    combined_ok = test_combined_operations()
    
    print("\n=== 测试总结 ===")
    print(f"拟人化点击: {'✅' if click_ok else '❌'}")
    print(f"拟人化输入: {'✅' if input_ok else '❌'}")
    print(f"组合操作: {'✅' if combined_ok else '❌'}")
    
    if click_ok and input_ok and combined_ok:
        print("\n✅ 拟人化功能正常，可以增加反检测能力")
    else:
        print("\n⚠️ 拟人化功能异常，需要检查实现")

if __name__ == '__main__':
    main()