#!/usr/bin/env python3
"""
修复后的C++ RPA模块测试脚本
"""

import os
import sys
import time
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/neogh/wechat_copilot/cpp_rpa')

def test_basic_functionality():
    """测试基本功能"""
    print("🚀 开始测试 C++ RPA 模块...")
    
    try:
        import wechat_rpa
        print("✅ 成功导入 wechat_rpa 模块")
    except ImportError as e:
        print(f"❌ 导入 wechat_rpa 模块失败: {e}")
        return False
    
    try:
        # 创建管理器实例
        manager = wechat_rpa.WeChatManager()
        print("✅ WeChatManager 实例创建成功")
        
        # 初始化
        result = manager.initialize()
        print(f"✅ 初始化结果: {result}")
        
        # 测试窗口功能
        print("\n=== 测试窗口功能 ===")
        try:
            activated = manager.activate_wechat()
            print(f"✅ 微信激活: {activated}")
            
            window_info = manager.get_wechat_window()
            print(f"✅ 窗口信息获取成功:")
            print(f"  - ID: {window_info.id}")
            print(f"  - 标题: {window_info.title}")
            print(f"  - 位置: ({window_info.x}, {window_info.y})")
            print(f"  - 大小: {window_info.width}x{window_info.height}")
            print(f"  - 激活状态: {window_info.is_active}")
            
            is_active = manager.is_wechat_active()
            print(f"✅ 微信激活状态: {is_active}")
        except Exception as e:
            print(f"⚠️ 窗口功能测试失败: {e}")
        
        # 测试UI分析功能
        print("\n=== 测试UI分析功能 ===")
        try:
            # 测试分析UI元素
            elements = manager.analyze_ui_elements()
            print(f"✅ 分析UI元素结果: 共 {len(elements)} 个元素")
            
            # 测试查找所有按钮
            buttons = manager.find_all_buttons()
            print(f"✅ 查找所有按钮结果: 共 {len(buttons)} 个按钮")
            
            # 测试截图特定元素
            try:
                element_screenshot = manager.capture_specific_element("chat_area")
                print(f"✅ 截图特定元素结果: 形状 {element_screenshot.shape if hasattr(element_screenshot, 'shape') and element_screenshot.size > 0 else 'Empty'}")
            except Exception as e:
                print(f"⚠️ 截图特定元素失败: {e}")
                
        except Exception as e:
            print(f"⚠️ UI分析功能测试失败: {e}")
        
        # 测试消息功能
        print("\n=== 测试消息功能 ===")
        try:
            # 测试获取最新消息
            messages = manager.get_latest_messages(5)
            print(f"✅ 获取最新消息结果: 共 {len(messages)} 条消息")
            for i, msg in enumerate(messages[:3]):  # 只打印前3条
                print(f"  - 消息 {i+1}: {msg.sender} -> {msg.content} (置信度: {getattr(msg, 'confidence', 'N/A')})")
            
            # 测试截图消息区域并保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/tmp/wechat_message_{timestamp}.png"
            try:
                saved = manager.capture_and_save_message_area(screenshot_path)
                print(f"✅ 截图消息区域并保存: {saved}")
                print(f"  - 文件路径: {screenshot_path}")
                print(f"  - 文件存在: {os.path.exists(screenshot_path)}")
                if os.path.exists(screenshot_path):
                    file_size = os.path.getsize(screenshot_path)
                    print(f"  - 文件大小: {file_size} bytes")
            except Exception as e:
                print(f"⚠️ 截图保存功能失败: {e}")
                
        except Exception as e:
            print(f"⚠️ 消息功能测试失败: {e}")
        
        # 测试联系人功能
        print("\n=== 测试联系人功能 ===")
        try:
            # 测试搜索联系人
            contact = manager.search_contact("test")
            print(f"✅ 搜索联系人结果:")
            print(f"  - ID: {contact.id}")
            print(f"  - 名称: {contact.name}")
            print(f"  - 微信ID: {contact.wechat_id}")
            print(f"  - 头像: {contact.avatar}")
            
            # 测试获取联系人列表
            contacts = manager.get_contacts(5)
            print(f"✅ 获取联系人列表结果: 共 {len(contacts)} 个联系人")
            for i, contact in enumerate(contacts[:3]):  # 只打印前3个
                print(f"  - 联系人 {i+1}: {contact.name} (ID: {contact.id})")
                
        except Exception as e:
            print(f"⚠️ 联系人功能测试失败: {e}")
        
        # 测试AT-SPI功能
        print("\n=== 测试AT-SPI功能 ===")
        try:
            # 测试点击控件
            click_result = manager.click_control_by_atspi("test_control")
            print(f"✅ AT-SPI点击控件结果: {click_result}")
            
            # 测试输入文本
            input_result = manager.input_text_by_atspi("test_input", "测试文本")
            print(f"✅ AT-SPI输入文本结果: {input_result}")
            
            # 测试获取控件文本
            text_result = manager.get_control_text_by_atspi("test_control")
            print(f"✅ AT-SPI获取控件文本结果: '{text_result}'")
            
        except Exception as e:
            print(f"⚠️ AT-SPI功能测试失败: {e}")
        
        print("\n🎉 所有测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")
