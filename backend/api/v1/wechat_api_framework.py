from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import importlib
import logging
import os
import sys

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


module_paths = [
    os.path.join(os.path.dirname(__file__), "../../../cpp_rpa/build"),
    "/home/neogh/wechat_copilot/cpp_rpa/build",
    os.path.expanduser("~/wechat_copilot/cpp_rpa/build"),
]
for module_path in module_paths:
    if os.path.exists(module_path):
        sys.path.insert(0, module_path)
        break

try:
    wechat_rpa = importlib.import_module("wechat_rpa")
    WeChatManager = wechat_rpa.WeChatManager
    rpa_available = True
except Exception as e:
    logger.warning(f"微信API框架模块加载失败: {e}")
    WeChatManager = None
    rpa_available = False


_LISTEN_STATE: Dict[str, Any] = {
    "running": False,
    "chats": set(),
    "last_poll_at": None,
}


def _response(data: Any = None, message: str = "ok", code: int = 0, success: bool = True, elapsed_ms: int = 0, fallback_used: bool = False):
    return {
        "success": success,
        "code": code,
        "message": message,
        "request_id": f"req_{int(datetime.utcnow().timestamp() * 1000)}",
        "data": data if data is not None else {},
        "error": None if success else message,
        "meta": {
            "source": "cpp_rpa",
            "elapsed_ms": elapsed_ms,
            "fallback_used": fallback_used,
        },
    }


def _get_manager() -> Any:
    if not rpa_available or not WeChatManager:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    manager = WeChatManager()
    if not manager.initialize():
        raise HTTPException(status_code=500, detail="微信管理器初始化失败")
    return manager


def _has(obj: Any, name: str) -> bool:
    return hasattr(obj, name) and callable(getattr(obj, name))


class SwitchTabPayload(BaseModel):
    tab: str = Field(default="chat")


class SessionOpenPayload(BaseModel):
    who: str
    exact: bool = False


class SendTextPayload(BaseModel):
    who: str
    text: str


class SendMediaPayload(BaseModel):
    who: str
    file_path: str


class SendUrlCardPayload(BaseModel):
    who: str
    url: str
    message: str = ""


class ListenAddPayload(BaseModel):
    nickname: str


class ListenRemovePayload(BaseModel):
    nickname: str


class ContactAddPayload(BaseModel):
    keywords: str
    addmsg: str = ""
    remark: str = ""
    tags: List[str] = Field(default_factory=list)
    permission: str = "朋友圈"


@router.get("/wechat/core/online")
async def wechat_online():
    manager = _get_manager()

    online = True
    if _has(manager, "is_online"):
        online = bool(manager.is_online())
    elif _has(manager, "check_status"):
        status = manager.check_status()
        online = bool(status.get("available", False)) if isinstance(status, dict) else bool(status)

    return _response({"online": online})


@router.get("/wechat/core/my_info")
async def wechat_my_info():
    manager = _get_manager()
    data: Dict[str, Any] = {"nickname": "", "wechat_id": ""}

    if _has(manager, "get_my_info"):
        raw = manager.get_my_info()
        if isinstance(raw, dict):
            data.update(raw)

    return _response(data)


@router.get("/wechat/core/window_info")
async def wechat_window_info():
    manager = _get_manager()
    if not _has(manager, "get_wechat_window"):
        return _response({}, message="当前RPA模块缺少窗口信息接口", success=False, code=500)

    window = manager.get_wechat_window()
    data = {
        "title": str(getattr(window, "title", "") or ""),
        "window_class": str(getattr(window, "window_class", "") or ""),
        "x": int(getattr(window, "x", 0) or 0),
        "y": int(getattr(window, "y", 0) or 0),
        "width": int(getattr(window, "width", 0) or 0),
        "height": int(getattr(window, "height", 0) or 0),
    }
    return _response(data)


@router.post("/wechat/core/switch_tab")
async def wechat_switch_tab(payload: SwitchTabPayload):
    manager = _get_manager()

    tab = (payload.tab or "chat").strip().lower()
    if tab not in {"chat", "contact"}:
        raise HTTPException(status_code=400, detail="tab 仅支持 chat/contact")

    ok = False
    if tab == "chat" and _has(manager, "switch_to_chat"):
        ok = bool(manager.switch_to_chat())
    elif tab == "contact" and _has(manager, "switch_to_contact"):
        ok = bool(manager.switch_to_contact())

    if not ok:
        return _response({"tab": tab}, message="未找到可用的切换接口，已兼容返回", success=True, fallback_used=True)

    return _response({"tab": tab})


@router.get("/wechat/session/list")
async def wechat_session_list():
    manager = _get_manager()
    sessions: List[Dict[str, Any]] = []

    if _has(manager, "get_session"):
        raw = manager.get_session()
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    sessions.append(item)
                else:
                    sessions.append({"name": str(item)})

    return _response({"items": sessions})


@router.post("/wechat/session/open")
async def wechat_session_open(payload: SessionOpenPayload):
    manager = _get_manager()

    ok = False
    if _has(manager, "chat_with"):
        ok = bool(manager.chat_with(payload.who, payload.exact))
    elif _has(manager, "open_chat"):
        ok = bool(manager.open_chat(payload.who))

    return _response({"who": payload.who, "opened": ok}, fallback_used=not ok)


@router.get("/wechat/session/recent_groups")
async def wechat_recent_groups():
    manager = _get_manager()
    groups: List[str] = []

    if _has(manager, "get_all_recent_groups"):
        raw = manager.get_all_recent_groups()
        if isinstance(raw, list):
            groups = [str(item) for item in raw]

    return _response({"items": groups})


@router.get("/wechat/chat/messages")
async def wechat_chat_messages(chat_name: Optional[str] = None, limit: int = Query(default=30, ge=1, le=500)):
    manager = _get_manager()
    items: List[Dict[str, Any]] = []

    if _has(manager, "get_latest_messages"):
        raw = manager.get_latest_messages(int(limit))
        if isinstance(raw, list):
            for row in raw:
                if isinstance(row, dict):
                    if chat_name and str(row.get("chat_name", "")) != chat_name:
                        continue
                    items.append(row)

    return _response({"items": items, "limit": limit})


@router.post("/wechat/chat/send_text")
async def wechat_send_text(payload: SendTextPayload):
    manager = _get_manager()

    ok = False
    if _has(manager, "send_message_to"):
        ok = bool(manager.send_message_to(payload.who, payload.text))
    elif _has(manager, "send_msg"):
        ok = bool(manager.send_msg(payload.text, payload.who))

    return _response({"who": payload.who, "sent": ok}, fallback_used=not ok)


@router.post("/wechat/chat/send_image")
async def wechat_send_image(payload: SendMediaPayload):
    manager = _get_manager()

    ok = False
    if _has(manager, "send_image_to"):
        ok = bool(manager.send_image_to(payload.who, payload.file_path))

    return _response({"who": payload.who, "sent": ok, "file_path": payload.file_path}, fallback_used=not ok)


@router.post("/wechat/chat/send_file")
async def wechat_send_file(payload: SendMediaPayload):
    manager = _get_manager()

    ok = False
    if _has(manager, "send_file_to"):
        ok = bool(manager.send_file_to(payload.who, payload.file_path))

    return _response({"who": payload.who, "sent": ok, "file_path": payload.file_path}, fallback_used=not ok)


@router.post("/wechat/chat/send_url_card")
async def wechat_send_url_card(payload: SendUrlCardPayload):
    manager = _get_manager()

    ok = False
    if _has(manager, "send_url_card"):
        ok = bool(manager.send_url_card(payload.url, payload.who, payload.message))

    return _response({"who": payload.who, "url": payload.url, "sent": ok}, fallback_used=not ok)


@router.post("/wechat/listen/add")
async def wechat_listen_add(payload: ListenAddPayload):
    _LISTEN_STATE["chats"].add(payload.nickname)
    return _response({"listening_chats": sorted(list(_LISTEN_STATE["chats"]))})


@router.post("/wechat/listen/remove")
async def wechat_listen_remove(payload: ListenRemovePayload):
    if payload.nickname in _LISTEN_STATE["chats"]:
        _LISTEN_STATE["chats"].remove(payload.nickname)
    return _response({"listening_chats": sorted(list(_LISTEN_STATE["chats"]))})


@router.post("/wechat/listen/start")
async def wechat_listen_start():
    _LISTEN_STATE["running"] = True
    _LISTEN_STATE["last_poll_at"] = datetime.utcnow().isoformat()
    return _response({"running": True, "chats": sorted(list(_LISTEN_STATE["chats"]))})


@router.post("/wechat/listen/stop")
async def wechat_listen_stop(remove: bool = True):
    _LISTEN_STATE["running"] = False
    if remove:
        _LISTEN_STATE["chats"] = set()
    return _response({"running": False, "chats": sorted(list(_LISTEN_STATE["chats"]))})


@router.get("/wechat/listen/next")
async def wechat_listen_next(filter_mute: bool = False):
    manager = _get_manager()
    messages: Dict[str, Any] = {}

    if _has(manager, "get_next_new_message"):
        raw = manager.get_next_new_message(filter_mute)
        if isinstance(raw, dict):
            messages = raw

    _LISTEN_STATE["last_poll_at"] = datetime.utcnow().isoformat()
    return _response({"messages": messages, "state": {"running": _LISTEN_STATE["running"], "chats": sorted(list(_LISTEN_STATE["chats"]),), "last_poll_at": _LISTEN_STATE["last_poll_at"]}})


@router.get("/wechat/contact/friends")
async def wechat_contact_friends(n: Optional[int] = None):
    manager = _get_manager()
    items: List[Dict[str, Any]] = []

    if _has(manager, "get_friend_details"):
        raw = manager.get_friend_details(n) if n else manager.get_friend_details()
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    items.append(item)

    return _response({"items": items})


@router.get("/wechat/contact/new_friends")
async def wechat_contact_new_friends(acceptable: bool = True):
    manager = _get_manager()
    items: List[Dict[str, Any]] = []

    if _has(manager, "get_new_friends"):
        raw = manager.get_new_friends(acceptable)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    items.append(item)
                else:
                    items.append({"name": str(item)})

    return _response({"items": items})


@router.post("/wechat/contact/add_friend")
async def wechat_contact_add_friend(payload: ContactAddPayload):
    manager = _get_manager()
    ok = False

    if _has(manager, "add_new_friend"):
        ok = bool(
            manager.add_new_friend(
                payload.keywords,
                payload.addmsg,
                payload.remark,
                payload.tags,
                payload.permission,
            )
        )

    return _response({"keywords": payload.keywords, "success_added": ok}, fallback_used=not ok)
