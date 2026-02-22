#!/usr/bin/env python3
"""
微信UI交互脚本：识别界面元素、发送消息、读取联系人
"""

import sys
import os
import cv2
import numpy as np
import time

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

class WeChatUIInteract:
    def __init__(self):
        try:
            import wechat_rpa
            self.manager = wechat_rpa.WeChatManager()
            self.manager.initialize()
            print("✅ 微信管理器初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise
    
    def activate_wechat(self):
        """激活微信窗口"""
        print("\n=== 激活微信窗口 ===")
        if self.manager.activate_wechat():
            print("✅ 微信激活成功")
            return True
        else:
            print("❌ 微信激活失败")
            return False
    
    def capture_and_analyze(self):
        """截图并分析界面"""
        print("\n=== 截图并分析界面 ===")
        
        # 截取消息区域
        screenshot = self.manager.capture_message_area()
        print(f"✅ 截图成功，尺寸: {screenshot.shape}")
        
        # 保存截图
        timestamp = int(time.time())
        filename = f"wechat_ui_analysis_{timestamp}.png"
        cv2.imwrite(filename, screenshot)
        print(f"✅ 截图已保存: {filename}")
        
        # 提取消息
        messages = self.manager.extract_messages(screenshot)
        print(f"✅ 提取到 {len(messages)} 条消息")
        
        # 显示消息
        for i, msg in enumerate(messages):
            print(f"\n{i+1}. 发送者: {msg.sender}")
            print(f"   内容: {msg.content}")
            print(f"   置信度: {msg.confidence}")
        
        return screenshot, messages
    
    def get_contacts(self):
        """获取联系人列表"""
        print("\n=== 获取联系人列表 ===")
        
        try:
            contacts = self.manager.get_contacts(20)  # 获取前20个联系人
            print(f"✅ 获取到 {len(contacts)} 个联系人:")
            
            for i, contact in enumerate(contacts):
                print(f"\n{i+1}. 姓名: {contact.name}")
                print(f"   ID: {contact.wechat_id}")
                print(f"   备注: {contact.id}")
            
            return contacts
        except Exception as e:
            print(f"❌ 获取联系人失败: {e}")
            return []
    
    def search_contact(self, keyword):
        """搜索联系人"""
        print(f"\n=== 搜索联系人: {keyword} ===")
        
        try:
            contacts = self.manager.search_contact(keyword)
            print(f"✅ 找到 {len(contacts)} 个匹配的联系人:")
            
            for i, contact in enumerate(contacts):
                print(f"\n{i+1}. 姓名: {contact.name}")
                print(f"   ID: {contact.wechat_id}")
            
            return contacts
        except Exception as e:
            print(f"❌ 搜索联系人失败: {e}")
            return []
    
    def send_message(self, contact_name, message):
        """发送消息"""
        print(f"\n=== 发送消息 ===")
        print(f"联系人: {contact_name}")
        print(f"消息内容: {message}")
        
        try:
            # 创建联系人对象
            contact = wechat_rpa.Contact()
            contact.name = contact_name
            
            # 发送消息
            result = self.manager.send_message(contact, message)
            if result:
                print("✅ 消息发送成功")
                return True
            else:
                print("❌ 消息发送失败")
                return False
        except Exception as e:
            print(f"❌ 发送消息异常: {e}")
            return False
    
    def set_window_size_and_position(self, width, height, x, y):
        """设置微信窗口的大小和位置"""
        print(f"\n=== 设置微信窗口大小和位置 ===")
        try:
            # 获取微信窗口
            window = self.manager.get_wechat_window()
            
            # 设置窗口大小和位置
            self.manager.set_window_geometry(window.id, x, y, width, height)
            print(f"✅ 窗口已设置为: {width}x{height} 位置:({x}, {y})")
            return True
        except Exception as e:
            print(f"❌ 设置窗口失败: {e}")
            return False
    
    def analyze_ui_elements(self):
        """使用 ATSPI 遍历并分析界面元素"""
        print("\n=== 遍历并分析界面元素 ===")
        try:
            import pyatspi
            desktop = pyatspi.Registry.getDesktop(0)
            
            # 遍历所有应用程序
            for app in desktop:
                if app.name.lower() == "wechat":
                    print(f"✅ 找到微信应用: {app.name}")
                    
                    # 遍历微信窗口中的控件
                    for child in app:
                        print(f"控件: {child.name}, 角色: {child.getRoleName()}")
                        
                        # 如果是按钮，记录按钮信息
                        if child.getRoleName().lower() == "push button":
                            print(f"按钮: {child.name}, 状态: {child.getState().getStates()}")
            return True
        except Exception as e:
            print(f"❌ 界面元素分析失败: {e}")
            return False
    
    def interactive_mode(self):
        """交互模式"""
        print("\n=== 微信UI交互模式 ===")
        print("可用命令:")
        print("  1 - 激活微信")
        print("  2 - 截图分析")
        print("  3 - 获取联系人列表")
        print("  4 - 搜索联系人")
        print("  5 - 发送消息")
        print("  6 - 设置窗口大小和位置")
        print("  7 - 遍历并分析界面元素")
        print("  q - 退出")
        
        while True:
            try:
                choice = input("\n请选择操作 (1/2/3/4/5/6/7/q): ").strip()
                
                if choice == '1':
                    self.activate_wechat()
                elif choice == '2':
                    self.capture_and_analyze()
                elif choice == '3':
                    self.get_contacts()
                elif choice == '4':
                    keyword = input("请输入搜索关键词: ")
                    self.search_contact(keyword)
                elif choice == '5':
                    contact_name = input("请输入联系人姓名: ")
                    message = input("请输入消息内容: ")
                    self.send_message(contact_name, message)
                elif choice == '6':
                    width = int(input("请输入窗口宽度: "))
                    height = int(input("请输入窗口高度: "))
                    x = int(input("请输入窗口X坐标: "))
                    y = int(input("请输入窗口Y坐标: "))
                    self.set_window_size_and_position(width, height, x, y)
                elif choice == '7':
                    self.analyze_ui_elements()
                elif choice.lower() == 'q':
                    print("退出交互模式")
                    break
                else:
                    print("无效选择，请重试")
            except KeyboardInterrupt:
                print("\n用户中断，退出")
                break
            except Exception as e:
                print(f"操作出错: {e}")

def main():
    print("=== 微信UI交互脚本 ===")
    
    try:
        # 创建交互对象
        interact = WeChatUIInteract()
        
        # 进入交互模式
        interact.interactive_mode()
        
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()