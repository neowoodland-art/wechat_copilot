#!/usr/bin/env python3
"""
测试C++ RPA模块编译结果
"""

import os
import sys
import subprocess

def test_module_import():
    """测试模块导入"""
    print("=== 测试C++ RPA模块导入 ===")
    
    # 将build目录添加到Python路径
    build_dir = os.path.join(os.path.dirname(__file__), 'build')
    sys.path.insert(0, build_dir)
    
    try:
        import wechat_rpa
        print("✅ 微信RPA模块导入成功")
        print(f"   模块路径: {wechat_rpa.__file__ if hasattr(wechat_rpa, '__file__') else 'N/A'}")
        return True
    except ImportError as e:
        print(f"❌ 微信RPA模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 导入时发生未知错误: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("\n=== 测试基本功能 ===")
    
    try:
        import wechat_rpa
        
        # 创建微信管理器
        print("创建微信管理器...")
        manager = wechat_rpa.WeChatManager()
        print("✅ 微信管理器创建成功")
        
        # 测试初始化
        print("初始化管理器...")
        result = manager.initialize()
        print(f"✅ 初始化结果: {result}")
        
        # 测试错误码枚举
        print("测试错误码枚举...")
        error_code = wechat_rpa.ErrorCode
        print(f"✅ 错误码枚举可用: {error_code.SUCCESS}")
        
        # 测试数据结构
        print("测试数据结构...")
        region = wechat_rpa.Region(10, 20, 100, 50)
        print(f"✅ Region结构可用: {region}")
        
        return True
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        return False

def main():
    print("C++ RPA模块编译测试")
    print("=" * 50)
    
    success = True
    
    # 测试模块导入
    if not test_module_import():
        success = False
    
    # 测试基本功能
    if not test_basic_functionality():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！C++ RPA模块编译成功。")
    else:
        print("❌ 部分测试失败，请检查编译过程。")
    
    return success

if __name__ == "__main__":
    main()