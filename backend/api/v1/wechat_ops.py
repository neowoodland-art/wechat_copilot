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
    logger.warning(f"微信操作器不可用: {e}")
    OPERATOR_CPP_AVAILABLE = False
    WeChatOperator = None


@router.get("/activate-wechat")
async def activate_wechat():
    """激活微信窗口"""
    if not OPERATOR_CPP_AVAILABLE or not WeChatOperator:
        raise HTTPException(status_code=500, detail="微信操作器不可用")
    
    try:
        operator = WeChatOperator()
        result = operator.check_wechat_visible()
        
        if result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "微信窗口已激活"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "激活微信失败"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"激活微信失败: {e}")
        raise HTTPException(status_code=500, detail=f"激活微信失败: {str(e)}")


@router.get("/wechat-window-info")
async def get_wechat_window_info():
    """获取微信窗口信息"""
    if not OPERATOR_CPP_AVAILABLE or not WeChatOperator:
        raise HTTPException(status_code=500, detail="微信操作器不可用")
    
    try:
        operator = WeChatOperator()
        result = operator.get_window_info()
        
        if result.get("success"):
            return {
                "success": True,
                "window_info": result.get("window_info"),
                "message": result.get("message", "窗口信息获取成功"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "获取窗口信息失败"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"获取窗口信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取窗口信息失败: {str(e)}")


@router.get("/read-messages")
async def read_messages(min_confidence: float = 0.6):
    """读取微信消息"""
    if not OPERATOR_CPP_AVAILABLE or not WeChatOperator:
        raise HTTPException(status_code=500, detail="微信操作器不可用")
    
    try:
        operator = WeChatOperator()
        result = operator.get_latest_message(min_confidence=min_confidence)
        
        if result.get("success"):
            return {
                "success": True,
                "latest_message": result.get("latest_message"),
                "all_messages": result.get("all_messages"),
                "message_count": result.get("message_count"),
                "message": result.get("message", "消息读取成功"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "消息读取失败"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"读取消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取消息失败: {str(e)}")


@router.get("/capture-message-area")
async def capture_message_area():
    """截图微信消息区域"""
    if not OPERATOR_CPP_AVAILABLE or not WeChatOperator:
        raise HTTPException(status_code=500, detail="微信操作器不可用")
    
    try:
        operator = WeChatOperator()
        result = operator.capture_message_area()
        
        if result.get("success"):
            return {
                "success": True,
                "image_path": result.get("image_path"),
                "image_size": result.get("image_size"),
                "region": result.get("region"),
                "message": result.get("message", "消息区域截图成功"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "截图失败"),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"截图失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图失败: {str(e)}")