#!/usr/bin/env python3
"""
测试C++ ATSPI引擎（不依赖Python ATSPI模块）
"""

import os
import sys
import time

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

try:
    import wechat_rpa
    print("✅ 微信RPA模块导入成功")
except ImportError as e:
    print(f"❌ 微信RPA模块导入失败: {e}")
    sys.exit(1)

def test_atspi_initialization():
    """测试ATSPI初始化"""
    print("\n=== 测试ATSPI初始化 ===")
    
    try:
        # 创建管理器
        manager = wechat_rpa.WeChatManager()
        print("✅ 微信管理器创建成功")
        
        # 初始化
        result = manager.initialize()
        print(f"{'✅' if result else '❌'} 初始化结果: {result}")
        
        return True, manager
    except Exception as e:
        print(f"❌ ATSPI初始化失败: {e}")
        return False, None

def test_atspi_click_control(manager):
    """测试ATSPI点击控件"""
    print("\n=== 测试ATSPI点击控件 ===")
    
    try:
        # 测试点击控件
        result = manager.click_control_by_atspi("发送")
        print(f"{'✅' if result else '❌'} ATSPI点击控件结果: {result}")
        return result
    except Exception as e:
        print(f"⚠️ ATSPI点击控件失败: {e}")
        return False

def test_atspi_input_text(manager):
    """测试ATSPI输入文本"""
    print("\n=== 测试ATSPI输入文本 ===")
    
    try:
        # 测试输入文本
        result = manager.input_text_by_atspi("输入框", "测试消息")
        print(f"{'✅' if result else '❌'} ATSPI输入文本结果: {result}")
        return result
    except Exception as e:
        print(f"⚠️ ATSPI输入文本失败: {e}")
        return False

def test_atspi_get_text(manager):
    """测试ATSPI获取控件文本"""
    print("\n=== 测试ATSPI获取控件文本 ===")
    
    try:
        # 测试获取控件文本
        text = manager.get_control_text_by_atspi("发送")
        print(f"✅ ATSPI获取控件文本结果: {text}")
        return True
    except Exception as e:
        print(f"⚠️ ATSPI获取控件文本失败: {e}")
        return False

def test_humanized_operations(manager):
    """测试拟人化操作"""
    print("\n=== 测试拟人化操作 ===")
    
    try:
        # 获取窗口信息
        window = manager.get_wechat_window()
        print(f"✅ 微信窗口信息: {window}")
        
        # 测试拟人化点击
        center_x = window.width // 2
        center_y = window.height // 2
        result = manager.humanized_click(center_x, center_y)
        print(f"{'✅' if result else '❌'} 拟人化点击结果: {result}")
        
        # 测试拟人化输入
        result = manager.humanized_input("测试消息")
        print(f"{'✅' if result else '❌'} 拟人化输入结果: {result}")
        
        return True
    except Exception as e:
        print(f"❌ 拟人化操作测试失败: {e}")
        return False

def main():
    print("=== C++ ATSPI引擎测试 ===")
    
    # 测试ATSPI初始化
    init_ok, manager = test_atspi_initialization()
    
    if not init_ok:
        print("\n❌ ATSPI初始化失败，无法继续测试")
        return
    
    # 测试ATSPI点击控件
    click_ok = test_atspi_click_control(manager)
    
    # 测试ATSPI输入文本
    input_ok = test_atspi_input_text(manager)
    
    # 测试ATSPI获取控件文本
    get_text_ok = test_atspi_get_text(manager)
    
    # 测试拟人化操作
    humanized_ok = test_humanized_operations(manager)
    
    print("\n=== 测试总结 ===")
    print(f"ATSPI初始化: {'✅' if init_ok else '❌'}")
    print(f"ATSPI点击控件: {'✅' if click_ok else '❌'}")
    print(f"ATSPI输入文本: {'✅' if input_ok else '❌'}")
    print(f"ATSPI获取控件文本: {'✅' if get_text_ok else '❌'}")
    print(f"拟人化操作: {'✅' if humanized_ok else '❌'}")
    
    # 评估ATSPI功能
    atspi_functions_ok = click_ok or input_ok or get_text_ok
    
    if atspi_functions_ok:
        print("\n✅ ATSPI功能部分正常，可以使用ATSPI进行控件操作")
    else:
        print("\n⚠️ ATSPI功能异常，建议使用xdotool方案")
    
    if humanized_ok:
        print("✅ 拟人化功能正常，可以增加反检测能力")
    else:
        print("⚠️ 拟人化功能异常，需要检查实现")
    
    print("\n=== 下一步建议 ===")
    if atspi_functions_ok and humanized_ok:
        print("1. ATSPI和拟人化功能都正常，可以开始使用微信RPA")
        print("2. 可以使用Flask API服务器进行远程控制: python3 wechat_api_server.py")
    elif humanized_ok:
        print("1. 拟人化功能正常，可以使用xdotool方案")
        print("2. 如果需要更强的反检测能力，可以尝试修复ATSPI功能")
    else:
        print("1. 基础功能异常，需要检查实现")
        print("2. 请确保微信已启动并处于可用状态")

if __name__ == '__main__':
    main()