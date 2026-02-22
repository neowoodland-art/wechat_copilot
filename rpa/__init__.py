"""
微信自动化 RPA 模块
"""
__version__ = "1.0.0"
__author__ = "WeChat Copilot Team"

# 导出主要类和函数
from .wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE

# 确保 rpa 目录被识别为 Python 包
__all__ = [
    "capture",
    "controller",
    "ui_analyzer",
    "wechat_activator",
    "wechat_operator"
]

# 添加编译后的 C++ 模块路径
import sys
import os

cpp_rpa_build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cpp_rpa/build'))
if cpp_rpa_build_path not in sys.path:
    sys.path.insert(0, cpp_rpa_build_path)

try:
    import wechat_rpa
    print("✅ 成功加载 wechat_rpa 模块")
except ImportError as e:
    print(f"❌ 无法加载 wechat_rpa 模块: {e}")