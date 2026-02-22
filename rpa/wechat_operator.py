"""
微信操作器 - 统一接口层，兼容C++ RPA核心和Python实现
"""

import sys
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 标记C++ RPA是否可用
CPP_RPA_AVAILABLE = False
WeChatOperator = None

# 尝试导入C++ RPA模块
try:
    # 添加C++ RPA模块路径
    cpp_rpa_build_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cpp_rpa', 'build'))
    if os.path.exists(cpp_rpa_build_path) and cpp_rpa_build_path not in sys.path:
        sys.path.insert(0, cpp_rpa_build_path)
        logger.info(f"添加C++ RPA路径到Python路径: {cpp_rpa_build_path}")
    
    import wechat_rpa
    CPP_RPA_AVAILABLE = True
    logger.info("✅ 成功导入C++ RPA模块")
    
    class WeChatOperator:
        """
        微信操作器 - 使用C++ RPA核心
        """
        def __init__(self):
            try:
                self.cpp_manager = wechat_rpa.WeChatManager()
                # 修复初始化逻辑，不依赖返回值
                self.cpp_manager.initialize()
                logger.info("✅ WeChatManager 初始化完成")
            except Exception as e:
                logger.error(f"❌ WeChatManager 初始化失败: {e}")
                raise
        
        def check_wechat_visible(self) -> Dict[str, Any]:
            """检查微信是否可见"""
            try:
                # 根据示例代码，使用is_wechat_active检查微信是否激活
                is_active = self.cpp_manager.is_wechat_active()
                if is_active:
                    return {
                        "success": True,
                        "message": "微信窗口已激活",
                        "is_visible": True
                    }
                else:
                    # 如果未激活，尝试激活微信
                    activated = self.cpp_manager.activate_wechat()
                    if activated:
                        return {
                            "success": True,
                            "message": "微信已激活",
                            "is_visible": True
                        }
                    else:
                        return {
                            "success": False,
                            "message": "无法激活微信",
                            "is_visible": False
                        }
            except Exception as e:
                logger.error(f"检查微信可见性失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "is_visible": False
                }
        
        def get_latest_message(self, min_confidence: float = 0.5) -> Dict[str, Any]:
            """获取最新消息"""
            try:
                # 使用C++ RPA核心获取消息 - 调用正确的C++方法
                # 根据示例代码，应该是 get_latest_messages(count)，而不是置信度
                # 我们先尝试获取固定数量的消息，然后过滤置信度
                if hasattr(self.cpp_manager, 'get_latest_messages'):
                    # 根据示例，get_latest_messages接收的是数量而不是置信度
                    result = self.cpp_manager.get_latest_messages(10)  # 获取最近10条消息
                    if result:
                        # result应该是消息对象列表，每个消息有content和confidence属性
                        if isinstance(result, list):
                            # 过滤置信度大于等于min_confidence的消息
                            filtered_messages = []
                            latest_message = ""
                            
                            for msg_obj in result:
                                # 检查消息对象是否有confidence和content属性
                                if hasattr(msg_obj, 'confidence') and hasattr(msg_obj, 'content'):
                                    if msg_obj.confidence >= min_confidence:
                                        filtered_messages.append({
                                            'content': msg_obj.content,
                                            'confidence': msg_obj.confidence
                                        })
                                        latest_message = msg_obj.content  # 更新最新消息
                            
                            return {
                                "success": True,
                                "all_messages": filtered_messages,
                                "latest_message": latest_message,
                                "message_count": len(filtered_messages)
                            }
                        else:
                            return {
                                "success": True,
                                "all_messages": [],
                                "latest_message": "",
                                "message_count": 0
                            }
                    else:
                        return {
                            "success": True,  # 即使没有消息也是成功的状态
                            "all_messages": [],
                            "latest_message": "",
                            "message_count": 0
                        }
                else:
                    # 如果没有get_latest_messages方法，返回默认值
                    return {
                        "success": True,
                        "all_messages": [],
                        "latest_message": "",
                        "message_count": 0
                    }
            except Exception as e:
                logger.error(f"获取最新消息失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "all_messages": [],
                    "latest_message": "",
                    "message_count": 0
                }
        
        def activate_wechat(self) -> bool:
            """激活微信窗口"""
            try:
                if hasattr(self.cpp_manager, 'activate_wechat'):
                    result = self.cpp_manager.activate_wechat()
                    return bool(result)  # 确保返回布尔值
                return False
            except Exception as e:
                logger.error(f"激活微信失败: {e}")
                return False
        
        def capture_message_area(self) -> Dict[str, Any]:
            """截取消息区域"""
            try:
                # 使用C++ RPA核心截图
                if hasattr(self.cpp_manager, 'capture_message_area'):
                    # 根据示例代码，使用capture_message_area方法
                    screenshot_result = self.cpp_manager.capture_message_area()
                    # capture_message_area返回numpy数组，需要保存为文件
                    if screenshot_result is not None:
                        import cv2
                        import tempfile
                        # 创建临时文件保存截图
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            image_path = tmp.name
                            # 保存截图
                            cv2.imwrite(image_path, screenshot_result)
                        return {
                            "success": True,
                            "image_path": image_path
                        }
                    else:
                        return {
                            "success": False,
                            "error": "截图失败"
                        }
                elif hasattr(self.cpp_manager, 'take_screenshot'):
                    screenshot_result = self.cpp_manager.take_screenshot()
                    if screenshot_result is not None:
                        import cv2
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            image_path = tmp.name
                            cv2.imwrite(image_path, screenshot_result)
                        return {
                            "success": True,
                            "image_path": image_path
                        }
                    else:
                        return {
                            "success": False,
                            "error": "截图失败"
                        }
                else:
                    # 如果没有截图方法，返回错误
                    return {
                        "success": False,
                        "error": "C++ RPA模块不支持截图功能"
                    }
            except Exception as e:
                logger.error(f"截取消息区域失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

    logger.info("✅ WeChatOperator已初始化为C++ RPA实现")

except ImportError as e:
    logger.warning(f"C++ RPA模块不可用: {e}")
    logger.info("将使用模拟实现")
    
    # 定义一个模拟类作为fallback
    class WeChatOperator:
        """
        微信操作器 - 模拟实现（用于fallback）
        """
        def __init__(self):
            logger.info("使用模拟WeChatOperator实现")
            
        def check_wechat_visible(self) -> Dict[str, Any]:
            """检查微信是否可见"""
            return {
                "success": False,
                "message": "模拟实现：微信操作器不可用，请检查C++ RPA模块",
                "is_visible": False
            }
        
        def get_latest_message(self, min_confidence: float = 0.5) -> Dict[str, Any]:
            """获取最新消息"""
            return {
                "success": False,
                "all_messages": [],
                "latest_message": "",
                "message_count": 0,
                "error": "模拟实现：无法获取消息，请检查C++ RPA模块"
            }
        
        def activate_wechat(self) -> bool:
            """激活微信窗口"""
            return False
        
        def capture_message_area(self) -> Dict[str, Any]:
            """截取消息区域"""
            return {
                "success": False,
                "error": "模拟实现：无法截图，请检查C++ RPA模块"
            }
        
        def extract_messages(self, image_path: str, min_confidence: float = 0.5) -> Dict[str, Any]:
            """从截图中提取消息"""
            return {
                "success": False,
                "all_messages": [],
                "latest_message": "",
                "message_count": 0,
                "error": "模拟实现：无法提取消息，请检查C++ RPA模块"
            }

    CPP_RPA_AVAILABLE = False

# 导出变量
__all__ = ['WeChatOperator', 'CPP_RPA_AVAILABLE']

if __name__ == "__main__":
    # 测试代码
    print(f"C++ RPA 可用: {CPP_RPA_AVAILABLE}")
    if CPP_RPA_AVAILABLE:
        print("测试创建WeChatOperator实例...")
        try:
            operator = WeChatOperator()
            print("✅ WeChatOperator创建成功")
        except Exception as e:
            print(f"❌ WeChatOperator创建失败: {e}")
    else:
        print("C++ RPA不可用，将使用模拟实现")
