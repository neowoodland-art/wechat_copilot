"""
微信激活器 - 用于激活微信窗口
"""

import logging
from typing import Dict, Any

from .wechat_operator import WeChatOperator, CPP_RPA_AVAILABLE

logger = logging.getLogger(__name__)

def ensure_wechat_is_active(pause_input: bool = True) -> Dict[str, Any]:
    """
    确保微信处于激活状态
    """
    try:
        if CPP_RPA_AVAILABLE:
            operator = WeChatOperator()
            result = operator.check_wechat_visible()
            if result.get("success"):
                return {
                    "success": True,
                    "message": "微信已激活",
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": result.get("error", "无法激活微信"),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
        else:
            logger.warning("C++ RPA不可用，无法激活微信")
            return {
                "success": False,
                "message": "C++ RPA不可用",
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"激活微信失败: {e}")
        return {
            "success": False,
            "message": f"激活微信失败: {str(e)}",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

def activate_wechat() -> Dict[str, Any]:
    """
    激活微信
    """
    return ensure_wechat_is_active()

__all__ = [
    'ensure_wechat_is_active',
    'activate_wechat'
]

