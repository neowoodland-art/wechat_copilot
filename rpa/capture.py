"""
屏幕捕获模块
"""

import logging
import tempfile
import os
import subprocess
import cv2
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

def capture_screen() -> Dict[str, Any]:
    """
    捕获屏幕
    """
    try:
        # 使用 OpenCV 捕获屏幕
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot_np = np.array(screenshot)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        # 保存截图到临时文件
        temp_path = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
        cv2.imwrite(temp_path, screenshot_bgr)

        return {
            "success": True,
            "image_path": temp_path,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"屏幕捕获失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

def capture_region(x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    """
    捕获指定区域
    """
    try:
        # 使用 OpenCV 捕获指定区域
        import pyautogui
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot_np = np.array(screenshot)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        # 保存截图到临时文件
        temp_path = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
        cv2.imwrite(temp_path, screenshot_bgr)

        return {
            "success": True,
            "image_path": temp_path,
            "region": {"x": x, "y": y, "width": width, "height": height},
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"区域捕获失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

__all__ = [
    'capture_screen',
    'capture_region'
]
