from fastapi import APIRouter, HTTPException
import logging
import sys
import os
from pydantic import Field, BaseModel, validator
from typing import Dict, Any, Optional, List
import re

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


class RefreshAtomicProfileRequest(BaseModel):
    profile_name: str = Field(..., min_length=1, description="原子控件配置名称")
    max_nodes: int = Field(2200, ge=100, le=20000, description="最大扫描节点数")
    max_depth: int = Field(24, ge=-1, le=64, description="最大扫描深度，-1表示不限制")


class DiscoverAtomicRequest(BaseModel):
    max_nodes: int = Field(2200, ge=100, le=20000, description="最大扫描节点数")
    max_depth: int = Field(24, ge=-1, le=64, description="最大扫描深度，-1表示不限制")


class AtomicActionExecuteRequest(BaseModel):
    action_type: str = Field("click", description="动作类型：click/activate/input_text")
    profile_name: str = Field(..., min_length=1, description="原子控件配置名称")
    text: str = Field("", description="input_text动作时输入文本")
    max_nodes: int = Field(1200, ge=100, le=20000, description="最大扫描节点数")
    max_depth: int = Field(-1, ge=-1, le=64, description="最大扫描深度")


class AtomicQueryRequest(BaseModel):
    role_equals: str = Field("", description="角色精确匹配")
    role_contains: str = Field("", description="角色包含匹配")
    name_contains: str = Field("", description="名称包含匹配")
    text_contains: str = Field("", description="文本包含匹配")
    parent_role_equals: str = Field("", description="父角色精确匹配")
    path_contains: str = Field("", description="路径/编码包含匹配")
    path_code_contains: str = Field("", description="路径编码包含匹配（别名）")
    expected_depth: Optional[int] = Field(None, ge=0, le=64)
    min_depth: Optional[int] = Field(None, ge=0, le=64)
    max_depth: Optional[int] = Field(None, ge=0, le=64)
    require_visible: bool = False
    require_showing: bool = False
    require_editable: bool = False
    require_focusable: bool = False
    require_sensitive: bool = False
    require_non_empty_name: bool = False
    require_non_empty_text: bool = False
    require_non_empty_name_or_text: bool = False
    require_non_zero_rect: bool = False
    min_x_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_x_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_y_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_y_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    scan_max_nodes: int = Field(2400, ge=100, le=20000)
    scan_max_depth: int = Field(24, ge=-1, le=64)
    limit: int = Field(500, ge=1, le=5000)
    sort_by: str = Field("position", description="position/depth/name")
    sort_order: str = Field("asc", description="asc/desc")
    parse_contact_unread: bool = Field(True, description="解析联系人名称与未读数")
    include_chat_order: bool = Field(True, description="为聊天区域增加排序序号")


def _build_atomic_query_filters(request: AtomicQueryRequest) -> Dict[str, str]:
    filters: Dict[str, str] = {}

    def put_text(key: str, value: str) -> None:
        text = str(value or "").strip()
        if text:
            filters[key] = text

    def put_bool(key: str, value: bool) -> None:
        if bool(value):
            filters[key] = "true"

    def put_int(key: str, value: Optional[int]) -> None:
        if value is not None:
            filters[key] = str(int(value))

    def put_float(key: str, value: Optional[float]) -> None:
        if value is not None:
            filters[key] = f"{float(value):.4f}"

    put_text("role_equals", request.role_equals)
    put_text("role_contains", request.role_contains)
    put_text("name_contains", request.name_contains)
    put_text("text_contains", request.text_contains)
    put_text("parent_role_equals", request.parent_role_equals)

    merged_path = str(request.path_contains or "").strip() or str(request.path_code_contains or "").strip()
    put_text("path_contains", merged_path)

    put_int("expected_depth", request.expected_depth)
    put_int("min_depth", request.min_depth)
    put_int("max_depth", request.max_depth)

    put_bool("require_visible", request.require_visible)
    put_bool("require_showing", request.require_showing)
    put_bool("require_editable", request.require_editable)
    put_bool("require_focusable", request.require_focusable)
    put_bool("require_sensitive", request.require_sensitive)
    put_bool("require_non_empty_name", request.require_non_empty_name)
    put_bool("require_non_empty_text", request.require_non_empty_text)
    put_bool("require_non_zero_rect", request.require_non_zero_rect)

    put_float("min_x_ratio", request.min_x_ratio)
    put_float("max_x_ratio", request.max_x_ratio)
    put_float("min_y_ratio", request.min_y_ratio)
    put_float("max_y_ratio", request.max_y_ratio)

    return filters


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _parse_contact_unread_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    role = str(item.get("role") or "").lower()
    depth = _to_int(item.get("depth"), -1)
    source_text = str(item.get("text") or item.get("name") or "").strip()

    if depth != 15 or "list item" not in role or not source_text:
        return item

    name_match = re.match(r"^\s*([^\s]+)", source_text)
    unread_match = re.search(r"(?:\s|^)([1-9][0-9]?)\s*条未读", source_text)

    contact_name = name_match.group(1) if name_match else ""
    unread_count = int(unread_match.group(1)) if unread_match else 0

    item["contact_name"] = contact_name
    item["unread_count"] = unread_count
    item["has_unread"] = unread_count > 0
    return item


def _append_chat_order(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chat_items = []
    for idx, row in enumerate(items):
        role = str(row.get("role") or "").lower()
        depth = _to_int(row.get("depth"), -1)
        if depth == 14 and "list item" in role:
            y = _to_int(row.get("y"), 0)
            chat_items.append((idx, y))

    chat_items.sort(key=lambda x: x[1])
    for order, (source_idx, _) in enumerate(chat_items, start=1):
        items[source_idx]["chat_order"] = order

    return items


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


@router.get("/atomic/profiles")
async def list_atomic_profiles():
    """列出当前 C++ AT-SPI 原子控件配置名。"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        profiles = manager.list_atomic_profiles()
        return {
            "success": True,
            "profiles": profiles,
            "count": len(profiles),
        }
    except Exception as e:
        logger.error(f"获取原子控件配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取原子控件配置列表失败: {str(e)}")


@router.post("/atomic/profile/refresh")
async def refresh_atomic_profile(request: RefreshAtomicProfileRequest):
    """根据当前微信 AT-SPI 树，返回指定 profile 的重建建议参数。"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        suggestion = manager.refresh_atomic_profile(
            request.profile_name,
            int(request.max_nodes),
            int(request.max_depth),
        )
        return {
            "success": True,
            "profile_name": request.profile_name,
            "suggestion": suggestion,
            "message": "已生成重建建议" if suggestion else "未生成建议，请确认当前界面与 profile 是否匹配",
        }
    except Exception as e:
        logger.error(f"生成原子控件重建建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成原子控件重建建议失败: {str(e)}")


@router.post("/atomic/chat/discover")
async def discover_chat_atomic_groups(request: DiscoverAtomicRequest):
    """发现聊天消息原子容器，返回可直接用于前端重建的分组节点。"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        nodes = manager.find_chat_atomic_groups(int(request.max_nodes), int(request.max_depth))
        return {
            "success": True,
            "items": nodes,
            "count": len(nodes),
        }
    except Exception as e:
        logger.error(f"发现聊天原子容器失败: {e}")
        raise HTTPException(status_code=500, detail=f"发现聊天原子容器失败: {str(e)}")


@router.post("/atomic/popup/discover")
async def discover_popup_atomic_controls(request: DiscoverAtomicRequest):
    """发现当前弹窗相关的原子控件节点（菜单项/菜单容器）。"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        nodes = manager.detect_popup_atomic_controls(int(request.max_nodes), int(request.max_depth))
        return {
            "success": True,
            "items": nodes,
            "count": len(nodes),
        }
    except Exception as e:
        logger.error(f"发现弹窗原子控件失败: {e}")
        raise HTTPException(status_code=500, detail=f"发现弹窗原子控件失败: {str(e)}")


@router.get("/atomic/query/presets")
async def list_atomic_query_presets():
    """返回常用原子查询预设，便于前端一键加载。"""
    return {
        "success": True,
        "presets": [
            {
                "name": "contacts_depth15_unread",
                "label": "联系人区域(深度15 list item + 未读解析)",
                "filters": {
                    "expected_depth": 15,
                    "role_contains": "list item",
                    "require_non_zero_rect": True,
                    "require_showing": True,
                    "parse_contact_unread": True,
                },
            },
            {
                "name": "chat_depth14_messages",
                "label": "聊天显示区(深度14 list item，按序)",
                "filters": {
                    "expected_depth": 14,
                    "role_contains": "list item",
                    "require_non_zero_rect": True,
                    "require_showing": True,
                    "include_chat_order": True,
                },
            },
            {
                "name": "menu_buttons_depth6",
                "label": "菜单栏按钮(深度6 button)",
                "filters": {
                    "expected_depth": 6,
                    "role_contains": "button",
                    "require_non_zero_rect": True,
                    "require_non_empty_name": True,
                },
            },
            {
                "name": "send_button_depth15",
                "label": "发送按钮(深度15 button + 发送(S))",
                "filters": {
                    "expected_depth": 15,
                    "role_contains": "button",
                    "name_contains": "发送(S)",
                    "require_non_zero_rect": True,
                },
            },
            {
                "name": "chat_function_buttons_depth16",
                "label": "聊天功能按钮(深度16 button)",
                "filters": {
                    "expected_depth": 16,
                    "role_contains": "button",
                    "require_non_zero_rect": True,
                    "require_non_empty_name": True,
                },
            },
        ],
    }


@router.post("/atomic/query")
async def query_atomic_controls_advanced(request: AtomicQueryRequest):
    """多维原子控件查询：深度/名称/编码(path)/角色/状态/位置等。"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        filters = _build_atomic_query_filters(request)
        items = manager.query_atomic_controls(filters, int(request.scan_max_nodes), int(request.scan_max_depth))

        normalized: List[Dict[str, Any]] = []
        for row in items:
            node = dict(row)

            if request.require_non_empty_name_or_text:
                if not str(node.get("name") or "").strip() and not str(node.get("text") or "").strip():
                    continue

            if request.parse_contact_unread:
                node = _parse_contact_unread_fields(node)

            normalized.append(node)

        sort_by = str(request.sort_by or "position").strip().lower()
        sort_order = str(request.sort_order or "asc").strip().lower()
        reverse = sort_order == "desc"

        if sort_by == "depth":
            normalized.sort(key=lambda x: (_to_int(x.get("depth"), 999), _to_int(x.get("y"), 0), _to_int(x.get("x"), 0)), reverse=reverse)
        elif sort_by == "name":
            normalized.sort(key=lambda x: str(x.get("name") or x.get("text") or "").lower(), reverse=reverse)
        else:
            normalized.sort(key=lambda x: (_to_int(x.get("y"), 0), _to_int(x.get("x"), 0), _to_int(x.get("depth"), 999)), reverse=reverse)

        if request.include_chat_order:
            normalized = _append_chat_order(normalized)

        limited = normalized[: int(request.limit)]
        return {
            "success": True,
            "count": len(limited),
            "total": len(normalized),
            "filters": filters,
            "items": limited,
        }
    except Exception as e:
        logger.error(f"原子控件高级查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"原子控件高级查询失败: {str(e)}")


@router.post("/atomic/action/execute")
async def execute_atomic_action(request: AtomicActionExecuteRequest):
    """执行统一原子控件动作（click/activate/input_text）。"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        action_spec = {
            "action_type": str(request.action_type or "click"),
            "profile_name": str(request.profile_name or "").strip(),
            "text": str(request.text or ""),
            "max_nodes": str(int(request.max_nodes)),
            "max_depth": str(int(request.max_depth)),
        }
        execution = manager.execute_atomic_action(action_spec)
        success = str(execution.get("success", "0")) == "1"
        return {
            "success": success,
            "execution": execution,
            "message": execution.get("message", "执行完成"),
        }
    except Exception as e:
        logger.error(f"执行原子控件动作失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行原子控件动作失败: {str(e)}")