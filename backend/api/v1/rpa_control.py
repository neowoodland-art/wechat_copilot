from fastapi import APIRouter, HTTPException
import logging
import sys
import os
from pydantic import Field, BaseModel, validator
from typing import Dict, Any

# 导入配置存储函数
from .rpa_compatibility import _load_profile_store

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

router = APIRouter(prefix="/rpa", tags=["rpa"])


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


class SearchContactRequest(BaseModel):
    keyword: str = Field(..., min_length=1, description="搜索关键字，不能为空")

    @validator("keyword")
    def validate_keyword(cls, value):
        if not value.strip():
            raise ValueError("搜索关键字不能为空或全为空格")
        return value

class GetContactsListRequest(BaseModel):
    max_count: int = Field(100, ge=1, le=1000, description="获取联系人列表的最大数量，范围为1到1000")

class ClickControlRequest(BaseModel):
    control_name: str = Field(..., min_length=1, description="控件名称，不能为空")

    @validator("control_name")
    def validate_control_name(cls, value):
        if not value.strip():
            raise ValueError("控件名称不能为空或全为空格")
        return value

class InputTextRequest(BaseModel):
    control_name: str = Field(..., min_length=1, description="控件名称，不能为空")
    text: str = Field(..., min_length=1, description="输入的文本内容，不能为空")

    @validator("control_name", "text")
    def validate_non_empty(cls, value):
        if not value.strip():
            raise ValueError("控件名称或文本内容不能为空或全为空格")
        return value

class GenerateAnnotatedScreenshotRequest(BaseModel):
    profile_name: str = Field(..., min_length=1, description="配置名称，不能为空")

    @validator("profile_name")
    def validate_profile_name(cls, value):
        if not value.strip():
            raise ValueError("配置名称不能为空或全为空格")
        return value


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
    """截图消息区域并返回图片数据"""
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
            "screenshot": screenshot_base64,
            "message": "截图成功"
        }
    except Exception as e:
        logger.error(f"截图消息区域失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图消息区域失败: {str(e)}")


@router.post("/wechat/contacts/search")
async def search_contact(request: SearchContactRequest):
    """搜索联系人"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        contact = manager.search_contact(request.keyword)
        
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
async def get_contacts_list(request: GetContactsListRequest):
    """获取联系人列表"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        contacts = manager.get_contacts(request.max_count)
        
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
async def click_control(request: ClickControlRequest):
    """点击控件"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        engine = get_atspi_engine()
        success = engine.click_control_by_name(request.control_name)  # 假设WeChatManager提供此方法
        
        # 由于ATSPIEngine没有直接的click_control_by_name方法，我们使用WeChatManager
        manager = get_wechat_manager()
        success = manager.click_control_by_atspi(request.control_name)
        
        return {
            "success": success,
            "message": "控件点击成功" if success else "控件点击失败"
        }
    except Exception as e:
        logger.error(f"点击控件失败: {e}")
        raise HTTPException(status_code=500, detail=f"点击控件失败: {str(e)}")


@router.post("/atspi/input_text")
async def input_text(request: InputTextRequest):
    """输入文本到控件"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        success = manager.input_text_by_atspi(request.control_name, request.text)
        
        return {
            "success": success,
            "message": "文本输入成功" if success else "文本输入失败"
        }
    except Exception as e:
        logger.error(f"输入文本到控件失败: {e}")
        raise HTTPException(status_code=500, detail=f"输入文本到控件失败: {str(e)}")


@router.post("/atspi/get_text")
async def get_text_from_control(control_name: str):
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
async def humanized_click(x: int, y: int, button: int = 1):
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
async def humanized_input(text: str):
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


@router.post("/wechat/generate_annotated_screenshot")
async def generate_annotated_screenshot(request: GenerateAnnotatedScreenshotRequest):
    """生成带有标注的截图"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        # 加载配置
        store = _load_profile_store()
        profile = store["profiles"].get(request.profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 '{request.profile_name}' 不存在")

        # 获取当前窗口截图
        manager = get_wechat_manager()
        screenshot = manager.capture_full_window()

        # 在截图上绘制标注区域
        import cv2
        import numpy as np

        # 转换为RGB用于绘制
        if len(screenshot.shape) == 2:
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_GRAY2RGB)
        elif screenshot.shape[2] == 1:
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_GRAY2RGB)

        regions = profile.get("regions", {})
        colors = [
            (255, 0, 0),    # 红色
            (0, 255, 0),    # 绿色
            (0, 0, 255),    # 蓝色
            (255, 255, 0),  # 黄色
            (255, 0, 255),  # 品红
        ]

        for i, (region_id, region_data) in enumerate(regions.items()):
            bounds = region_data.get("bounds")
            if bounds:
                x, y, w, h = bounds["x"], bounds["y"], bounds["width"], bounds["height"]
                color = colors[i % len(colors)]
                
                # 绘制矩形
                cv2.rectangle(screenshot, (x, y), (x + w, y + h), color, 2)
                
                # 添加标签
                label = region_data.get("name", region_id)
                cv2.putText(screenshot, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # 转换为Base64
        _, buffer = cv2.imencode('.png', screenshot)
        screenshot_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "success": True,
            "screenshot": screenshot_base64,
            "message": f"生成带有 {len(regions)} 个标注区域的截图成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成标注截图失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成标注截图失败: {str(e)}")