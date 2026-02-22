"""
UI分析器 - 分析微信界面元素
"""

import logging
import json
import os
from typing import Dict, Any, Optional

from .wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE

logger = logging.getLogger(__name__)

class UIAnalyzer:
    """
    UI分析器类
    """
    
    def __init__(self):
        self.operator = None
        if CPP_RPA_AVAILABLE:
            try:
                self.operator = WeChatOperator()
            except Exception as e:
                logger.error(f"初始化WeChatOperator失败: {e}")
                self.operator = None
        
        # 界面元素缓存
        self.element_cache = {}
        self.cache_timestamp = 0
        
        # 加载预定义的界面元素位置
        self.load_predefined_elements()
    
    def load_predefined_elements(self):
        """
        加载预定义的界面元素位置
        """
        try:
            elements_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cpp_rpa', 'interface_elements.json')
            if os.path.exists(elements_file):
                with open(elements_file, 'r', encoding='utf-8') as f:
                    self.predefined_elements = json.load(f)
            else:
                # 默认界面元素定义
                self.predefined_elements = {
                    "chat_area": {"x": 300, "y": 100, "width": 500, "height": 400},
                    "input_box": {"x": 300, "y": 520, "width": 500, "height": 100},
                    "send_button": {"x": 780, "y": 530, "width": 60, "height": 30},
                    "contact_list": {"x": 0, "y": 100, "width": 280, "height": 500}
                }
        except Exception as e:
            logger.warning(f"加载预定义元素失败: {e}")
            self.predefined_elements = {}
    
    def analyze_interface(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        分析微信界面元素
        """
        try:
            if not CPP_RPA_AVAILABLE or not self.operator:
                return {
                    "success": False,
                    "error": "WeChatOperator不可用",
                    "elements": {}
                }
            
            # 检查缓存
            import time
            current_time = time.time()
            if not force_refresh and self.element_cache and (current_time - self.cache_timestamp < 30):  # 30秒缓存
                return {
                    "success": True,
                    "elements": self.element_cache,
                    "cached": True
                }
            
            # 尝试使用C++ RPA分析界面
            if hasattr(self.operator.cpp_manager, 'analyze_interface'):
                try:
                    result = self.operator.cpp_manager.analyze_interface()
                    if result:
                        # 确保result格式正确，转换为统一的对象格式
                        formatted_result = {}
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if isinstance(value, dict):
                                    # 如果value是包含坐标信息的字典，将其转换为统一格式
                                    formatted_result[key] = {
                                        "name": key,
                                        "bbox": [
                                            value.get("x", 0),
                                            value.get("y", 0),
                                            value.get("width", 0),
                                            value.get("height", 0)
                                        ],
                                        "element_type": value.get("type", "unknown")
                                    }
                                else:
                                    # 其他情况，创建默认对象
                                    formatted_result[key] = {
                                        "name": key,
                                        "bbox": [0, 0, 0, 0],
                                        "element_type": "unknown"
                                    }
                        elif isinstance(result, list):
                            # 如果result是列表，将其转换为字典
                            for i, item in enumerate(result):
                                key = f"element_{i}"
                                if isinstance(item, dict):
                                    formatted_result[key] = {
                                        "name": key,
                                        "bbox": [
                                            item.get("x", 0),
                                            item.get("y", 0),
                                            item.get("width", 0),
                                            item.get("height", 0)
                                        ],
                                        "element_type": item.get("type", "unknown")
                                    }
                                else:
                                    formatted_result[key] = {
                                        "name": key,
                                        "bbox": [0, 0, 0, 0],
                                        "element_type": "unknown"
                                    }
                        else:
                            # 其他类型，使用预定义元素
                            formatted_result = self.predefined_elements.copy()
                        
                        self.element_cache = formatted_result
                        self.cache_timestamp = current_time
                        return {
                            "success": True,
                            "elements": formatted_result,
                            "cached": False
                        }
                except Exception as e:
                    logger.warning(f"C++界面分析失败: {e}")
            
            # 如果C++方法不可用，使用预定义元素
            elements = {}
            for key, value in self.predefined_elements.items():
                elements[key] = {
                    "name": key,
                    "bbox": [
                        value.get("x", 0),
                        value.get("y", 0),
                        value.get("width", 0),
                        value.get("height", 0)
                    ],
                    "element_type": value.get("type", "unknown")
                }
            
            # 尝试从当前窗口获取实时信息
            visibility_result = self.operator.check_wechat_visible()
            if visibility_result.get("success"):
                elements["window_status"] = {
                    "name": "window_status",
                    "bbox": [0, 0, 0, 0],
                    "element_type": "status"
                }
            
            self.element_cache = elements
            self.cache_timestamp = current_time
            
            return {
                "success": True,
                "elements": elements,
                "cached": False
            }
            
        except Exception as e:
            logger.error(f"分析界面失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "elements": {}
            }
    
    def get_element_position(self, element_name: str) -> Dict[str, Any]:
        """
        获取特定元素的位置
        """
        try:
            interface_result = self.analyze_interface()
            if interface_result.get("success"):
                elements = interface_result.get("elements", {})
                position = elements.get(element_name)
                
                if position:
                    # 返回统一格式的元素对象
                    if isinstance(position, dict):
                        # 如果position已经是包含坐标信息的字典
                        element_obj = {
                            "name": element_name,
                            "bbox": [
                                position.get("x", 0),
                                position.get("y", 0),
                                position.get("width", 0),
                                position.get("height", 0)
                            ],
                            "element_type": position.get("type", "unknown")
                        }
                    else:
                        # 其他情况，创建默认对象
                        element_obj = {
                            "name": element_name,
                            "bbox": [0, 0, 0, 0],
                            "element_type": "unknown"
                        }
                    
                    return {
                        "success": True,
                        "element": element_obj
                    }
                else:
                    # 尝试在预定义元素中查找
                    predefined_pos = self.predefined_elements.get(element_name)
                    if predefined_pos:
                        element_obj = {
                            "name": element_name,
                            "bbox": [
                                predefined_pos.get("x", 0),
                                predefined_pos.get("y", 0),
                                predefined_pos.get("width", 0),
                                predefined_pos.get("height", 0)
                            ],
                            "element_type": predefined_pos.get("type", "unknown")
                        }
                        return {
                            "success": True,
                            "element": element_obj,
                            "source": "predefined"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"未找到元素: {element_name}",
                            "element_name": element_name
                        }
            else:
                return {
                    "success": False,
                    "error": interface_result.get("error", "无法分析界面"),
                    "element_name": element_name
                }
                
        except Exception as e:
            logger.error(f"获取元素位置失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "element_name": element_name
            }
    
    def check_layout_status(self) -> Dict[str, Any]:
        """
        检查布局状态
        """
        try:
            interface_result = self.analyze_interface(force_refresh=True)
            if interface_result.get("success"):
                elements = interface_result.get("elements", {})
                elements_count = len(elements)
                
                # 检查是否发生了显著变化
                layout_changed = False  # 简单起见，暂时假定布局未变
                
                return {
                    "layout_changed": layout_changed,
                    "elements_count": elements_count,
                    "elements": list(elements.keys())
                }
            else:
                return {
                    "layout_changed": False,
                    "elements_count": 0,
                    "elements": [],
                    "error": interface_result.get("error")
                }
                
        except Exception as e:
            logger.error(f"检查布局状态失败: {e}")
            return {
                "layout_changed": False,
                "elements_count": 0,
                "elements": [],
                "error": str(e)
            }

# 导出便捷函数
def analyze_wechat_ui(force_refresh: bool = False) -> Dict[str, Any]:
    """
    便捷函数：分析微信UI
    """
    analyzer = UIAnalyzer()
    return analyzer.analyze_interface(force_refresh)

def get_element_pos(element_name: str) -> Dict[str, Any]:
    """
    便捷函数：获取元素位置
    """
    analyzer = UIAnalyzer()
    return analyzer.get_element_position(element_name)

def check_layout() -> Dict[str, Any]:
    """
    便捷函数：检查布局状态
    """
    analyzer = UIAnalyzer()
    return analyzer.check_layout_status()


__all__ = [
    'UIAnalyzer',
    'analyze_wechat_ui',
    'get_element_pos',
    'check_layout'
]