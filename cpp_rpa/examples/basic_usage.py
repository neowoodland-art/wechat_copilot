#!/usr/bin/env python3
"""
C++ RPA模块使用示例
"""

import sys
import os

# 添加C++ RPA模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

try:
    import wechat_rpa
    print("✅ 成功导入C++ RPA模块")
except ImportError as e:
    print(f"❌ 导入C++ RPA模块失败: {e}")
    print("请先编译C++ RPA模块")
    sys.exit(1)


def main():
    """主函数"""
    print("=== C++ RPA模块使用示例 ===")
    
    # 创建微信管理器
    manager = wechat_rpa.WeChatManager()
    print("✅ 创建微信管理器")
    
    # 初始化
    if manager.initialize():
        print("✅ 初始化微信管理器成功")
    else:
        print("❌ 初始化微信管理器失败")
        return
    
    # 激活微信
    if manager.activate_wechat():
        print("✅ 激活微信成功")
    else:
        print("❌ 激活微信失败")
        return
    
    # 检查微信是否激活
    if manager.is_wechat_active():
        print("✅ 微信已激活")
    else:
        print("❌ 微信未激活")
        return
    
    # 获取微信窗口信息
    try:
        window = manager.get_wechat_window()
        print(f"✅ 获取微信窗口信息成功: {window.title} ({window.width}x{window.height})")
    except Exception as e:
        print(f"❌ 获取微信窗口信息失败: {e}")
        return
    
    # 截图消息区域
    try:
        screenshot = manager.capture_message_area()
        print(f"✅ 截图消息区域成功: {screenshot.shape}")
        
        # 保存截图
        import cv2
        cv2.imwrite("wechat_message_area.png", screenshot)
        print("✅ 保存截图成功: wechat_message_area.png")
    except Exception as e:
        print(f"❌ 截图消息区域失败: {e}")
    
    # 获取最新消息
    try:
        messages = manager.get_latest_messages(5)
        print(f"✅ 获取最新消息成功，共 {len(messages)} 条")
        
        for i, msg in enumerate(messages):
            print(f"  消息{i+1}: {msg.content[:50]}... (置信度: {msg.confidence:.2f})")
    except Exception as e:
        print(f"❌ 获取最新消息失败: {e}")
    
    # 搜索联系人
    try:
        contact = manager.search_contact("测试")
        print(f"✅ 搜索联系人成功: {contact.name} ({contact.wechat_id})")
    except Exception as e:
        print(f"❌ 搜索联系人失败: {e}")
    
    # 获取联系人列表
    try:
        contacts = manager.get_contacts(5)
        print(f"✅ 获取联系人列表成功，共 {len(contacts)} 条")
        
        for contact in contacts:
            print(f"  联系人: {contact.name} ({contact.wechat_id})")
    except Exception as e:
        print(f"❌ 获取联系人列表失败: {e}")
    
    print("=== 示例结束 ===")


if __name__ == "__main__":
    main()