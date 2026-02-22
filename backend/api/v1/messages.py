from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# 安全导入微信操作器
try:
    from rpa.wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE
    OPERATOR_CPP_AVAILABLE = CPP_RPA_AVAILABLE
except ImportError as e:
    logger.warning(f"WeChat操作器不可用: {e}")
    OPERATOR_CPP_AVAILABLE = False
    # 定义一个模拟类
    class MockWeChatOperator:
        def extract_messages(self, confidence_threshold=0.5):
            return []
        def send_message(self, wechat_id, content):
            return {"success": False, "message": "WeChat操作器不可用"}
    WeChatOperator = MockWeChatOperator


@router.get("/extract-messages")
async def extract_messages(confidence_threshold: float = 0.5):
    """提取当前聊天消息"""
    if not OPERATOR_CPP_AVAILABLE or not WeChatOperator:
        raise HTTPException(status_code=500, detail="WeChat操作器不可用")
    
    try:
        operator = WeChatOperator()
        # 使用C++ RPA核心提取消息
        result = operator.get_latest_message(min_confidence=confidence_threshold)
        
        if result.get("success"):
            messages = result.get('all_messages', [])
            return {
                "messages": messages,
                "count": len(messages),
                "latest_message": result.get('latest_message'),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '消息提取失败'))
    except Exception as e:
        logger.error(f"提取消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"提取消息失败: {str(e)}")


@router.post("/send-message")
async def send_message(wechat_id: str, content: str):
    """发送消息到指定微信用户"""
    if not OPERATOR_CPP_AVAILABLE or not WeChatOperator:
        raise HTTPException(status_code=500, detail="WeChat操作器不可用")
    
    try:
        operator = WeChatOperator()
        # 使用C++ RPA核心发送消息
        if operator.cpp_manager:
            result = operator.cpp_manager.send_message_to_contact(wechat_id, content)
        else:
            result = operator.send_message(wechat_id, content)
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/process-message-with-ai")
async def process_message_with_ai(content: str, user_context: Dict[str, Any] = None):
    """使用AI处理消息"""
    try:
        # 尝试使用AI路由器，如果失败则降级到基础AI客户端
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
        except ImportError:
            # 如果AI路由器不可用，使用基础AI客户端
            from core.ai_client import ai_client
            
            prompt = f"请回复以下消息：{content}"
            result = await ai_client.call(prompt)
            
            return {
                "response": result.get("response", "抱歉，暂时无法处理您的消息"),
                "routing_intent": "normal_conversation",
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"AI处理消息失败: {e}")
        return {
            "response": "抱歉，AI处理服务暂时不可用",
            "routing_intent": "error",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }