from fastapi import APIRouter, Depends, HTTPException
import logging
import sys
import os
from sqlmodel import Session, select, select, select, select
from typing import Dict, Any
from db.session import get_session
from db.models import User, Message
from datetime import datetime
import time

# 添加编译后的模块路径
module_paths = [
    os.path.join(os.path.dirname(__file__), '../../../cpp_rpa/build'),
    '/home/neogh/wechat_copilot/cpp_rpa/build',
    os.path.expanduser('~/wechat_copilot/cpp_rpa/build'),
]

for path in module_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

try:
    import wechat_rpa
    from wechat_rpa import WeChatManager, ATSPIEngine
    rpa_available = True
    print("✅ 成功导入 wechat_rpa 模块")
except ImportError as e:
    rpa_available = False
    print(f"警告: 无法导入 wechat_rpa 模块: {e}")
    print("RPA功能将不可用")
    # 临时导入，避免后续代码出错
    WeChatManager = None
    ATSPIEngine = None

logger = logging.getLogger(__name__)

router = APIRouter()

ocr_engine = None
ocr_engine_init_error = None


def get_ocr_engine():
    """按需初始化OCR引擎，避免服务启动阶段加载Paddle导致进程中止。"""
    global ocr_engine, ocr_engine_init_error

    if ocr_engine is not None:
        return ocr_engine

    if ocr_engine_init_error is not None:
        raise RuntimeError(ocr_engine_init_error)

    try:
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch")
        return ocr_engine
    except Exception as e:
        ocr_engine_init_error = f"OCR引擎初始化失败: {e}"
        raise RuntimeError(ocr_engine_init_error) from e

@router.post("/handle-message")
async def handle_message(
    message_data: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    RPA 调用此接口处理接收到的消息
    由 rpa/monitor.py 调用
    """
    try:
        wechat_id = message_data.get("wechat_id")
        nickname = message_data.get("nickname", "")
        content = message_data.get("content", "")
        
        if not wechat_id or not content:
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 1. 获取或创建用户
        user = session.exec(select(User).where(User.wechat_id == wechat_id)).first()
        if not user:
            user = User(wechat_id=wechat_id, nickname=nickname)
            session.add(user)
            session.commit()
            session.refresh(user)
        elif user.nickname != nickname:
            # 更新昵称
            user.nickname = nickname
            session.add(user)
            session.commit()
        
        # 2. 保存用户消息
        user_msg = Message(
            user_id=user.id,
            role="user",
            content=content,
            session_id=f"session_{datetime.now().strftime('%Y%m%d')}",
            confidence=message_data.get("confidence", 1.0)
        )
        session.add(user_msg)
        session.commit()
        
        # 3. 生成简单回复
        reply_text = f"已收到您的消息：{content}。AI回复功能正在维护中。"
        
        # 4. 保存助手回复
        assistant_msg = Message(
            user_id=user.id,
            role="assistant",
            content=reply_text,
            session_id=f"session_{datetime.now().strftime('%Y%m%d')}"
        )
        session.add(assistant_msg)
        session.commit()
        
        # 5. 返回成功响应
        return {
            "success": True,
            "reply": reply_text,
            "user_id": user.id,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        session.rollback()  # 添加回滚以确保事务一致性
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/test")
async def test_rpa():
    """
    测试RPA API是否正常工作
    """
    return {
        "success": True,
        "message": "RPA API正常工作",
        "timestamp": datetime.now().isoformat()
    }


def get_wechat_manager():
    """获取微信管理器实例"""
    if not rpa_available or not WeChatManager:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    manager = WeChatManager()
    if not manager.initialize():
        raise HTTPException(status_code=500, detail="无法初始化微信管理器")
    
    return manager


def get_atspi_engine():
    """获取ATSPI引擎实例"""
    if not rpa_available or not ATSPIEngine:
        raise HTTPException(status_code=500, detail="C++ ATSPI模块不可用")
    
    engine = ATSPIEngine()
    if not engine.initialize():
        raise HTTPException(status_code=500, detail="无法初始化ATSPI引擎")
    
    return engine


@router.get("/status")
async def get_rpa_status():
    """获取RPA模块状态"""
    return {
        "rpa_available": rpa_available,
        "message": "RPA模块可用" if rpa_available else "RPA模块不可用"
    }


@router.post("/wechat/check_status")
async def check_wechat_status():
    """检查微信状态"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        is_active = manager.is_wechat_active()
        
        return {
            "success": True,
            "is_active": is_active,
            "message": "微信已激活" if is_active else "微信未激活"
        }
    except Exception as e:
        logger.error(f"检查微信状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查微信状态失败: {str(e)}")


@router.post("/wechat/get_window_info")
async def get_wechat_window_info():
    """获取微信窗口信息"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        window_info = manager.get_wechat_window()

        return {
            "success": True,
            "window_info": {
                "id": window_info.id,
                "title": window_info.title,
                "x": window_info.x,
                "y": window_info.y,
                "width": window_info.width,
                "height": window_info.height,
                "is_active": window_info.is_active
            }
        }
    except Exception as e:
        logger.error(f"获取微信窗口信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取微信窗口信息失败: {str(e)}")


@router.post("/wechat/messages/latest")
async def get_latest_messages(count: int = 10):
    """获取最新消息"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        messages = manager.get_latest_messages(count)
        
        message_list = []
        for msg in messages:
            message_list.append({
                "content": msg.content,
                "confidence": msg.confidence,
                "sender": getattr(msg, 'sender', ''),
                "timestamp": getattr(msg, 'timestamp', 0)
            })
        
        return {
            "success": True,
            "messages": message_list
        }
    except Exception as e:
        logger.error(f"获取最新消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最新消息失败: {str(e)}")


@router.post("/wechat/capture_message_area")
async def capture_message_area():
    """截图消息区域"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        screenshot = manager.capture_message_area()
        
        # 将截图数据转换为 Base64
        import base64
        import cv2
        _, buffer = cv2.imencode('.png', screenshot)
        screenshot_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "success": True,
            "screenshot": f"data:image/png;base64,{screenshot_base64}",
            "message": "截图成功"
        }
    except Exception as e:
        logger.error(f"截图消息区域失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图消息区域失败: {str(e)}")


@router.post("/wechat/contacts/search")
async def search_contact(keyword: str):
    """搜索联系人"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        contact = manager.search_contact(keyword)
        
        return {
            "success": True,
            "contact": {
                "name": contact.name,
                "wechat_id": contact.wechat_id,
                "alias": getattr(contact, 'alias', ''),
                "remark": getattr(contact, 'remark', '')
            }
        }
    except Exception as e:
        logger.error(f"搜索联系人失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索联系人失败: {str(e)}")


@router.post("/wechat/contacts/list")
async def get_contacts_list(max_count: int = 100):
    """获取联系人列表"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        contacts = manager.get_contacts(max_count)

        contact_list = []
        for contact in contacts:
            contact_list.append({
                "name": contact.name,
                "wechat_id": contact.wechat_id,
                "alias": getattr(contact, 'alias', ''),
                "remark": getattr(contact, 'remark', '')
            })

        return {
            "success": True,
            "contacts": contact_list
        }
    except Exception as e:
        logger.error(f"获取联系人列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取联系人列表失败: {str(e)}")


@router.post("/atspi/click_control")
async def click_control_api(control_name: str):
    """点击控件"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        success = manager.click_control_by_atspi(control_name)
        
        return {
            "success": success,
            "message": "控件点击成功" if success else "控件点击失败"
        }
    except Exception as e:
        logger.error(f"点击控件失败: {e}")
        raise HTTPException(status_code=500, detail=f"点击控件失败: {str(e)}")


@router.post("/atspi/input_text")
async def input_text_api(control_name: str, text: str):
    """输入文本到控件"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        success = manager.input_text_by_atspi(control_name, text)
        
        return {
            "success": success,
            "message": "文本输入成功" if success else "文本输入失败"
        }
    except Exception as e:
        logger.error(f"输入文本到控件失败: {e}")
        raise HTTPException(status_code=500, detail=f"输入文本到控件失败: {str(e)}")


@router.post("/atspi/get_text")
async def get_text_from_control_api(control_name: str):
    """从控件获取文本"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        text = manager.get_control_text_by_atspi(control_name)
        
        return {
            "success": True,
            "text": text,
            "message": "获取文本成功"
        }
    except Exception as e:
        logger.error(f"从控件获取文本失败: {e}")
        raise HTTPException(status_code=500, detail=f"从控件获取文本失败: {str(e)}")


@router.post("/humanized/click")
async def humanized_click_api(x: int, y: int, button: int = 1):
    """拟人化点击"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        success = manager.humanized_click(x, y, button)
        
        return {
            "success": success,
            "message": "拟人化点击成功" if success else "拟人化点击失败"
        }
    except Exception as e:
        logger.error(f"拟人化点击失败: {e}")
        raise HTTPException(status_code=500, detail=f"拟人化点击失败: {str(e)}")


@router.post("/humanized/input")
async def humanized_input_api(text: str):
    """拟人化输入"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        success = manager.humanized_input(text)
        
        return {
            "success": success,
            "message": "拟人化输入成功" if success else "拟人化输入失败"
        }
    except Exception as e:
        logger.error(f"拟人化输入失败: {e}")
        raise HTTPException(status_code=500, detail=f"拟人化输入失败: {str(e)}")


@router.post("/humanized/move_mouse")
async def humanized_move_mouse_api(x: int, y: int):
    """拟人化鼠标移动"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        success = manager.humanized_move_mouse(x, y)

        return {
            "success": success,
            "message": "拟人化鼠标移动成功" if success else "拟人化鼠标移动失败"
        }
    except Exception as e:
        logger.error(f"拟人化鼠标移动失败: {e}")
        raise HTTPException(status_code=500, detail=f"拟人化鼠标移动失败: {str(e)}")


@router.post("/humanized/random_delay")
async def humanized_random_delay_api(min_delay: float, max_delay: float):
    """随机延迟"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        import random
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

        return {
            "success": True,
            "message": f"随机延迟 {delay:.2f} 秒完成"
        }
    except Exception as e:
        logger.error(f"随机延迟失败: {e}")
        raise HTTPException(status_code=500, detail=f"随机延迟失败: {str(e)}")


@router.post("/atspi/get_messages")
async def get_messages():
    """获取消息列表"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ ATSPI模块不可用")

    try:
        engine = get_atspi_engine()
        messages = engine.get_messages()
        return {"success": True, "messages": messages}
    except Exception as e:
        logger.error(f"获取消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取消息失败: {str(e)}")

@router.post("/atspi/get_contacts")
async def get_contacts():
    """获取联系人列表"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ ATSPI模块不可用")

    try:
        engine = get_atspi_engine()
        contacts = engine.get_contacts()
        return {"success": True, "contacts": contacts}
    except Exception as e:
        logger.error(f"获取联系人失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取联系人失败: {str(e)}")

@router.post("/atspi/get_ui_elements")
async def get_ui_elements():
    """获取界面控件信息"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ ATSPI模块不可用")

    try:
        engine = get_atspi_engine()
        elements = engine.get_ui_elements()
        return {"success": True, "elements": elements}
    except Exception as e:
        logger.error(f"获取界面控件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取界面控件信息失败: {str(e)}")

@router.post("/atspi/traverse_control_tree")
async def traverse_control_tree():
    """遍历控件树信息"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ ATSPI模块不可用")

    try:
        engine = get_atspi_engine()
        tree_info = engine.traverse_control_tree()
        return {"success": True, "tree_info": tree_info}
    except Exception as e:
        logger.error(f"遍历控件树失败: {e}")
        raise HTTPException(status_code=500, detail=f"遍历控件树失败: {str(e)}")

@router.post("/atspi/capture_message_area")
async def capture_message_area():
    """截图消息区域并返回信息"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ ATSPI模块不可用")

    try:
        engine = get_atspi_engine()
        screenshot_info = engine.capture_message_area()
        return {"success": True, "screenshot_info": screenshot_info}
    except Exception as e:
        logger.error(f"截图消息区域失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图消息区域失败: {str(e)}")

@router.post("/ocr/extract_text")
async def extract_text_from_image(image_path: str):
    """从图像中提取文本"""
    try:
        ocr_engine = get_ocr_engine()
        result = ocr_engine.ocr(image_path, cls=True)
        extracted_text = [line[1][0] for line in result[0]]
        return {
            "success": True,
            "text": extracted_text
        }
    except Exception as e:
        logger.error(f"OCR文本提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"OCR文本提取失败: {str(e)}")

@router.get("/ui-elements")
async def get_ui_elements():
    """
    获取微信界面元素
    """
    try:
        manager = get_wechat_manager()
        elements = manager.get_ui_elements()
        return {
            "success": True,
            "elements": elements
        }
    except Exception as e:
        logger.error(f"获取界面元素失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/ui-tree-analysis")
async def analyze_ui_tree():
    """
    遍历控件树并分析元素
    """
    try:
        engine = get_atspi_engine()
        analysis = engine.analyze_ui_tree()
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"分析控件树失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }