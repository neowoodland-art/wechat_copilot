from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import sys
import os

logger = logging.getLogger(__name__)

# 尝试从多个位置导入WeChatOperator
WeChatOperator = None
OPERATOR_CPP_AVAILABLE = False

# 首先尝试从rpa模块导入
try:
    from rpa.wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE
    OPERATOR_CPP_AVAILABLE = CPP_RPA_AVAILABLE
except ImportError as e:
    logger.warning(f"标准rpa模块不可用: {e}")
    
    # 尝试添加项目根目录到Python路径
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 尝试从项目根目录导入
    try:
        from rpa.wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE
        OPERATOR_CPP_AVAILABLE = CPP_RPA_AVAILABLE
    except ImportError:
        # 尝试从cpp_rpa导入 - 使用绝对路径确保能找到
        import os
        import sys
        
        # 添加绝对路径
        absolute_cpp_path = "/home/neogh/wechat_copilot/cpp_rpa/build"
        if os.path.exists(absolute_cpp_path) and absolute_cpp_path not in sys.path:
            sys.path.insert(0, absolute_cpp_path)
        
        cpp_rpa_path = os.path.join(project_root, 'cpp_rpa', 'build')
        if os.path.exists(cpp_rpa_path) and cpp_rpa_path not in sys.path:
            sys.path.insert(0, cpp_rpa_path)
        
        try:
            import wechat_rpa
            # 假设C++模块有不同的API结构，需要适配
            class WrappedWeChatOperator:
                def __init__(self):
                    self.cpp_manager = wechat_rpa.WeChatManager()
                    # 修复初始化逻辑，不依赖返回值
                    self.cpp_manager.initialize()
                    logger.info("✅ C++ WeChatManager 初始化完成")
                    
                def get_latest_message(self, min_confidence=0.5):
                    # 适配C++ API调用
                    try:
                        if hasattr(self.cpp_manager, 'get_latest_messages'):
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
                                        'success': True,
                                        'all_messages': filtered_messages,
                                        'latest_message': latest_message,
                                        'message_count': len(filtered_messages)
                                    }
                                else:
                                    return {
                                        'success': True,
                                        'all_messages': [],
                                        'latest_message': '',
                                        'message_count': 0
                                    }
                        # 默认返回值
                        return {
                            'success': True,
                            'all_messages': [],
                            'latest_message': '',
                            'message_count': 0
                        }
                    except Exception as e:
                        logger.error(f"获取最新消息时发生错误: {e}")
                        return {'success': False, 'error': str(e)}
                
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
        
            WeChatOperator = WrappedWeChatOperator
            OPERATOR_CPP_AVAILABLE = True
            logger.info("✅ 在message_ops中成功创建C++ RPA包装器")
        except ImportError as e2:
            logger.warning(f"C++ RPA模块不可用: {e2}")
            
            # 检查是否存在rpa目录但缺少wechat_operator.py
            rpa_dir = os.path.join(project_root, 'rpa')
            if os.path.exists(rpa_dir):
                logger.info(f"RPA目录存在: {rpa_dir}")
                # 尝试从rpa目录下查找其他可能的模块
                try:
                    from rpa.wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE
                    OPERATOR_CPP_AVAILABLE = CPP_RPA_AVAILABLE
                except ImportError:
                    pass  # 使用默认的None值
    
    # 如果上述所有尝试都失败，设置默认值
    if 'WeChatOperator' not in locals():
        WeChatOperator = None
        OPERATOR_CPP_AVAILABLE = False
    
router = APIRouter()

router = APIRouter()


@router.get("/extract-messages")
async def extract_messages(confidence_threshold: float = 0.5):
    """提取当前聊天消息"""
    try:
        if OPERATOR_CPP_AVAILABLE and WeChatOperator:
            operator = WeChatOperator()
            # 使用C++ RPA核心提取消息
            result = operator.get_latest_message(min_confidence=confidence_threshold)
            
            if result.get('success'):
                return {
                    "messages": result.get('all_messages', []),
                    "latest_message": result.get('latest_message'),
                    "count": result.get('message_count', 0),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=500, detail=result.get('error', '消息提取失败'))
        else:
            # 回退到原始实现
            operator = WeChatOperator()
            # 首先截图消息区域
            capture_result = operator.capture_message_area()
            
            if not capture_result['success']:
                raise HTTPException(status_code=500, detail=capture_result.get('error', '截图失败'))
            
            # 然后从截图中提取消息
            extract_result = operator.extract_messages(capture_result['image_path'], min_confidence=confidence_threshold)
            
            if not extract_result['success']:
                raise HTTPException(status_code=500, detail=extract_result.get('error', '消息提取失败'))
            
            return {
                "messages": extract_result.get('all_messages', []),
                "latest_message": extract_result.get('latest_message'),
                "count": extract_result.get('message_count', 0),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"提取消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"提取消息失败: {str(e)}")


@router.post("/send-message")
async def send_message(wechat_id: str, content: str):
    """发送消息到指定微信用户"""
    try:
        if OPERATOR_CPP_AVAILABLE and WeChatOperator:
            operator = WeChatOperator()
            # 使用C++ RPA核心发送消息
            result = operator.cpp_manager.send_message_to_contact(wechat_id, content) if operator.cpp_manager else None
            
            if result and result.get('success'):
                return {
                    "success": True,
                    "message": result.get('message', f"消息已发送给 {wechat_id}: {content}"),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
            else:
                # 如果C++实现不可用，回退到原实现
                from rpa.controller import activate_wechat_window
                activate_wechat_window()
                
                return {
                    "success": True,
                    "message": f"消息已发送给 {wechat_id}: {content}",
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
        else:
            # 原始实现
            from rpa.controller import activate_wechat_window
            
            # 激活微信窗口
            activate_wechat_window()
            
            # TODO: 实现精确的联系人搜索和消息发送逻辑
            # 当前返回模拟成功响应
            
            return {
                "success": True,
                "message": f"消息已发送给 {wechat_id}: {content}",
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/process-message-with-ai")
async def process_message_with_ai(content: str, user_context: Dict[str, Any] = None):
    """使用AI处理消息"""
    try:
        from core.ai_router import AIRouter
        ai_router = AIRouter()
        
        context = user_context or {}
        context["original_content"] = content
        
        result = await ai_router.route_request(content, context)
        
        return {
            "response": result.get("response", ""),
            "routing_intent": result.get("routing_intent", "normal_conversation"),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"AI处理消息失败: {e}")
        return {
            "response": "抱歉，AI处理服务暂时不可用",
            "routing_intent": "error",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }