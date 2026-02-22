#!/usr/bin/env python3
# 测试C++ RPA模块的UI元素标注功能

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

def test_annotated_ui():
    print("\n=== 测试UI元素标注功能 ===")
    
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
        
        # 测试标注所有UI元素
        print("\n测试标注所有UI元素...")
        try:
            annotated_image = manager.capture_and_annotate_all_elements()
            print(f"✅ 成功标注并截图所有UI元素，图像尺寸: {annotated_image.shape[1]}x{annotated_image.shape[0]}")
            
            # 保存标注后的图像
            import cv2
            save_path = "/tmp/wechat_annotated_ui.png"
            success = cv2.imwrite(save_path, annotated_image)
            if success:
                print(f"✅ 标注图像已保存到: {save_path}")
            else:
                print(f"❌ 保存标注图像失败")
                
        except Exception as e:
            print(f"❌ 标注所有UI元素失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试标注指定UI元素
        print("\n测试标注指定UI元素...")
        try:
            element_names = ["search_box", "message_input", "send_button"]
            annotated_image = manager.capture_and_annotate_elements(element_names)
            print(f"✅ 成功标注并截图指定UI元素，图像尺寸: {annotated_image.shape[1]}x{annotated_image.shape[0]}")
            
            # 保存标注后的图像
            import cv2
            save_path = "/tmp/wechat_annotated_specific_elements.png"
            success = cv2.imwrite(save_path, annotated_image)
            if success:
                print(f"✅ 特定元素标注图像已保存到: {save_path}")
            else:
                print(f"❌ 保存特定元素标注图像失败")
                
        except Exception as e:
            print(f"❌ 标注指定UI元素失败: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_annotated_ui()