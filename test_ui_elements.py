#!/usr/bin/env python3
# 测试C++ RPA模块的UI元素分析功能

import sys
import os
import json

# 添加模块路径
module_paths = [
    os.path.join(os.path.dirname(__file__), 'cpp_rpa/build'),
    '/home/neogh/wechat_copilot/cpp_rpa/build',
]

for path in module_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

try:
    import wechat_rpa
    from wechat_rpa import WeChatManager
    print("✅ 成功导入 wechat_rpa 模块")
except ImportError as e:
    print(f"❌ 无法导入 wechat_rpa 模块: {e}")
    print("请先编译C++ RPA模块")
    sys.exit(1)

def test_ui_elements():
    print("\n=== 测试UI元素分析功能 ===")
    
    try:
        # 创建WeChatManager实例
        manager = WeChatManager()
        print("✅ WeChatManager创建成功")
        
        # 初始化
        if manager.initialize():
            print("✅ WeChatManager初始化成功")
        else:
            print("❌ WeChatManager初始化失败")
            return
        
        # 激活微信
        print("正在激活微信...")
        if manager.activate_wechat():
            print("✅ 微信激活成功")
        else:
            print("⚠️ 微信激活失败，仍在继续测试其他功能")
        
        # 测试分析UI元素
        print("\n测试分析UI元素...")
        try:
            elements = manager.analyze_ui_elements()
            print(f"✅ 成功分析到 {len(elements)} 个UI元素")
            
            # 显示前几个元素
            for name, region in list(elements.items())[:5]:
                print(f"  - {name}: ({region.x}, {region.y}, {region.width}x{region.height})")
                
        except Exception as e:
            print(f"❌ 分析UI元素失败: {e}")
        
        # 测试查找所有按钮
        print("\n测试查找所有按钮...")
        try:
            buttons = manager.find_all_buttons()
            print(f"✅ 成功找到 {len(buttons)} 个按钮")
            
            # 显示前几个按钮
            for i, region in enumerate(buttons[:5]):
                print(f"  - Button {i}: ({region.x}, {region.y}, {region.width}x{region.height})")
                
        except Exception as e:
            print(f"❌ 查找按钮失败: {e}")
        
        # 测试ATSPI相关功能
        print("\n测试ATSPI功能...")
        try:
            # 测试点击控件
            print("  尝试点击搜索框...")
            result = manager.click_control_by_atspi("搜索")
            print(f"  点击结果: {result}")
            
            # 测试输入文本
            print("  尝试输入文本到搜索框...")
            result = manager.input_text_by_atspi("搜索", "测试文本")
            print(f"  输入结果: {result}")
            
        except Exception as e:
            print(f"❌ ATSPI功能测试失败: {e}")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_ui_elements()