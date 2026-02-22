#!/usr/bin/env python3
"""
WeChat Copilot C++ RPA 微信界面元素分析器
"""

import os
import sys
import time
from datetime import datetime

# 添加构建目录到Python路径
sys.path.insert(0, '/home/neogh/wechat_copilot/cpp_rpa/build')

try:
    import wechat_rpa
    print("[SUCCESS] 成功导入 wechat_rpa 模块")
except ImportError as e:
    print(f"[ERROR] 导入 wechat_rpa 模块失败: {e}")
    sys.exit(1)


def analyze_wechat_interface():
    """分析微信界面元素"""
    print("\n" + "="*60)
    print("微信界面元素分析器")
    print("="*60)
    
    try:
        # 创建WeChatManager实例
        wechat_manager = wechat_rpa.WeChatManager()
        print("[INFO] WeChatManager 创建成功")
        
        # 初始化微信管理器
        success = wechat_manager.initialize()
        print(f"[INFO] WeChatManager 初始化: {'成功' if success else '失败'}")
        
        if not success:
            print("[ERROR] 无法初始化WeChatManager，退出分析")
            return False
        
        # 尝试查找微信窗口
        print("\n正在查找微信窗口...")
        try:
            window_info = wechat_manager.get_wechat_window()
            print(f"[SUCCESS] 找到微信窗口:")
            print(f"  - 标题: {window_info.title}")
            print(f"  - ID: {window_info.id}")
            print(f"  - 位置: ({window_info.x}, {window_info.y})")
            print(f"  - 尺寸: {window_info.width} x {window_info.height}")
            print(f"  - 激活状态: {'是' if window_info.is_active else '否'}")
        except Exception as e:
            print(f"[WARNING] 无法获取微信窗口: {e}")
            print("请确保微信已启动并至少有一个窗口可见")
            return False
        
        # 检查微信是否激活
        is_active = wechat_manager.is_wechat_active()
        print(f"[INFO] 微信激活状态: {'是' if is_active else '否'}")
        
        if not is_active:
            print("[INFO] 尝试激活微信窗口...")
            try:
                activation_result = wechat_manager.activate_wechat()
                print(f"[INFO] 微信激活结果: {'成功' if activation_result else '失败'}")
            except Exception as e:
                print(f"[WARNING] 激活微信时出错: {e}")
        
        # 使用AT-SPI引擎分析界面元素
        print("\n正在使用AT-SPI引擎分析界面元素...")
        atspi_engine = wechat_rpa.ATSPIEngine()
        atspi_success = atspi_engine.initialize()
        
        if atspi_success:
            print("[SUCCESS] AT-SPI引擎初始化成功")
            
            # 尝试获取微信应用程序
            print("正在获取微信应用程序...")
            try:
                wechat_app = atspi_engine.get_wechat_application()
                if wechat_app:
                    print("[SUCCESS] 成功获取微信应用程序对象")
                    
                    # 获取控件区域信息
                    try:
                        region = atspi_engine.get_control_region(wechat_app)
                        print(f"[INFO] 微信窗口区域: ({region.x}, {region.y}, {region.width}x{region.height})")
                    except Exception as e:
                        print(f"[INFO] 获取控件区域时出错: {e}")
                        print("[INFO] 这可能是由于权限或AT-SPI实现限制")
                    
                    # 尝试获取微信文本内容
                    try:
                        text_content = atspi_engine.get_control_text(wechat_app)
                        if text_content and text_content.strip():
                            print(f"[INFO] 微信文本内容: {text_content[:100]}...")  # 显示前100个字符
                        else:
                            print("[INFO] 未获取到微信文本内容（这很正常，因为微信是自绘界面）")
                    except Exception as e:
                        print(f"[INFO] 获取文本内容时出错: {e}")
                        
                else:
                    print("[INFO] 未找到微信应用程序（可能微信未运行或AT-SPI无法访问）")
            except Exception as e:
                print(f"[INFO] 获取微信应用程序时出错: {e}")
        else:
            print("[WARNING] AT-SPI引擎初始化失败，可能无法分析界面元素")
        
        # 尝试获取UI元素（如果支持）
        print("\n正在尝试检测UI元素...")
        try:
            ui_elements = wechat_manager.find_ui_elements("button")  # 尝试查找按钮
            if ui_elements:
                print(f"[INFO] 找到 {len(ui_elements)} 个按钮元素")
                for i, elem in enumerate(ui_elements[:5]):  # 只显示前5个
                    print(f"  - 按钮 {i+1}: ({elem.x}, {elem.y}, {elem.width}x{elem.height})")
                if len(ui_elements) > 5:
                    print(f"  ... 还有 {len(ui_elements)-5} 个按钮元素")
            else:
                print("[INFO] 未找到按钮元素（这在微信中很常见，因为它使用自绘界面）")
        except Exception as e:
            print(f"[INFO] 检测按钮元素时出错: {e}")
        
        # 尝试获取特定元素区域
        print("\n正在尝试获取聊天窗口区域...")
        try:
            chat_region = wechat_manager.get_element_region("聊天")
            print(f"[INFO] 聊天区域: ({chat_region.x}, {chat_region.y}, {chat_region.width}x{chat_region.height})")
        except Exception as e:
            print(f"[INFO] 获取聊天区域时出错（这很正常）: {e}")
        
        # 尝试截取界面
        print("\n正在尝试截取微信界面...")
        try:
            base_interface = wechat_manager.capture_base_interface()
            if base_interface is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_filename = f"/tmp/wechat_screenshot_{timestamp}.png"
                print(f"[INFO] 已捕获基础界面，数据类型: {type(base_interface)}")
                print(f"[INFO] 截图已准备就绪 (保存到: {screenshot_filename} - 实际保存需额外处理)")
            else:
                print("[INFO] 未能捕获界面（可能由于权限或窗口状态）")
        except Exception as e:
            print(f"[INFO] 截取界面时出错: {e}")
        
        # 尝试获取最近消息
        print("\n正在尝试获取最近消息...")
        try:
            messages = wechat_manager.get_latest_messages(5)  # 获取最近5条消息
            if messages:
                print(f"[INFO] 找到 {len(messages)} 条消息:")
                for i, msg in enumerate(messages[:5]):
                    print(f"  - 消息 {i+1}: {msg.content[:50]}...")  # 显示前50个字符
            else:
                print("[INFO] 当前无消息或无法读取消息（可能需要更多权限）")
        except Exception as e:
            print(f"[INFO] 获取消息时出错: {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 分析微信界面时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print(f"开始微信界面分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = analyze_wechat_interface()
    
    print("\n" + "="*60)
    if success:
        print("微信界面分析完成！")
        print("我们成功使用C++ RPA引擎分析了您的微信界面。")
    else:
        print("微信界面分析部分完成。")
        print("某些功能可能因系统权限或微信的安全机制而受限。")
    print("="*60)
    
    return success


if __name__ == "__main__":
    main()
