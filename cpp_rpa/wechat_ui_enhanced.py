#!/usr/bin/env python3
"""
增强的微信UI交互脚本：完整界面分析、元素定位、固定窗口
"""

import sys
import os
import cv2
import numpy as np
import time
import subprocess

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

class WeChatUIEnhanced:
    def __init__(self):
        try:
            import wechat_rpa
            self.manager = wechat_rpa.WeChatManager()
            self.manager.initialize()
            print("✅ 微信管理器初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise
    
    def fix_window_size(self):
        """固定微信窗口大小和位置"""
        print("\n=== 固定微信窗口大小和位置 ===")
        
        # 获取窗口信息
        window = self.manager.get_wechat_window()
        print(f"当前窗口: {window.width}x{window.height} 位置:({window.x}, {window.y})")
        
        # 设置固定大小和位置
        target_width = 1000
        target_height = 700
        target_x = 100
        target_y = 100
        
        # 使用wmctrl设置窗口大小和位置
        try:
            # 获取窗口ID（十六进制转十进制）
            window_id_dec = int(window.id, 16) if window.id.startswith('0x') else int(window.id)
            
            # 设置窗口大小和位置
            cmd = f"wmctrl -i -r {window.id} -e 0,{target_x},{target_y},{target_width},{target_height}"
            subprocess.run(cmd, shell=True, check=True)
            
            print(f"✅ 窗口已设置为: {target_width}x{target_height} 位置:({target_x}, {target_y})")
            
            # 等待窗口调整
            time.sleep(1)
            
            return True
        except Exception as e:
            print(f"❌ 设置窗口失败: {e}")
            return False
    
    def capture_full_interface(self):
        """截取完整微信界面"""
        print("\n=== 截取完整微信界面 ===")
        
        # 截取完整窗口
        screenshot = self.manager.capture_full_window()
        print(f"✅ 截图成功，尺寸: {screenshot.shape}")
        
        # 保存截图
        timestamp = int(time.time())
        filename = f"wechat_full_interface_{timestamp}.png"
        cv2.imwrite(filename, screenshot)
        print(f"✅ 完整界面截图已保存: {filename}")
        
        return screenshot
    
    def analyze_ui_elements(self, screenshot):
        """分析UI元素"""
        print("\n=== 分析UI元素 ===")
        
        # 查找按钮
        try:
            buttons = self.manager.find_ui_elements("button")
            print(f"✅ 找到 {len(buttons)} 个按钮:")
            for i, btn in enumerate(buttons):
                print(f"  按钮{i+1}: 位置({btn.x}, {btn.y}) 大小:{btn.width}x{btn.height}")
        except Exception as e:
            print(f"❌ 查找按钮失败: {e}")
        
        # 查找输入框
        try:
            inputs = self.manager.find_ui_elements("input")
            print(f"✅ 找到 {len(inputs)} 个输入框:")
            for i, inp in enumerate(inputs):
                print(f"  输入框{i+1}: 位置({inp.x}, {inp.y}) 大小:{inp.width}x{inp.height}")
        except Exception as e:
            print(f"❌ 查找输入框失败: {e}")
        
        # 查找联系人区域
        try:
            contacts = self.manager.find_ui_elements("contact")
            print(f"✅ 找到 {len(contacts)} 个联系人区域:")
            for i, contact in enumerate(contacts):
                print(f"  联系人区域{i+1}: 位置({contact.x}, {contact.y}) 大小:{contact.width}x{contact.height}")
        except Exception as e:
            print(f"❌ 查找联系人区域失败: {e}")
    
    def show_fixed_elements(self):
        """显示固定元素位置"""
        print("\n=== 固定元素位置 ===")
        
        elements = [
            ("search_box", "搜索框"),
            ("message_input", "消息输入框"),
            ("send_button", "发送按钮")
        ]
        
        for element_name, element_desc in elements:
            try:
                region = self.manager.get_element_region(element_name)
                print(f"{element_desc}: 位置({region.x}, {region.y}) 大小:{region.width}x{region.height}")
            except Exception as e:
                print(f"❌ 获取{element_desc}失败: {e}")
    
    def click_element(self, element_name):
        """点击元素"""
        print(f"\n=== 点击元素: {element_name} ===")
        
        try:
            # 获取元素区域
            region = self.manager.get_element_region(element_name)
            
            # 计算点击位置（中心点）
            click_x = region.x + region.width // 2
            click_y = region.y + region.height // 2
            
            # 使用 C++ RPA 模块点击
            self.manager.click_at(click_x, click_y)
            
            print(f"✅ 已点击位置: ({click_x}, {click_y})")
            return True
        except Exception as e:
            print(f"❌ 点击失败: {e}")
            return False
    
    def send_message_with_ui(self, message):
        """使用UI操作发送消息"""
        print(f"\n=== 发送消息: {message} ===")
        
        # 1. 点击输入框
        if not self.click_element("message_input"):
            print("❌ 点击输入框失败")
            return False
        
        time.sleep(0.5)
        
        # 2. 输入消息
        try:
            # 使用xdotool输入文本
            cmd = f"xdotool type '{message}'"
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ 已输入消息: {message}")
        except Exception as e:
            print(f"❌ 输入消息失败: {e}")
            return False
        
        time.sleep(0.5)
        
        # 3. 点击发送按钮
        if not self.click_element("send_button"):
            print("❌ 点击发送按钮失败")
            return False
        
        print("✅ 消息发送成功")
        return True
    
    def interactive_mode(self):
        """交互模式"""
        print("\n=== 增强微信UI交互模式 ===")
        print("可用命令:")
        print("  1 - 固定窗口大小")
        print("  2 - 截取完整界面")
        print("  3 - 分析UI元素")
        print("  4 - 显示固定元素位置")
        print("  5 - 点击元素")
        print("  6 - UI发送消息")
        print("  q - 退出")
        
        while True:
            try:
                choice = input("\n请选择操作 (1/2/3/4/5/6/q): ").strip()
                
                if choice == '1':
                    self.fix_window_size()
                elif choice == '2':
                    screenshot = self.capture_full_interface()
                    # 保存截图供查看
                    cv2.imshow("Full WeChat Interface", screenshot)
                    print("按任意键关闭窗口...")
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                elif choice == '3':
                    screenshot = self.capture_full_interface()
                    self.analyze_ui_elements(screenshot)
                elif choice == '4':
                    self.show_fixed_elements()
                elif choice == '5':
                    element = input("请输入元素名称 (search_box/message_input/send_button): ")
                    self.click_element(element)
                elif choice == '6':
                    message = input("请输入消息内容: ")
                    self.send_message_with_ui(message)
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
    print("=== 增强微信UI交互脚本 ===")
    
    try:
        # 创建交互对象
        interact = WeChatUIEnhanced()
        
        # 进入交互模式
        interact.interactive_mode()
        
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()