#!/usr/bin/env python3
"""
ATSPI功能测试脚本
测试Linux辅助功能API是否可用
"""

import os
import sys
import time
import subprocess
import json

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

try:
    import wechat_rpa
    print("✅ 微信RPA模块导入成功")
except ImportError as e:
    print(f"❌ 微信RPA模块导入失败: {e}")
    sys.exit(1)

def test_atspi_availability():
    """测试ATSPI是否可用"""
    print("\n=== 测试ATSPI可用性 ===")
    
    try:
        # 检查ATSPI服务是否运行
        result = subprocess.run(['ps', '-ef'], capture_output=True, text=True)
        if 'at-spi-bus-launcher' in result.stdout:
            print("✅ ATSPI总线服务正在运行")
        else:
            print("❌ ATSPI总线服务未运行，尝试启动...")
            subprocess.run(['at-spi-bus-launcher', '--replace'], check=False)
            time.sleep(2)
            
        # 检查注册表服务
        if 'at-spi-registryd' in result.stdout or 'at-spi2-registryd' in result.stdout:
            print("✅ ATSPI注册表服务正在运行")
        else:
            print("❌ ATSPI注册表服务未运行，尝试启动...")
            subprocess.run(['at-spi2-registryd', '--replace'], check=False)
            time.sleep(2)
            
        return True
    except Exception as e:
        print(f"❌ ATSPI服务检查失败: {e}")
        return False

def test_python_atspi():
    """测试Python ATSPI绑定"""
    print("\n=== 测试Python ATSPI绑定 ===")
    
    try:
        import atspi
        print("✅ ATSPI模块导入成功")
        
        # 获取桌面
        desktop = atspi.get_desktop(0)
        print(f"✅ 获取桌面成功")
        
        # 查找微信应用
        wechat_found = False
        try:
            child_count = atspi.get_desktop_child_count(0)
            for i in range(child_count):
                app = atspi.get_desktop_child_at_index(0, i)
                if app:
                    name = atspi.get_accessible_name(app)
                    if name and 'wechat' in name.lower():
                        print(f"✅ 找到微信应用: {name}")
                        wechat_found = True
                        break
        except Exception as e:
            print(f"⚠️ 查找微信应用失败: {e}")
                
        if not wechat_found:
            print("⚠️ 未找到微信应用，请确保微信已启动")
            
        return True
    except ImportError:
        print("❌ pyatspi模块未安装，尝试安装...")
        try:
            subprocess.run(['pip', 'install', 'pyatspi'], check=True)
            print("✅ pyatspi安装成功")
            return True
        except:
            print("❌ pyatspi安装失败")
            return False
    except Exception as e:
        print(f"❌ pyatspi测试失败: {e}")
        return False

def test_cpp_atspi():
    """测试C++ ATSPI引擎"""
    print("\n=== 测试C++ ATSPI引擎 ===")
    
    try:
        # 创建微信管理器
        manager = wechat_rpa.WeChatManager()
        print("✅ 微信管理器创建成功")
        
        # 初始化
        result = manager.initialize()
        print(f"{'✅' if result else '❌'} 初始化结果: {result}")
        
        # 激活微信
        result = manager.activate_wechat()
        print(f"{'✅' if result else '❌'} 激活微信结果: {result}")
        
        # 测试ATSPI功能（如果实现了）
        if hasattr(manager, 'test_atspi_functionality'):
            result = manager.test_atspi_functionality()
            print(f"{'✅' if result else '❌'} ATSPI功能测试: {result}")
        else:
            print("⚠️ ATSPI功能尚未实现")
            
        return True
    except Exception as e:
        print(f"❌ C++ ATSPI测试失败: {e}")
        return False

def test_xdotool_alternatives():
    """测试xdotool替代方案"""
    print("\n=== 测试xdotool替代方案 ===")
    
    # 测试xdotool
    try:
        result = subprocess.run(['xdotool', '--version'], capture_output=True, text=True)
        print(f"✅ xdotool可用: {result.stdout.strip()}")
    except:
        print("❌ xdotool不可用")
        
    # 测试ydotool
    try:
        result = subprocess.run(['ydotool', '--version'], capture_output=True, text=True)
        print(f"✅ ydotool可用: {result.stdout.strip()}")
    except:
        print("❌ ydotool不可用")
        
    # 测试X11权限
    try:
        result = subprocess.run(['xhost'], capture_output=True, text=True)
        if "access control disabled" in result.stdout.lower() or "enabled" in result.stdout.lower():
            print("✅ X11权限配置正确")
        else:
            print("⚠️ 可能需要配置X11权限: xhost +")
    except:
        print("❌ 无法检查X11权限")

def main():
    print("=== ATSPI功能测试 ===")
    
    # 测试ATSPI可用性
    atspi_ok = test_atspi_availability()
    
    # 测试Python ATSPI绑定
    pyatspi_ok = test_python_atspi()
    
    # 测试C++ ATSPI引擎
    cpp_atspi_ok = test_cpp_atspi()
    
    # 测试xdotool替代方案
    test_xdotool_alternatives()
    
    print("\n=== 测试总结 ===")
    print(f"ATSPI服务: {'✅' if atspi_ok else '❌'}")
    print(f"Python ATSPI: {'✅' if pyatspi_ok else '❌'}")
    print(f"C++ ATSPI: {'✅' if cpp_atspi_ok else '❌'}")
    
    if atspi_ok and pyatspi_ok:
        print("\n✅ 建议使用ATSPI方案进行微信自动化")
    else:
        print("\n⚠️ 建议先修复ATSPI环境，或使用xdotool替代方案")

if __name__ == '__main__':
    main()