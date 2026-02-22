#!/usr/bin/env python3
"""
模块化微信操作器测试脚本
用于测试新的模块化架构
"""

import sys
import os
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rpa.wechat_operator import WeChatOperator

def test_wechat_operator():
    """测试微信操作器模块"""
    print("🧪 测试微信操作器模块")
    print("=" * 50)
    
    # 创建操作器实例
    operator = WeChatOperator()
    
    # 测试1: 检查微信可见性
    print("\n1. 测试微信可见性检查...")
    visible_result = operator.check_wechat_visible()
    print(f"   结果: {json.dumps(visible_result, ensure_ascii=False, indent=2)}")
    
    if not visible_result['success']:
        print("❌ 微信不可见，测试终止")
        return False
    
    # 测试2: 获取窗口信息
    print("\n2. 测试获取窗口信息...")
    window_result = operator.get_window_info()
    print(f"   结果: {json.dumps(window_result, ensure_ascii=False, indent=2)}")
    
    if not window_result['success']:
        print("❌ 获取窗口信息失败")
        return False
    
    # 测试3: 截图消息区域
    print("\n3. 测试截图消息区域...")
    capture_result = operator.capture_message_area()
    print(f"   结果: {json.dumps(capture_result, ensure_ascii=False, indent=2)}")
    
    if not capture_result['success']:
        print("❌ 截图失败")
        return False
    
    # 测试4: 提取消息
    print("\n4. 测试消息提取...")
    extract_result = operator.extract_messages(capture_result['image_path'])
    print(f"   结果: {json.dumps(extract_result, ensure_ascii=False, indent=2)}")
    
    if not extract_result['success']:
        print("❌ 消息提取失败")
        return False
    
    # 测试5: 完整流程
    print("\n5. 测试完整流程...")
    full_result = operator.get_latest_message()
    print(f"   结果: {json.dumps(full_result, ensure_ascii=False, indent=2)}")
    
    if full_result['success']:
        print("✅ 所有测试通过!")
        return True
    else:
        print("❌ 完整流程测试失败")
        return False

def test_command_line():
    """测试命令行接口"""
    print("\n🔧 测试命令行接口")
    print("=" * 50)
    
    # 模拟命令行参数
    test_cases = [
        ["--action", "info", "--output", "json"],
        ["--action", "latest", "--output", "text"],
        ["--action", "capture", "--confidence", "0.7"]
    ]
    
    for i, args in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: python rpa/wechat_operator.py {' '.join(args)}")
        
        # 在实际环境中，这些命令需要在终端中执行
        print("   请在终端中执行以上命令进行测试")
    
    return True

def main():
    """主测试函数"""
    print("🚀 模块化微信操作器测试")
    
    # 测试核心模块
    module_ok = test_wechat_operator()
    
    # 测试命令行接口
    cli_ok = test_command_line()
    
    print("\n" + "=" * 50)
    if module_ok and cli_ok:
        print("✅ 模块化测试完成!")
        print("\n📋 下一步操作:")
        print("1. 启动后端服务: cd backend && uvicorn main:app --host 0.0.0.0 --port 8000")
        print("2. 测试监控模块: python rpa/monitor.py --mode single")
        print("3. 启动完整监控: python rpa/monitor.py --mode monitor")
    else:
        print("❌ 测试过程中发现问题")
    
    return module_ok and cli_ok

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        exit(1)