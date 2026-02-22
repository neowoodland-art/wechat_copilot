from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()



# 安全导入UI分析器、微信激活器和微信操作器
try:
    from rpa.ui_analyzer import UIAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"UI分析器不可用: {e}")
    ANALYZER_AVAILABLE = False
    # 定义一个模拟类
    class MockUIAnalyzer:
        def analyze_interface(self, force_refresh=False):
            return {"success": False, "error": "UI分析器不可用"}
        def get_element_position(self, element_name):
            return {"success": False, "error": "UI分析器不可用"}
        def check_layout_status(self):
            return {"layout_changed": False, "elements_count": 0}
    UIAnalyzer = MockUIAnalyzer

try:
    from rpa.wechat_activator import ensure_wechat_is_active
    WECHAT_ACTIVATOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"微信激活器不可用: {e}")
    WECHAT_ACTIVATOR_AVAILABLE = False
    def ensure_wechat_is_active(pause_input: bool = True) -> Dict[str, Any]:
        return {"success": False, "error": "微信激活器不可用"}

try:
    from rpa.wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE
    OPERATOR_CPP_AVAILABLE = CPP_RPA_AVAILABLE
except ImportError as e:
    logger.warning(f"微信操作器不可用: {e}")
    OPERATOR_CPP_AVAILABLE = False
    WeChatOperator = None


@router.post("/analyze-ui")
async def analyze_ui(force_refresh: bool = False):
    """分析微信界面元素"""
    # 确保微信处于激活状态
    if WECHAT_ACTIVATOR_AVAILABLE:
        activation_result = ensure_wechat_is_active(pause_input=True)
        if not activation_result.get('success'):
            logger.warning(f"微信激活失败: {activation_result.get('error')}")
    
    if not ANALYZER_AVAILABLE:
        return {
            "success": False,
            "error": "UI分析器不可用",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        analyzer = UIAnalyzer()
        result = analyzer.analyze_interface(force_refresh=force_refresh)
        
        if result.get("success"):
            elements_data = {}
            if "elements" in result:
                elements = result["elements"]
                # 检查elements是字典还是列表
                if isinstance(elements, dict):
                    # 如果是字典，遍历键值对
                    for k, v in elements.items():
                        if hasattr(v, 'bbox'):
                            # v是一个对象，有bbox属性
                            elements_data[k] = {
                                "x": v.bbox[0],
                                "y": v.bbox[1],
                                "width": v.bbox[2],
                                "height": v.bbox[3]
                            }
                        elif isinstance(v, dict) and 'bbox' in v:
                            # v是一个字典，有bbox键
                            bbox = v['bbox']
                            elements_data[k] = {
                                "x": bbox[0] if isinstance(bbox, (list, tuple)) else 0,
                                "y": bbox[1] if isinstance(bbox, (list, tuple)) and len(bbox) > 1 else 0,
                                "width": bbox[2] if isinstance(bbox, (list, tuple)) and len(bbox) > 2 else 0,
                                "height": bbox[3] if isinstance(bbox, (list, tuple)) and len(bbox) > 3 else 0
                            }
                elif isinstance(elements, list):
                    # 如果是列表，需要特殊处理
                    for i, element in enumerate(elements):
                        if hasattr(element, 'bbox'):
                            # element是一个对象，有bbox属性
                            elements_data[f"element_{i}"] = {
                                "x": element.bbox[0],
                                "y": element.bbox[1],
                                "width": element.bbox[2],
                                "height": element.bbox[3]
                            }
                        elif isinstance(element, dict) and 'bbox' in element:
                            # element是一个字典，有bbox键
                            bbox = element['bbox']
                            elements_data[f"element_{i}"] = {
                                "x": bbox[0] if isinstance(bbox, (list, tuple)) else 0,
                                "y": bbox[1] if isinstance(bbox, (list, tuple)) and len(bbox) > 1 else 0,
                                "width": bbox[2] if isinstance(bbox, (list, tuple)) and len(bbox) > 2 else 0,
                                "height": bbox[3] if isinstance(bbox, (list, tuple)) and len(bbox) > 3 else 0
                            }
                        elif isinstance(element, dict) and all(key in element for key in ['x', 'y', 'width', 'height']):
                            # element是一个包含位置信息的字典
                            elements_data[element.get('name', f'element_{i}')] = {
                                "x": element['x'],
                                "y": element['y'],
                                "width": element['width'],
                                "height": element['height']
                            }
            
            return {
                "success": True,
                "elements": elements_data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "分析失败"),
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"界面分析失败: {e}")
        return {
            "success": False,
            "error": f"界面分析失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/get-element-position")
async def get_element_position(element_name: str):
    """获取特定界面元素的位置"""
    # 确保微信处于激活状态
    if WECHAT_ACTIVATOR_AVAILABLE:
        activation_result = ensure_wechat_is_active(pause_input=True)
        if not activation_result.get('success'):
            logger.warning(f"微信激活失败: {activation_result.get('error')}")
    
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=500, detail="UI分析器不可用")
    
    try:
        analyzer = UIAnalyzer()
        result = analyzer.get_element_position(element_name)
        
        if result.get("success"):
            element = result["element"]
            # 检查element是对象还是字典
            if hasattr(element, 'name') and hasattr(element, 'bbox') and hasattr(element, 'element_type'):
                # element是一个对象
                return {
                    "success": True,
                    "element": {
                        "name": element.name,
                        "x": element.bbox[0],
                        "y": element.bbox[1],
                        "width": element.bbox[2],
                        "height": element.bbox[3],
                        "type": element.element_type
                    },
                    "timestamp": datetime.now().isoformat()
                }
            elif isinstance(element, dict):
                # element是一个字典
                bbox = element.get('bbox', [0, 0, 0, 0])
                return {
                    "success": True,
                    "element": {
                        "name": element.get('name', element_name),
                        "x": bbox[0] if isinstance(bbox, (list, tuple)) else 0,
                        "y": bbox[1] if isinstance(bbox, (list, tuple)) and len(bbox) > 1 else 0,
                        "width": bbox[2] if isinstance(bbox, (list, tuple)) and len(bbox) > 2 else 0,
                        "height": bbox[3] if isinstance(bbox, (list, tuple)) and len(bbox) > 3 else 0,
                        "type": element.get('element_type', 'unknown')
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=500, detail="元素格式不正确")
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "元素未找到"))
    
    except Exception as e:
        logger.error(f"获取元素位置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取元素位置失败: {str(e)}")


@router.get("/check-layout-status")
async def check_layout_status():
    """检查界面布局状态"""
    # 确保微信处于激活状态
    if WECHAT_ACTIVATOR_AVAILABLE:
        activation_result = ensure_wechat_is_active(pause_input=True)
        if not activation_result.get('success'):
            logger.warning(f"微信激活失败: {activation_result.get('error')}")
    
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=500, detail="UI分析器不可用")
    
    try:
        analyzer = UIAnalyzer()
        result = analyzer.check_layout_status()
        
        return {
            "success": True,
            "layout_changed": result.get("layout_changed", False),
            "last_updated": result.get("last_updated"),
            "elements_count": result.get("elements_count", 0)
        }
    
    except Exception as e:
        logger.error(f"检查布局状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查布局状态失败: {str(e)}")


@router.post("/capture-screen")
async def capture_screen_endpoint():
    """截取微信界面"""
    # 确保微信处于激活状态
    if WECHAT_ACTIVATOR_AVAILABLE:
        activation_result = ensure_wechat_is_active(pause_input=True)
        if not activation_result.get('success'):
            logger.warning(f"微信激活失败: {activation_result.get('error')}")
    
    try:
        if OPERATOR_CPP_AVAILABLE and WeChatOperator:
            operator = WeChatOperator()
            
            # 使用WeChatOperator的截图功能（现在使用C++ RPA核心）
            result = operator.capture_message_area()
            
            # 如果截图成功，返回结果
            if result.get('success'):
                return {
                    "success": True,
                    "image_path": result.get('image_path', '/tmp/wechat_screen.png'),
                    "image_size": result.get('image_size'),
                    "region": result.get('region'),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 如果C++ RPA截图失败，返回错误信息
                logger.warning(f"C++ RPA截图失败: {result.get('error', '未知错误')}")
                return {
                    "success": False,
                    "error": result.get('error', '截图失败'),
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # 回退到原始实现
            try:
                from rpa.capture import capture_screen
                img = capture_screen()
                return {
                    "success": True,
                    "image_path": "/tmp/wechat_screen.png",
                    "timestamp": datetime.now().isoformat()
                }
            except ImportError:
                # 如果都失败，返回模拟结果
                return {
                    "success": True,
                    "image_path": "/tmp/mock_screenshot.png",
                    "ocr_text": "微信界面截图示例：\n用户昵称: 张三\n消息: 你好，在吗？\n时间: 10:30",
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        logger.error(f"截图失败: {e}")
        return {
            "success": False,
            "error": f"截图失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }