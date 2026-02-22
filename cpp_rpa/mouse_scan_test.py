#!/usr/bin/env python3
"""
测试鼠标移动扫描界面元素的功能
"""

import sys
import os
import cv2
import numpy as np
import time

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

class MouseScanTest:
    def __init__(self):
        try:
            import wechat_rpa
            self.manager = wechat_rpa.WeChatManager()
            self.manager.initialize()
            print("✅ 微信管理器初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise
    
    def test_hover_detection(self):
        """测试鼠标悬停检测"""
        print("\n=== 测试鼠标悬停检测 ===")
        
        # 1. 截取基础界面
        print("1. 截取基础界面...")
        base_image = self.manager.capture_base_interface()
        print(f"✅ 基础界面截图成功，尺寸: {base_image.shape}")
        
        # 2. 移动鼠标并截取
        print("2. 移动鼠标到指定位置并截取...")
        hover_image = self.manager.capture_hover_interface(200, 200)
        print(f"✅ 悬停界面截图成功，尺寸: {hover_image.shape}")
        
        # 3. 检测变化
        print("3. 检测界面变化...")
        try:
            # 这里需要在C++中添加方法
            elements = self.manager.scan_interface_by_mouse()
            print(f"✅ 检测到 {len(elements)} 个界面元素:")
            
            for i, elem in enumerate(elements):
                print(f"  元素{i+1}: 位置({elem.x}, {elem.y}) 大小:{elem.width}x{elem.height}")
        except Exception as e:
            print(f"❌ 检测失败: {e}")
        
        # 4. 保存对比图像
        timestamp = int(time.time())
        cv2.imwrite(f"base_interface_{timestamp}.png", base_image)
        cv2.imwrite(f"hover_interface_{timestamp}.png", hover_image)
        print(f"✅ 对比图像已保存")
        
        # 5. 显示对比
        cv2.imshow("Base Interface", base_image)
        cv2.imshow("Hover Interface", hover_image)
        print("\n按任意键关闭窗口...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def full_scan(self):
        """完整扫描界面"""
        print("\n=== 完整扫描界面 ===")
        print("这将需要一些时间，请耐心等待...")
        print("按ESC键或输入'q'可随时停止扫描")
        
        try:
            # 执行完整扫描（支持ESC退出）
            elements = self.manager.scan_interface_by_mouse_with_timeout(60)  # 60秒超时
            print(f"✅ 扫描完成，找到 {len(elements)} 个界面元素:")
            
            for i, elem in enumerate(elements):
                print(f"  元素{i+1}: 位置({elem.x}, {elem.y}) 大小:{elem.width}x{elem.height}")
                
                # 保存元素信息
                with open("interface_elements.json", "w") as f:
                    import json
                    json.dump([{
                        "x": elem.x,
                        "y": elem.y,
                        "width": elem.width,
                        "height": elem.height
                    } for elem in elements], f, indent=2)
                print("✅ 元素信息已保存到 interface_elements.json")
        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            import traceback
            traceback.print_exc()
    
    def simple_scan(self):
        """简单扫描界面（不支持ESC停止）"""
        print("\n=== 简单扫描界面 ===")
        print("这将需要一些时间，请耐心等待...")
        
        try:
            # 执行简单扫描
            elements = self.manager.scan_interface_by_mouse_simple()
            print(f"✅ 扫描完成，找到 {len(elements)} 个界面元素:")
            
            for i, elem in enumerate(elements):
                print(f"  元素{i+1}: 位置({elem.x}, {elem.y}) 大小:{elem.width}x{elem.height}")
                
                # 保存元素信息
                with open("interface_elements.json", "w") as f:
                    import json
                    json.dump([{
                        "x": elem.x,
                        "y": elem.y,
                        "width": elem.width,
                        "height": elem.height
                    } for elem in elements], f, indent=2)
                print("✅ 元素信息已保存到 interface_elements.json")
        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            import traceback
            traceback.print_exc()
    
    def interactive_mode(self):
        """交互模式"""
        print("\n=== 鼠标扫描交互模式 ===")
        print("可用命令:")
        print("  1 - 测试鼠标悬停检测")
        print("  2 - 完整扫描界面（支持ESC停止）")
        print("  3 - 简单扫描界面（不支持ESC停止）")
        print("  q - 退出")
        
        while True:
            try:
                choice = input("\n请选择操作 (1/2/3/q): ").strip()
                
                if choice == '1':
                    self.test_hover_detection()
                elif choice == '2':
                    self.full_scan()
                elif choice == '3':
                    self.simple_scan()
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
    print("=== 鼠标扫描测试 ===")
    
    try:
        # 创建测试对象
        test = MouseScanTest()
        
        # 进入交互模式
        test.interactive_mode()
        
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()