from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import json
import logging
import re
import time
import uuid
import subprocess
import random
import os
import shutil

try:
    import yaml
except Exception:
    yaml = None

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from db.session import get_session
from backend.core.atspi_tree_service import ATSPIQueryOptions, build_snapshot_payload
from db.models import (
    WechatUIProfile,
    WechatUIRegion,
    WechatUIControlDefinition,
    WechatUIControlSnapshot,
    WechatOperationPackage,
    WechatOperationAction,
    WechatOperationRunLog,
    WechatChatRuntime,
    WechatListenState,
    WechatChatHistory,
)

router = APIRouter(prefix="/wechat", tags=["rpa_definition"])
logger = logging.getLogger(__name__)


DEFAULT_REGION_KEYS = [
    "search_bar",
    "main_menu",
    "contact_list",
    "chat_display",
    "chat_input",
    "new_window",
    "no_window",
]


def _json_dumps(data: Any) -> str:
    return json.dumps(data if data is not None else {}, ensure_ascii=False)


def _json_loads(text: str, default: Any):
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


class ProfileUpsertPayload(BaseModel):
    id: Optional[int] = None
    profile_name: str
    template_type: str = "chat"
    window_type: str = "chat"
    enabled: bool = True
    window_x: int = 0
    window_y: int = 0
    window_width: int = 0
    window_height: int = 0
    version: str = "v1"
    meta: Dict[str, Any] = Field(default_factory=dict)


class RegionBatchUpsertPayload(BaseModel):
    profile_id: int
    regions: List[Dict[str, Any]]


class ControlUpsertPayload(BaseModel):
    id: Optional[int] = None
    control_uid: str
    profile_id: int
    enabled: bool = True
    region_key: str = ""
    role: str = ""
    control_type: str = ""
    depth: int = 0
    depth_code: str = "00"
    access_path: str = ""
    path_numeric_code: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    text: str = ""
    window_type: str = "chat"
    actions: List[str] = Field(default_factory=list)
    is_clickable: bool = False
    has_post_click_change: bool = False
    source_type: str = "merged"
    source_ref_id: str = ""
    confidence: float = 0.0
    meta: Dict[str, Any] = Field(default_factory=dict)


class ControlsImportPayload(BaseModel):
    profile: Optional[ProfileUpsertPayload] = None
    regions: List[Dict[str, Any]] = Field(default_factory=list)
    controls: List[ControlUpsertPayload] = Field(default_factory=list)


class ControlsDeletePayload(BaseModel):
    profile_id: Optional[int] = None
    ids: List[int] = Field(default_factory=list)
    control_uids: List[str] = Field(default_factory=list)
    purge_profile: bool = False
    force_unlink_actions: bool = False


class SnapshotSavePayload(BaseModel):
    profile_id: int
    source_type: str = "atspi"
    capture_batch_id: str = ""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)


class PackageUpsertPayload(BaseModel):
    id: Optional[int] = None
    package_code: str
    package_name: str
    enabled: bool = True
    scene_type: str = "chat"
    profile_id: Optional[int] = None
    description: str = ""
    version: str = "v1"
    config: Dict[str, Any] = Field(default_factory=dict)


class ActionBatchUpsertPayload(BaseModel):
    package_id: int
    actions: List[Dict[str, Any]]


class RuntimeUpsertPayload(BaseModel):
    session_id: str
    chat_name: str
    msg_id: str
    msg_type: str = "text"
    sender: str = "other"
    content: str = ""
    content_json: Dict[str, Any] = Field(default_factory=dict)
    acked: bool = False


class RuntimeFlushPayload(BaseModel):
    customer_id: int
    session_id: Optional[str] = None
    clear_after_flush: bool = True


class ListenStateUpsertPayload(BaseModel):
    listener_key: str = "default"
    running: bool = False
    chats: List[str] = Field(default_factory=list)
    last_msg_id: str = ""


class PackageExecutePayload(BaseModel):
    package_id: Optional[int] = None
    package_code: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class PackageYamlImportPayload(BaseModel):
    yaml_text: str
    upsert: bool = True


class AtomicControlsGeneratePayload(BaseModel):
    profile_id: int
    source: str = "chat"
    max_nodes: int = 2200
    max_depth: int = 24
    limit: int = 200
    filters: Dict[str, Any] = Field(default_factory=dict)


def _render_template(value: Any, variables: Dict[str, Any]) -> Any:
    if not isinstance(value, str):
        return value

    def _replace(match: re.Match) -> str:
        key = str(match.group(1) or "").strip()
        return str(variables.get(key, ""))

    return re.sub(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}", _replace, value)


def _render_payload(data: Any, variables: Dict[str, Any]) -> Any:
    if isinstance(data, dict):
        return {k: _render_payload(v, variables) for k, v in data.items()}
    if isinstance(data, list):
        return [_render_payload(v, variables) for v in data]
    return _render_template(data, variables)


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _evaluate_condition(params: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    var_name = str(params.get("var") or params.get("left_var") or "").strip()
    op = str(params.get("op") or "==").strip()
    left = params.get("left", variables.get(var_name))
    right = params.get("value", params.get("right"))

    left_num = _to_float(left)
    right_num = _to_float(right)
    use_num = left_num is not None and right_num is not None

    lhs = left_num if use_num else left
    rhs = right_num if use_num else right

    if op == "==":
        result = lhs == rhs
    elif op == "!=":
        result = lhs != rhs
    elif op == ">":
        result = bool(use_num and lhs > rhs)
    elif op == ">=":
        result = bool(use_num and lhs >= rhs)
    elif op == "<":
        result = bool(use_num and lhs < rhs)
    elif op == "<=":
        result = bool(use_num and lhs <= rhs)
    elif op == "contains":
        result = str(rhs) in str(lhs)
    elif op == "not_contains":
        result = str(rhs) not in str(lhs)
    elif op == "is_true":
        result = bool(lhs)
    elif op == "is_false":
        result = not bool(lhs)
    else:
        raise ValueError(f"不支持的分支操作符: {op}")

    return {
        "result": bool(result),
        "var": var_name,
        "op": op,
        "left": left,
        "right": right,
    }


def _extract_bounds_from_row(row: WechatUIControlDefinition) -> Dict[str, int]:
    return {
        "x": int(row.x or 0),
        "y": int(row.y or 0),
        "width": int(row.width or 0),
        "height": int(row.height or 0),
    }


def _resolve_action_bounds(
    action_params: Dict[str, Any],
    action: WechatOperationAction,
    package: WechatOperationPackage,
    session: Session,
) -> Dict[str, int]:
    direct = action_params.get("bounds") or {}
    width = int(direct.get("width", 0) or 0)
    height = int(direct.get("height", 0) or 0)
    if width > 0 and height > 0:
        return {
            "x": int(direct.get("x", 0) or 0),
            "y": int(direct.get("y", 0) or 0),
            "width": width,
            "height": height,
        }

    control_uid = str(action_params.get("control_uid") or action.control_uid or "").strip()
    if not control_uid:
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    profile_id = action_params.get("profile_id") or package.profile_id
    if not profile_id:
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    control_row = session.exec(
        select(WechatUIControlDefinition).where(
            WechatUIControlDefinition.profile_id == int(profile_id),
            WechatUIControlDefinition.control_uid == control_uid,
        )
    ).first()
    if not control_row:
        return {"x": 0, "y": 0, "width": 0, "height": 0}
    return _extract_bounds_from_row(control_row)


def _resolve_atomic_profile_name(
    action_params: Dict[str, Any],
    action: WechatOperationAction,
    package: WechatOperationPackage,
    session: Session,
) -> str:
    direct = str(action_params.get("atomic_profile_name") or action_params.get("atspi_profile_name") or "").strip()
    if direct:
        return direct

    control_uid = str(action_params.get("control_uid") or action.control_uid or "").strip()
    profile_id = action_params.get("profile_id") or package.profile_id
    if not control_uid or not profile_id:
        return ""

    control_row = session.exec(
        select(WechatUIControlDefinition).where(
            WechatUIControlDefinition.profile_id == int(profile_id),
            WechatUIControlDefinition.control_uid == control_uid,
        )
    ).first()
    if not control_row:
        return ""

    meta = _json_loads(control_row.meta_json, {})
    return str(meta.get("atomic_profile_name") or "").strip()


def _execute_atomic_via_manager(manager: Any, action_type: str, profile_name: str, text: str = "") -> Dict[str, Any]:
    if not manager:
        return {"success": False, "message": "manager不可用"}
    if not profile_name:
        return {"success": False, "message": "atomic_profile_name为空"}

    try:
        result = manager.execute_atomic_action(
            {
                "action_type": action_type,
                "profile_name": profile_name,
                "text": text,
            }
        )
    except Exception as err:
        return {"success": False, "message": f"AT-SPI动作异常: {err}"}

    ok = str(result.get("success", "0")) == "1" or bool(result.get("success") is True)
    output = {
        "success": ok,
        "strategy": "atspi_atomic",
        "execution": result,
    }
    if not ok:
        output["message"] = str(result.get("message") or "AT-SPI动作执行失败")
    return output


def _xdotool_click(bounds: Dict[str, int]) -> Dict[str, Any]:
    x = int(bounds.get("x", 0) or 0)
    y = int(bounds.get("y", 0) or 0)
    width = max(0, int(bounds.get("width", 0) or 0))
    height = max(0, int(bounds.get("height", 0) or 0))
    if width <= 0 or height <= 0:
        return {"success": False, "message": "无效bounds"}

    target_x = x + width // 2
    target_y = y + height // 2

    try:
        move_ret = subprocess.run(
            ["xdotool", "mousemove", "--sync", str(target_x), str(target_y)],
            capture_output=True,
            text=True,
            timeout=1.2,
        )
    except FileNotFoundError:
        return {"success": False, "message": "未安装xdotool，无法执行真实鼠标移动点击"}
    except subprocess.TimeoutExpired:
        try:
            move_ret = subprocess.run(
                ["xdotool", "mousemove", str(target_x), str(target_y)],
                capture_output=True,
                text=True,
                timeout=1.2,
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "鼠标移动超时(同步/非同步均失败)"}
        except Exception as err:
            return {"success": False, "message": f"鼠标移动异常: {err}"}
    except Exception as err:
        return {"success": False, "message": f"鼠标移动异常: {err}"}
    if move_ret.returncode != 0:
        return {"success": False, "message": move_ret.stderr.strip() or "鼠标移动失败"}

    try:
        click_ret = subprocess.run(
            ["xdotool", "click", "1"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except FileNotFoundError:
        return {"success": False, "message": "未安装xdotool，无法执行真实鼠标点击"}
    except Exception as err:
        return {"success": False, "message": f"鼠标点击异常: {err}"}
    if click_ret.returncode != 0:
        return {"success": False, "message": click_ret.stderr.strip() or "鼠标点击失败"}

    return {"success": True, "target": {"x": target_x, "y": target_y}}


def _xdotool_type_text(text: str) -> Dict[str, Any]:
    content = str(text or "")
    if not content:
        return {"success": True, "text_len": 0}
    try:
        type_ret = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "20", content],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except FileNotFoundError:
        return {"success": False, "message": "未安装xdotool，无法执行真实键盘输入"}
    except Exception as err:
        return {"success": False, "message": f"键盘输入异常: {err}"}

    if type_ret.returncode != 0:
        return {"success": False, "message": type_ret.stderr.strip() or "键盘输入失败"}
    return {"success": True, "text_len": len(content)}


def _clipboard_copy_text(text: str) -> Dict[str, Any]:
    content = str(text or "")
    display = str(os.environ.get("DISPLAY") or "").strip()
    wayland = str(os.environ.get("WAYLAND_DISPLAY") or "").strip()

    candidates: List[Dict[str, Any]] = []
    if display:
        candidates.extend(
            [
                {"tool": "xclip", "cmd": ["xclip", "-selection", "clipboard", "-in", "-loops", "1"]},
                {"tool": "xsel", "cmd": ["xsel", "--clipboard", "--input"]},
            ]
        )
    if wayland:
        candidates.append({"tool": "wl-copy", "cmd": ["wl-copy"]})
    if not candidates:
        candidates.extend(
            [
                {"tool": "xclip", "cmd": ["xclip", "-selection", "clipboard", "-in", "-loops", "1"]},
                {"tool": "xsel", "cmd": ["xsel", "--clipboard", "--input"]},
                {"tool": "wl-copy", "cmd": ["wl-copy"]},
            ]
        )

    errors: List[str] = []
    for candidate in candidates:
        tool = str(candidate.get("tool") or "")
        cmd = candidate.get("cmd") or []
        try:
            ret = subprocess.run(
                cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=3.0,
            )
        except FileNotFoundError:
            errors.append(f"{tool}: not found")
            continue
        except subprocess.TimeoutExpired:
            errors.append(f"{tool}: timeout")
            continue
        except Exception as err:
            errors.append(f"{tool}: {err}")
            continue

        if ret.returncode == 0:
            return {"success": True, "tool": tool}
        message = (ret.stderr or ret.stdout or "").strip() or "failed"
        errors.append(f"{tool}: {message}")

    return {
        "success": False,
        "message": "剪贴板写入失败",
        "errors": errors,
        "display": display,
        "wayland_display": wayland,
    }


def _xdotool_paste_shortcut() -> Dict[str, Any]:
    try:
        paste_ret = subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except FileNotFoundError:
        return {"success": False, "message": "未安装xdotool，无法执行粘贴快捷键"}
    except Exception as err:
        return {"success": False, "message": f"粘贴快捷键异常: {err}"}

    if paste_ret.returncode != 0:
        return {"success": False, "message": paste_ret.stderr.strip() or "Ctrl+V 执行失败"}
    return {"success": True}


def _clipboard_read_text() -> Dict[str, Any]:
    display = str(os.environ.get("DISPLAY") or "").strip()
    wayland = str(os.environ.get("WAYLAND_DISPLAY") or "").strip()

    candidates: List[tuple[str, List[str]]] = []
    if display:
        candidates.extend([
            ("xclip", ["xclip", "-selection", "clipboard", "-out"]),
            ("xsel", ["xsel", "--clipboard", "--output"]),
        ])
    if wayland:
        candidates.append(("wl-paste", ["wl-paste", "-n"]))
    if not candidates:
        candidates.extend([
            ("xclip", ["xclip", "-selection", "clipboard", "-out"]),
            ("xsel", ["xsel", "--clipboard", "--output"]),
            ("wl-paste", ["wl-paste", "-n"]),
        ])

    last_error = ""
    for tool_name, command in candidates:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return {"success": True, "tool": tool_name, "text": result.stdout}
            last_error = result.stderr.strip() or f"{tool_name} 读取失败"
        except FileNotFoundError:
            last_error = f"未安装 {tool_name}"
        except subprocess.TimeoutExpired:
            last_error = f"{tool_name} 读取超时"
        except Exception as err:
            last_error = f"{tool_name} 读取异常: {err}"

    return {"success": False, "message": last_error or "无法读取剪贴板内容"}


def _paste_via_xclip_loops_once(text: str) -> Dict[str, Any]:
    content = str(text or "")
    if not content:
        return {"success": True, "text_len": 0, "mode": "empty"}

    if not _command_available("xclip"):
        return {"success": False, "message": "未安装 xclip"}

    proc = None
    try:
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard", "-in", "-loops", "1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.stdin is None:
            raise RuntimeError("xclip stdin 不可用")
        proc.stdin.write(content)
        proc.stdin.close()

        _sleep_ms(80)
        paste_ret = _xdotool_paste_shortcut()
        if not paste_ret.get("success"):
            if proc and proc.poll() is None:
                proc.kill()
            return {"success": False, "stage": "paste_shortcut", "detail": paste_ret}

        try:
            ret_code = proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if proc and proc.poll() is None:
                proc.kill()
            return {
                "success": False,
                "stage": "clipboard_consume",
                "detail": {"message": "未检测到粘贴请求，可能焦点不在输入框"},
            }

        if ret_code != 0:
            stderr = ""
            try:
                stderr = (proc.stderr.read() if proc.stderr else "") or ""
            except Exception:
                stderr = ""
            return {
                "success": False,
                "stage": "clipboard_consume",
                "detail": {"message": stderr.strip() or "xclip 粘贴消费失败"},
            }

        return {
            "success": True,
            "text_len": len(content),
            "mode": "clipboard_paste",
            "clipboard_tool": "xclip-loops",
            "clipboard_verified": True,
        }
    except Exception as err:
        if proc and proc.poll() is None:
            proc.kill()
        return {"success": False, "stage": "clipboard_copy", "detail": {"message": str(err)}}


def _command_available(name: str) -> bool:
    return bool(shutil.which(name))


def _build_ops_env_status() -> Dict[str, Any]:
    display = str(os.environ.get("DISPLAY") or "").strip()
    wayland = str(os.environ.get("WAYLAND_DISPLAY") or "").strip()

    tools = {
        "xdotool": _command_available("xdotool"),
        "xclip": _command_available("xclip"),
        "xsel": _command_available("xsel"),
        "wl_copy": _command_available("wl-copy"),
    }

    warnings: List[str] = []
    if not display and not wayland:
        warnings.append("未检测到 DISPLAY/WAYLAND_DISPLAY，GUI自动化可能不可用")
    if not tools["xdotool"]:
        warnings.append("缺少 xdotool：无法执行真实鼠标移动点击和粘贴快捷键")
    if display and (not tools["xclip"] and not tools["xsel"]):
        warnings.append("X11会话缺少 xclip/xsel：无法写入系统剪贴板")
    if wayland and (not tools["wl_copy"]):
        warnings.append("Wayland会话缺少 wl-copy：无法写入系统剪贴板")
    if (not display and not wayland) and (not tools["xclip"] and not tools["xsel"] and not tools["wl_copy"]):
        warnings.append("缺少剪贴板工具（xclip/xsel/wl-copy）")

    clipboard_ok = (display and (tools["xclip"] or tools["xsel"])) or (wayland and tools["wl_copy"]) or (tools["xclip"] or tools["xsel"] or tools["wl_copy"])
    can_real_execute = bool((display or wayland) and tools["xdotool"] and clipboard_ok)

    return {
        "success": True,
        "display": display,
        "wayland_display": wayland,
        "tools": tools,
        "can_real_execute": can_real_execute,
        "warnings": warnings,
    }


def _sleep_ms(ms: int) -> None:
    try:
        delay = max(0, int(ms or 0))
    except Exception:
        delay = 0
    if delay > 0:
        time.sleep(delay / 1000.0)


def _calc_humanized_step_delay_ms(params: Dict[str, Any], default_ms: int = 180, default_jitter_ms: int = 80) -> int:
    base = int(params.get("human_delay_ms", params.get("step_pause_ms", params.get("pause_ms", default_ms))) or default_ms)
    jitter = int(params.get("human_delay_jitter_ms", default_jitter_ms) or 0)
    if jitter < 0:
        jitter = 0
    delay = base + (random.randint(0, jitter) if jitter > 0 else 0)
    return max(0, min(3000, int(delay)))


def _input_text_with_fallback(text: str, manager: Any) -> Dict[str, Any]:
    content = str(text or "")
    if not content:
        return {"success": True, "text_len": 0, "mode": "empty"}

    display = str(os.environ.get("DISPLAY") or "").strip()
    if display and _command_available("xclip"):
        loop_ret = _paste_via_xclip_loops_once(content)
        if loop_ret.get("success"):
            return loop_ret

    copy_ret = _clipboard_copy_text(content)
    if not copy_ret.get("success"):
        return {
            "success": False,
            "stage": "clipboard_copy",
            "detail": copy_ret,
        }

    _sleep_ms(80)
    paste_ret = _xdotool_paste_shortcut()
    if not paste_ret.get("success"):
        return {
            "success": False,
            "stage": "paste_shortcut",
            "detail": paste_ret,
        }

    return {
        "success": True,
        "text_len": len(content),
        "mode": "clipboard_paste",
        "clipboard_tool": copy_ret.get("tool"),
        "clipboard_verified": False,
    }


def _get_action_rendered_params(action: WechatOperationAction, variables: Dict[str, Any]) -> Dict[str, Any]:
    params = _json_loads(action.params_json, {})
    rendered = _render_payload(params, variables)
    return rendered if isinstance(rendered, dict) else {}


def _apply_humanized_step_pause(action: WechatOperationAction, variables: Dict[str, Any], dry_run: bool) -> int:
    if dry_run:
        return 0
    rendered = _get_action_rendered_params(action, variables)
    delay_ms = _calc_humanized_step_delay_ms(rendered)
    _sleep_ms(delay_ms)
    return delay_ms


def _parse_contact_unread(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for row in nodes:
        role = str(row.get("role") or "").strip().lower()
        depth = int(row.get("depth", 0) or 0)
        if role != "list item" or depth != 15:
            continue
        text = str(row.get("text") or row.get("name") or "").strip()
        if not text:
            continue
        name = text.split(" ", 1)[0].strip()
        unread = 0
        m = re.search(r"\b([1-9][0-9]?)\s*条未读", text)
        if m:
            unread = min(99, int(m.group(1)))
        items.append(
            {
                "name": name,
                "unread": unread,
                "raw_text": text,
                "bounds": {
                    "x": int(row.get("x", 0) or 0),
                    "y": int(row.get("y", 0) or 0),
                    "width": int(row.get("width", 0) or 0),
                    "height": int(row.get("height", 0) or 0),
                },
            }
        )
    return items


def _parse_chat_messages(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in nodes:
        role = str(row.get("role") or "").strip().lower()
        depth = int(row.get("depth", 0) or 0)
        if role != "list item" or depth != 14:
            continue
        text = str(row.get("text") or row.get("name") or "").strip()
        if not text:
            continue
        y = int(row.get("y", 0) or 0)
        rows.append(
            {
                "text": text,
                "y": y,
                "bounds": {
                    "x": int(row.get("x", 0) or 0),
                    "y": y,
                    "width": int(row.get("width", 0) or 0),
                    "height": int(row.get("height", 0) or 0),
                },
            }
        )
    rows.sort(key=lambda item: item.get("y", 0))
    for idx, row in enumerate(rows):
        row["seq"] = idx + 1
    return rows


def _extract_peer_messages(chat_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chat_messages:
        return []

    xs: List[int] = []
    for row in chat_messages:
        bounds = row.get("bounds") or {}
        x = int(bounds.get("x", 0) or 0)
        xs.append(x)

    sorted_x = sorted(xs)
    median_x = sorted_x[len(sorted_x) // 2] if sorted_x else 0

    peer_rows: List[Dict[str, Any]] = []
    for row in chat_messages:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        low_text = text.lower()
        if low_text.startswith("我:") or low_text.startswith("you:"):
            continue

        bounds = row.get("bounds") or {}
        x = int(bounds.get("x", 0) or 0)
        if x <= median_x:
            peer_rows.append(row)

    if not peer_rows:
        for row in chat_messages:
            text = str(row.get("text") or "").strip()
            if text:
                peer_rows.append(row)

    return peer_rows


async def _execute_action(
    action: WechatOperationAction,
    package: WechatOperationPackage,
    manager: Any,
    variables: Dict[str, Any],
    session: Session,
    dry_run: bool,
) -> Dict[str, Any]:
    params = _json_loads(action.params_json, {})
    rendered = _render_payload(params, variables)
    action_type = str(action.action_type or "").strip().lower()

    if action_type in {"wait.ms", "wait"}:
        ms = int(rendered.get("ms", rendered.get("wait_ms", 500)) or 500)
        if not dry_run:
            time.sleep(max(0, ms) / 1000.0)
        return {"success": True, "wait_ms": ms}

    if action_type in {"ui.click_bounds", "click"}:
        atomic_profile_name = _resolve_atomic_profile_name(rendered, action, package, session)
        if atomic_profile_name:
            if dry_run:
                return {"success": True, "dry_run": True, "strategy": "atspi_atomic", "atomic_profile_name": atomic_profile_name}
            atspi_ret = _execute_atomic_via_manager(manager, "activate", atomic_profile_name)
            if atspi_ret.get("success"):
                return atspi_ret
        bounds = _resolve_action_bounds(rendered, action, package, session)
        if dry_run:
            return {"success": True, "dry_run": True, "bounds": bounds}
        click_ret = _xdotool_click(bounds)
        if atomic_profile_name:
            click_ret["fallback_from"] = "atspi_atomic"
            click_ret["atomic_profile_name"] = atomic_profile_name
        return click_ret

    if action_type in {"ui.input_text", "humanized.input"}:
        text = str(rendered.get("text") or rendered.get("content") or "")
        atomic_profile_name = _resolve_atomic_profile_name(rendered, action, package, session)
        if atomic_profile_name:
            if dry_run:
                return {"success": True, "dry_run": True, "strategy": "atspi_atomic", "atomic_profile_name": atomic_profile_name, "text": text}
            atspi_ret = _execute_atomic_via_manager(manager, "input_text", atomic_profile_name, text)
            if atspi_ret.get("success"):
                return atspi_ret
        if dry_run:
            return {"success": True, "dry_run": True, "text": text}
        focus_flag = rendered.get("focus_before_input")
        if focus_flag is None:
            focus_before_input = bool(rendered.get("control_uid") or rendered.get("bounds"))
        else:
            focus_before_input = bool(focus_flag)
        if focus_before_input:
            focus_bounds = _resolve_action_bounds(rendered, action, package, session)
            if int(focus_bounds.get("width", 0) or 0) > 0 and int(focus_bounds.get("height", 0) or 0) > 0:
                focus_click = _xdotool_click(focus_bounds)
                if not focus_click.get("success"):
                    return {"success": False, "stage": "focus_input", "detail": focus_click}
                time.sleep(0.12)
        input_result = _input_text_with_fallback(text, manager)
        if not input_result.get("success"):
            return {"success": False, "stage": "input_text", "detail": input_result.get("detail") or input_result}
        return input_result

    if action_type == "chat.send_text":
        text = str(rendered.get("text") or rendered.get("content") or variables.get("message", ""))
        input_atomic_profile = str(rendered.get("input_atomic_profile_name") or "").strip()
        send_atomic_profile = str(rendered.get("send_atomic_profile_name") or "").strip()

        if input_atomic_profile and send_atomic_profile and not dry_run:
            input_ret = _execute_atomic_via_manager(manager, "input_text", input_atomic_profile, text)
            if not input_ret.get("success"):
                return {"success": False, "stage": "input_text", "detail": input_ret}
            click_ret = _execute_atomic_via_manager(manager, "activate", send_atomic_profile)
            if not click_ret.get("success"):
                return {"success": False, "stage": "click_send", "detail": click_ret}
            return {
                "success": True,
                "strategy": "atspi_atomic",
                "sent_text_len": len(text),
                "input_profile": input_atomic_profile,
                "send_profile": send_atomic_profile,
            }

        input_bounds = _resolve_action_bounds({"bounds": rendered.get("input_bounds") or rendered.get("input") or {}}, action, package, session)
        send_bounds = _resolve_action_bounds({"bounds": rendered.get("send_bounds") or rendered.get("send") or {}}, action, package, session)
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "text": text,
                "input_bounds": input_bounds,
                "send_bounds": send_bounds,
            }
        click_input = _xdotool_click(input_bounds)
        if click_input.get("success"):
            time.sleep(0.12)
        input_result = _input_text_with_fallback(text, manager)
        if not input_result.get("success"):
            detail = {
                "input": input_result.get("detail") or input_result,
                "focus": click_input,
            }
            return {"success": False, "stage": "input_text", "detail": detail}
        click_send = _xdotool_click(send_bounds)
        if not click_send.get("success"):
            return {"success": False, "stage": "click_send", "detail": click_send}
        return {
            "success": True,
            "sent_text_len": len(text),
            "input_mode": input_result.get("mode", "unknown"),
        }

    if action_type in {"atspi.extract_contacts_unread", "atspi.contacts_unread"}:
        if dry_run:
            return {"success": True, "dry_run": True, "hint": "depth=15, role=list item"}
        payload = build_snapshot_payload(
            manager=manager,
            options=ATSPIQueryOptions(
                role_filter="list item",
                max_depth=15,
                max_nodes=8000,
                auto_activate=False,
                auto_refresh_tree=True,
                refresh_rounds=2,
                refresh_interval_ms=400,
                deep_search=True,
                prefer_tree=True,
                deduplicate=False,
            ),
        )
        nodes = list(payload.get("nodes") or [])
        contacts = _parse_contact_unread(nodes)
        variables["contacts"] = contacts
        variables["unread_contacts"] = [c for c in contacts if int(c.get("unread", 0)) > 0]
        return {"success": True, "count": len(contacts), "unread_count": len(variables["unread_contacts"])}

    if action_type in {"atspi.extract_chat_messages", "atspi.chat_messages"}:
        if dry_run:
            return {"success": True, "dry_run": True, "hint": "depth=14, role=list item"}
        payload = build_snapshot_payload(
            manager=manager,
            options=ATSPIQueryOptions(
                role_filter="list item",
                max_depth=14,
                max_nodes=10000,
                auto_activate=False,
                auto_refresh_tree=True,
                refresh_rounds=2,
                refresh_interval_ms=400,
                deep_search=True,
                prefer_tree=True,
                deduplicate=False,
            ),
        )
        nodes = list(payload.get("nodes") or [])
        messages = _parse_chat_messages(nodes)
        variables["chat_messages"] = messages
        return {"success": True, "count": len(messages)}

    if action_type in {"llm.core", "ai.parse_chat", "chat.ai_parse"}:
        from core.ai_router import AIRouter

        scene_type = str(rendered.get("scene_type") or action.llm_scene or package.scene_type or "chat").strip() or "chat"
        model_preference = str(rendered.get("model_preference") or "auto").strip() or "auto"
        chat_name = str(variables.get("chat_name") or rendered.get("chat_name") or "").strip()
        user_prompt = str(rendered.get("prompt") or "").strip()

        chat_messages = variables.get("chat_messages") or []
        if not isinstance(chat_messages, list):
            chat_messages = []

        peer_rows = _extract_peer_messages(chat_messages)
        peer_texts = [str(item.get("text") or "").strip() for item in peer_rows if str(item.get("text") or "").strip()]
        max_peer_lines = max(1, min(int(rendered.get("max_peer_lines", 20) or 20), 120))
        peer_texts = peer_texts[-max_peer_lines:]

        if not peer_texts and str(rendered.get("require_messages", "true")).lower() in {"1", "true", "yes", "on"}:
            return {"success": False, "message": "缺少可用于AI解析的对方聊天内容，请先执行 atspi.chat_messages"}

        if not user_prompt:
            user_prompt = "请基于以下对方聊天内容，输出JSON：{intent,emotion,key_points,reply_suggestion}，回复必须是JSON。"

        chat_blob = "\n".join(peer_texts)
        final_prompt = (
            f"场景: {scene_type}\n"
            f"会话: {chat_name or 'unknown'}\n"
            f"对方聊天内容:\n{chat_blob}\n\n"
            f"任务要求:\n{user_prompt}"
        )

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "scene_type": scene_type,
                "model_preference": model_preference,
                "peer_message_count": len(peer_texts),
                "prompt_preview": final_prompt[:600],
            }

        router_obj = AIRouter()
        route_context = {
            "scene_type": scene_type,
            "model_preference": model_preference,
            "chat_name": chat_name,
            "peer_message_count": len(peer_texts),
            "module": "rpa_definition.ops_execute",
        }
        llm_result = await router_obj.route_request(final_prompt, route_context)

        llm_text = str(llm_result.get("response") or "")
        variables["llm_response"] = llm_text
        variables["llm_model_used"] = str(llm_result.get("model_used") or "")
        variables["llm_success"] = bool(llm_result.get("success", False))
        variables["peer_messages"] = peer_rows
        variables["peer_message_texts"] = peer_texts

        return {
            "success": bool(llm_result.get("success", False)),
            "scene_type": scene_type,
            "model_used": llm_result.get("model_used", ""),
            "fallback_used": bool(llm_result.get("fallback_used", False)),
            "peer_message_count": len(peer_texts),
            "response": llm_text,
            "routing_trace": llm_result.get("routing_trace", []),
            "error": llm_result.get("error", "") if not bool(llm_result.get("success", False)) else "",
        }

    return {"success": False, "message": f"未支持的action_type: {action.action_type}"}


@router.post("/ui/settings/profile/upsert")
async def upsert_ui_profile(payload: ProfileUpsertPayload, session: Session = Depends(get_session)):
    row: Optional[WechatUIProfile] = None

    if payload.id:
        row = session.get(WechatUIProfile, payload.id)
    if not row:
        row = session.exec(
            select(WechatUIProfile).where(
                WechatUIProfile.profile_name == payload.profile_name,
                WechatUIProfile.template_type == payload.template_type,
            )
        ).first()

    if not row:
        row = WechatUIProfile(
            profile_name=payload.profile_name,
            template_type=payload.template_type,
        )

    row.window_type = payload.window_type
    row.enabled = payload.enabled
    row.window_x = payload.window_x
    row.window_y = payload.window_y
    row.window_width = payload.window_width
    row.window_height = payload.window_height
    row.version = payload.version
    row.meta_json = _json_dumps(payload.meta)
    row.updated_at = datetime.utcnow()

    session.add(row)
    session.commit()
    session.refresh(row)

    for idx, region_key in enumerate(DEFAULT_REGION_KEYS):
        exists = session.exec(
            select(WechatUIRegion).where(
                WechatUIRegion.profile_id == row.id,
                WechatUIRegion.region_key == region_key,
            )
        ).first()
        if exists:
            continue
        session.add(
            WechatUIRegion(
                profile_id=int(row.id),
                region_key=region_key,
                region_name=region_key,
                sort_order=idx,
            )
        )
    session.commit()

    return {"success": True, "profile_id": row.id}


@router.get("/ui/settings/profiles")
async def list_ui_profiles(template_type: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(WechatUIProfile).order_by(WechatUIProfile.updated_at.desc())
    if template_type:
        stmt = stmt.where(WechatUIProfile.template_type == template_type)

    rows = session.exec(stmt).all()
    items = [
        {
            "id": row.id,
            "profile_name": row.profile_name,
            "template_type": row.template_type,
            "window_type": row.window_type,
            "enabled": row.enabled,
            "window": {
                "x": row.window_x,
                "y": row.window_y,
                "width": row.window_width,
                "height": row.window_height,
            },
            "version": row.version,
            "meta": _json_loads(row.meta_json, {}),
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        }
        for row in rows
    ]
    return {"success": True, "items": items}


@router.get("/ui/settings/profile")
async def get_ui_profile(profile_id: int, session: Session = Depends(get_session)):
    profile = session.get(WechatUIProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile不存在")

    regions = session.exec(
        select(WechatUIRegion)
        .where(WechatUIRegion.profile_id == profile_id)
        .order_by(WechatUIRegion.sort_order.asc(), WechatUIRegion.id.asc())
    ).all()

    controls = session.exec(
        select(WechatUIControlDefinition)
        .where(WechatUIControlDefinition.profile_id == profile_id)
        .order_by(WechatUIControlDefinition.updated_at.desc())
    ).all()

    return {
        "success": True,
        "profile": {
            "id": profile.id,
            "profile_name": profile.profile_name,
            "template_type": profile.template_type,
            "window_type": profile.window_type,
            "enabled": profile.enabled,
            "window": {
                "x": profile.window_x,
                "y": profile.window_y,
                "width": profile.window_width,
                "height": profile.window_height,
            },
            "version": profile.version,
            "meta": _json_loads(profile.meta_json, {}),
        },
        "regions": [
            {
                "id": row.id,
                "region_key": row.region_key,
                "region_name": row.region_name,
                "enabled": row.enabled,
                "bounds": {"x": row.x, "y": row.y, "width": row.width, "height": row.height},
                "sort_order": row.sort_order,
                "meta": _json_loads(row.meta_json, {}),
            }
            for row in regions
        ],
        "control_count": len(controls),
    }


@router.post("/ui/regions/upsert_batch")
async def upsert_regions(payload: RegionBatchUpsertPayload, session: Session = Depends(get_session)):
    profile = session.get(WechatUIProfile, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile不存在")

    affected = 0
    for idx, item in enumerate(payload.regions):
        region_key = str(item.get("region_key") or "").strip()
        if not region_key:
            continue

        row = session.exec(
            select(WechatUIRegion).where(
                WechatUIRegion.profile_id == payload.profile_id,
                WechatUIRegion.region_key == region_key,
            )
        ).first()

        if not row:
            row = WechatUIRegion(profile_id=payload.profile_id, region_key=region_key)

        bounds = item.get("bounds") or {}
        row.region_name = str(item.get("region_name") or region_key)
        row.enabled = bool(item.get("enabled", True))
        row.x = int(bounds.get("x", item.get("x", 0)) or 0)
        row.y = int(bounds.get("y", item.get("y", 0)) or 0)
        row.width = int(bounds.get("width", item.get("width", 0)) or 0)
        row.height = int(bounds.get("height", item.get("height", 0)) or 0)
        row.sort_order = int(item.get("sort_order", idx) or idx)
        row.meta_json = _json_dumps(item.get("meta") or {})
        row.updated_at = datetime.utcnow()

        session.add(row)
        affected += 1

    session.commit()
    return {"success": True, "affected": affected}


@router.post("/ui/controls/upsert")
async def upsert_control(payload: ControlUpsertPayload, session: Session = Depends(get_session)):
    row: Optional[WechatUIControlDefinition] = None

    if payload.id:
        row = session.get(WechatUIControlDefinition, payload.id)
    if not row:
        row = session.exec(
            select(WechatUIControlDefinition).where(
                WechatUIControlDefinition.profile_id == payload.profile_id,
                WechatUIControlDefinition.control_uid == payload.control_uid,
            )
        ).first()

    if not row:
        row = WechatUIControlDefinition(
            control_uid=payload.control_uid,
            profile_id=payload.profile_id,
        )

    row.enabled = payload.enabled
    row.region_key = payload.region_key
    row.role = payload.role
    row.control_type = payload.control_type
    row.depth = payload.depth
    row.depth_code = payload.depth_code
    row.access_path = payload.access_path
    row.path_numeric_code = payload.path_numeric_code
    row.x = payload.x
    row.y = payload.y
    row.width = payload.width
    row.height = payload.height
    row.text = payload.text
    row.window_type = payload.window_type
    row.actions_json = _json_dumps(payload.actions)
    row.is_clickable = payload.is_clickable
    row.has_post_click_change = payload.has_post_click_change
    row.source_type = payload.source_type
    row.source_ref_id = payload.source_ref_id
    row.confidence = payload.confidence
    row.meta_json = _json_dumps(payload.meta)
    row.updated_at = datetime.utcnow()

    session.add(row)
    session.commit()
    session.refresh(row)
    return {"success": True, "id": row.id}


@router.post("/ui/controls/delete")
async def delete_controls(payload: ControlsDeletePayload, session: Session = Depends(get_session)):
    target_rows: List[WechatUIControlDefinition] = []
    profile_id = int(payload.profile_id) if payload.profile_id is not None else None

    if payload.purge_profile and profile_id is None:
        raise HTTPException(status_code=400, detail="purge_profile=true 时必须传 profile_id")

    for control_id in payload.ids:
        row = session.get(WechatUIControlDefinition, int(control_id))
        if row and (profile_id is None or int(row.profile_id or 0) == profile_id):
            target_rows.append(row)

    uid_list = [str(uid or "").strip() for uid in payload.control_uids if str(uid or "").strip()]
    if uid_list:
        stmt = select(WechatUIControlDefinition).where(WechatUIControlDefinition.control_uid.in_(uid_list))
        if profile_id is not None:
            stmt = stmt.where(WechatUIControlDefinition.profile_id == profile_id)
        uid_rows = session.exec(stmt).all()
        target_rows.extend(uid_rows)

    if payload.purge_profile and profile_id is not None:
        profile_rows = session.exec(
            select(WechatUIControlDefinition).where(WechatUIControlDefinition.profile_id == profile_id)
        ).all()
        target_rows.extend(profile_rows)

    dedup: Dict[int, WechatUIControlDefinition] = {}
    for row in target_rows:
        if row.id is not None:
            dedup[int(row.id)] = row

    if not dedup:
        if payload.purge_profile:
            return {"success": True, "deleted": 0}
        raise HTTPException(status_code=404, detail="未找到可删除的控件")

    deleting_uids = sorted({str(row.control_uid or "").strip() for row in dedup.values() if str(row.control_uid or "").strip()})
    if deleting_uids:
        action_rows = session.exec(select(WechatOperationAction).where(WechatOperationAction.control_uid.in_(deleting_uids))).all()
        if action_rows:
            package_ids = sorted({int(row.package_id) for row in action_rows if row.package_id is not None})
            package_map: Dict[int, WechatOperationPackage] = {}
            if package_ids:
                packages = session.exec(select(WechatOperationPackage).where(WechatOperationPackage.id.in_(package_ids))).all()
                package_map = {int(item.id): item for item in packages if item.id is not None}

            scoped_rows: List[WechatOperationAction] = []
            for row in action_rows:
                if row.package_id is None:
                    scoped_rows.append(row)
                    continue

                pkg = package_map.get(int(row.package_id))
                if pkg is None:
                    continue

                if profile_id is None:
                    scoped_rows.append(row)
                    continue

                if pkg.profile_id is None or int(pkg.profile_id) == profile_id:
                    scoped_rows.append(row)

            action_rows = scoped_rows

            if action_rows and payload.force_unlink_actions:
                deleting_uid_set = set(deleting_uids)
                for row in action_rows:
                    if str(row.control_uid or "").strip() in deleting_uid_set:
                        row.control_uid = ""
                        try:
                            params = _json_loads(row.params_json, {})
                            if isinstance(params, dict) and str(params.get("control_uid") or "").strip() in deleting_uid_set:
                                params["control_uid"] = ""
                                row.params_json = _json_dumps(params)
                        except Exception:
                            pass
                        row.updated_at = datetime.utcnow()
                        session.add(row)

            if action_rows and not payload.force_unlink_actions:
                refs: List[Dict[str, Any]] = []
                for row in action_rows:
                    pkg = package_map.get(int(row.package_id)) if row.package_id is not None else None
                    refs.append(
                        {
                            "control_uid": str(row.control_uid or ""),
                            "package_id": row.package_id,
                            "package_code": str(pkg.package_code or "") if pkg else "",
                            "package_name": str(pkg.package_name or "") if pkg else "",
                            "package_profile_id": int(pkg.profile_id) if pkg and pkg.profile_id is not None else None,
                            "action_id": row.id,
                            "action_key": str(row.action_key or ""),
                            "action_name": str(row.action_name or ""),
                        }
                    )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "控件已被微信操作打包引用，请先在打包步骤中移除对应控件后再删除原子控件",
                        "references": refs,
                    },
                )

    for row in dedup.values():
        session.delete(row)
    session.commit()

    return {"success": True, "deleted": len(dedup)}


@router.get("/ui/controls")
async def list_controls(
    profile_id: int,
    region_key: Optional[str] = None,
    window_type: Optional[str] = None,
    enabled_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    stmt = select(WechatUIControlDefinition).where(WechatUIControlDefinition.profile_id == profile_id)
    if region_key:
        stmt = stmt.where(WechatUIControlDefinition.region_key == region_key)
    if window_type:
        stmt = stmt.where(WechatUIControlDefinition.window_type == window_type)
    if enabled_only:
        stmt = stmt.where(WechatUIControlDefinition.enabled == True)

    rows = session.exec(stmt.order_by(WechatUIControlDefinition.updated_at.desc())).all()
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]

    items = [
        {
            "id": row.id,
            "control_uid": row.control_uid,
            "enabled": row.enabled,
            "region_key": row.region_key,
            "role": row.role,
            "control_type": row.control_type,
            "depth": row.depth,
            "depth_code": row.depth_code,
            "access_path": row.access_path,
            "path_numeric_code": row.path_numeric_code,
            "bounds": {"x": row.x, "y": row.y, "width": row.width, "height": row.height},
            "text": row.text,
            "window_type": row.window_type,
            "actions": _json_loads(row.actions_json, []),
            "is_clickable": row.is_clickable,
            "has_post_click_change": row.has_post_click_change,
            "source_type": row.source_type,
            "source_ref_id": row.source_ref_id,
            "confidence": row.confidence,
            "meta": _json_loads(row.meta_json, {}),
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        }
        for row in page_rows
    ]

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/ui/controls/references")
async def list_control_references(
    profile_id: int,
    include_cross_profile: bool = True,
    session: Session = Depends(get_session),
):
    controls = session.exec(
        select(WechatUIControlDefinition).where(WechatUIControlDefinition.profile_id == int(profile_id))
    ).all()

    control_uid_set = {
        str(row.control_uid or "").strip()
        for row in controls
        if str(row.control_uid or "").strip()
    }
    if not control_uid_set:
        return {
            "success": True,
            "profile_id": int(profile_id),
            "controls_count": len(controls),
            "control_uid_count": 0,
            "references_count": 0,
            "same_profile_count": 0,
            "cross_profile_count": 0,
            "items": [],
        }

    action_rows = session.exec(
        select(WechatOperationAction).where(WechatOperationAction.control_uid.in_(sorted(control_uid_set)))
    ).all()

    package_ids = sorted({int(row.package_id) for row in action_rows if row.package_id is not None})
    package_map: Dict[int, WechatOperationPackage] = {}
    if package_ids:
        packages = session.exec(select(WechatOperationPackage).where(WechatOperationPackage.id.in_(package_ids))).all()
        package_map = {int(item.id): item for item in packages if item.id is not None}

    refs: List[Dict[str, Any]] = []
    same_profile_count = 0
    cross_profile_count = 0

    for action in action_rows:
        pkg = package_map.get(int(action.package_id)) if action.package_id is not None else None
        package_profile_id = int(pkg.profile_id) if pkg and pkg.profile_id is not None else None
        same_profile = (package_profile_id == int(profile_id)) if package_profile_id is not None else False

        if same_profile:
            same_profile_count += 1
        else:
            cross_profile_count += 1

        if (not include_cross_profile) and (not same_profile):
            continue

        refs.append(
            {
                "control_uid": str(action.control_uid or ""),
                "action_id": action.id,
                "action_key": str(action.action_key or ""),
                "action_name": str(action.action_name or ""),
                "action_type": str(action.action_type or ""),
                "package_id": action.package_id,
                "package_code": str(pkg.package_code or "") if pkg else "",
                "package_name": str(pkg.package_name or "") if pkg else "",
                "package_profile_id": package_profile_id,
                "same_profile": same_profile,
            }
        )

    refs.sort(key=lambda item: (str(item.get("control_uid") or ""), str(item.get("package_code") or ""), str(item.get("action_key") or "")))

    return {
        "success": True,
        "profile_id": int(profile_id),
        "controls_count": len(controls),
        "control_uid_count": len(control_uid_set),
        "references_count": len(refs),
        "same_profile_count": same_profile_count,
        "cross_profile_count": cross_profile_count,
        "items": refs,
    }


@router.get("/ui/controls/export")
async def export_controls(profile_id: int, session: Session = Depends(get_session)):
    profile = session.get(WechatUIProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile不存在")

    regions = session.exec(
        select(WechatUIRegion)
        .where(WechatUIRegion.profile_id == profile_id)
        .order_by(WechatUIRegion.sort_order.asc(), WechatUIRegion.id.asc())
    ).all()

    controls = session.exec(
        select(WechatUIControlDefinition)
        .where(WechatUIControlDefinition.profile_id == profile_id)
        .order_by(WechatUIControlDefinition.updated_at.desc())
    ).all()

    return {
        "success": True,
        "profile": {
            "id": profile.id,
            "profile_name": profile.profile_name,
            "template_type": profile.template_type,
            "window_type": profile.window_type,
            "enabled": profile.enabled,
            "window": {
                "x": profile.window_x,
                "y": profile.window_y,
                "width": profile.window_width,
                "height": profile.window_height,
            },
            "version": profile.version,
            "meta": _json_loads(profile.meta_json, {}),
        },
        "regions": [
            {
                "region_key": row.region_key,
                "region_name": row.region_name,
                "enabled": row.enabled,
                "bounds": {"x": row.x, "y": row.y, "width": row.width, "height": row.height},
                "sort_order": row.sort_order,
                "meta": _json_loads(row.meta_json, {}),
            }
            for row in regions
        ],
        "controls": [
            {
                "control_uid": row.control_uid,
                "enabled": row.enabled,
                "region_key": row.region_key,
                "role": row.role,
                "control_type": row.control_type,
                "depth": row.depth,
                "depth_code": row.depth_code,
                "access_path": row.access_path,
                "path_numeric_code": row.path_numeric_code,
                "x": row.x,
                "y": row.y,
                "width": row.width,
                "height": row.height,
                "text": row.text,
                "window_type": row.window_type,
                "actions": _json_loads(row.actions_json, []),
                "is_clickable": row.is_clickable,
                "has_post_click_change": row.has_post_click_change,
                "source_type": row.source_type,
                "source_ref_id": row.source_ref_id,
                "confidence": row.confidence,
                "meta": _json_loads(row.meta_json, {}),
            }
            for row in controls
        ],
    }


@router.post("/ui/controls/import")
async def import_controls(payload: ControlsImportPayload, session: Session = Depends(get_session)):
    profile_id: Optional[int] = None

    if payload.profile:
        profile_resp = await upsert_ui_profile(payload.profile, session)
        profile_id = int(profile_resp["profile_id"])

    if profile_id is None:
        if payload.controls:
            profile_id = payload.controls[0].profile_id
        else:
            raise HTTPException(status_code=400, detail="缺少profile信息")

    if payload.regions:
        await upsert_regions(RegionBatchUpsertPayload(profile_id=profile_id, regions=payload.regions), session)

    affected = 0
    for control in payload.controls:
        control_data = control.model_copy(update={"profile_id": profile_id})
        await upsert_control(control_data, session)
        affected += 1

    return {"success": True, "profile_id": profile_id, "imported_controls": affected}


@router.post("/ui/controls/generate_from_atomic")
async def generate_controls_from_atomic(payload: AtomicControlsGeneratePayload, session: Session = Depends(get_session)):
    from .rpa_compatibility import get_wechat_manager, rpa_available

    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    profile = session.get(WechatUIProfile, int(payload.profile_id))
    if not profile:
        raise HTTPException(status_code=404, detail="profile不存在")

    manager = get_wechat_manager()
    source = str(payload.source or "chat").strip().lower()
    max_nodes = max(100, min(int(payload.max_nodes or 2200), 20000))
    max_depth = int(payload.max_depth)

    if source == "chat":
        nodes = manager.find_chat_atomic_groups(max_nodes, max_depth)
    elif source == "popup":
        nodes = manager.detect_popup_atomic_controls(max_nodes, max_depth)
    else:
        filters = dict(payload.filters or {})
        filters = {str(k): str(v) for k, v in filters.items() if str(k).strip()}
        nodes = manager.query_atomic_controls(filters, max_nodes, max_depth)

    if not nodes:
        return {"success": True, "generated": 0, "items": [], "message": "未发现可生成节点"}

    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _guess_region_key(depth: int, role: str) -> str:
        role_l = role.lower()
        if depth == 15 and "list item" in role_l:
            return "contact_list"
        if depth == 14 and "list item" in role_l:
            return "chat_display"
        if depth in {15, 16} and "button" in role_l:
            return "chat_input"
        if depth == 6 and "button" in role_l:
            return "main_menu"
        if "menu" in role_l:
            return "main_menu"
        return "chat"

    def _guess_atomic_profile_name(depth: int, role: str, name: str, text: str) -> str:
        role_l = role.lower()
        content = f"{name} {text}".strip()
        if depth == 15 and "button" in role_l and "发送" in content:
            return "chat_send_button"
        if depth == 6 and "button" in role_l:
            return "menu_bar_buttons"
        if depth == 16 and "button" in role_l:
            return "chat_action_buttons"
        if depth == 15 and "list item" in role_l:
            return "contact_list_items"
        if depth == 14 and "list item" in role_l:
            return "chat_message_items"
        if "menu item" in role_l or "menu" in role_l:
            return "popup_menu_items"
        if "text" in role_l:
            return "chat_input_box"
        return ""

    generated: List[Dict[str, Any]] = []
    limit = max(1, min(int(payload.limit or 200), 3000))

    for idx, node in enumerate(nodes[:limit]):
        depth = _to_int(node.get("depth"), 0)
        role = str(node.get("role") or "")
        name = str(node.get("name") or "")
        text = str(node.get("text") or name or "")
        x = _to_int(node.get("x"), 0)
        y = _to_int(node.get("y"), 0)
        w = _to_int(node.get("width"), 0)
        h = _to_int(node.get("height"), 0)
        path = str(node.get("path") or "")
        parent_path = str(node.get("parent_path") or "")

        if w <= 0 or h <= 0:
            continue

        region_key = _guess_region_key(depth, role)
        atomic_profile_name = _guess_atomic_profile_name(depth, role, name, text)
        role_slug = re.sub(r"[^a-z0-9]+", "_", role.lower()).strip("_") or "node"
        control_uid = f"atspi_{source}_{depth}_{role_slug}_{idx+1:04d}"

        existing = session.exec(
            select(WechatUIControlDefinition).where(
                WechatUIControlDefinition.profile_id == int(payload.profile_id),
                WechatUIControlDefinition.control_uid == control_uid,
            )
        ).first()
        row = existing or WechatUIControlDefinition(control_uid=control_uid, profile_id=int(payload.profile_id))

        row.enabled = True
        row.region_key = region_key
        row.role = role
        row.control_type = role
        row.depth = depth
        row.depth_code = f"{depth:02d}"
        row.access_path = path
        row.path_numeric_code = path
        row.x = x
        row.y = y
        row.width = w
        row.height = h
        row.text = text
        row.window_type = "chat"
        row.actions_json = _json_dumps(["click"])
        row.is_clickable = True
        row.has_post_click_change = source in {"popup"}
        row.source_type = "atomic_container"
        row.source_ref_id = parent_path or path
        row.confidence = 0.92
        row.meta_json = _json_dumps(
            {
                "atomic_source": source,
                "atomic_profile_name": atomic_profile_name,
                "parent_path": parent_path,
                "container_key": str(node.get("container_key") or ""),
            }
        )
        row.updated_at = datetime.utcnow()

        session.add(row)
        generated.append(
            {
                "control_uid": control_uid,
                "text": text,
                "role": role,
                "depth": depth,
                "region_key": region_key,
                "atomic_profile_name": atomic_profile_name,
            }
        )

    session.commit()
    return {
        "success": True,
        "generated": len(generated),
        "items": generated,
        "source": source,
    }


@router.post("/ui/control_snapshots/save")
async def save_control_snapshot(payload: SnapshotSavePayload, session: Session = Depends(get_session)):
    profile = session.get(WechatUIProfile, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile不存在")

    batch_id = payload.capture_batch_id.strip() or f"snap_{int(datetime.utcnow().timestamp())}"
    saved = 0
    for node in payload.nodes:
        bounds = node.get("bounds") or {}
        row = WechatUIControlSnapshot(
            profile_id=payload.profile_id,
            capture_batch_id=batch_id,
            source_type=payload.source_type,
            region_key=str(node.get("region_key") or ""),
            role=str(node.get("role") or ""),
            depth=int(node.get("depth", 0) or 0),
            access_path=str(node.get("access_path") or node.get("path") or ""),
            path_numeric_code=str(node.get("path_numeric_code") or ""),
            x=int(bounds.get("x", node.get("x", 0)) or 0),
            y=int(bounds.get("y", node.get("y", 0)) or 0),
            width=int(bounds.get("width", node.get("width", 0)) or 0),
            height=int(bounds.get("height", node.get("height", 0)) or 0),
            text=str(node.get("text") or node.get("name") or ""),
            ocr_text=str(node.get("ocr_text") or ""),
            raw_json=_json_dumps(node),
        )
        session.add(row)
        saved += 1

    session.commit()
    return {"success": True, "capture_batch_id": batch_id, "saved": saved}


@router.post("/ops/packages/upsert")
async def upsert_operation_package(payload: PackageUpsertPayload, session: Session = Depends(get_session)):
    row: Optional[WechatOperationPackage] = None
    if payload.id:
        row = session.get(WechatOperationPackage, payload.id)
    if not row:
        row = session.exec(
            select(WechatOperationPackage).where(WechatOperationPackage.package_code == payload.package_code)
        ).first()

    if not row:
        row = WechatOperationPackage(package_code=payload.package_code)

    row.package_name = payload.package_name
    row.enabled = payload.enabled
    row.scene_type = payload.scene_type
    row.profile_id = payload.profile_id
    row.description = payload.description
    row.version = payload.version
    row.config_json = _json_dumps(payload.config)
    row.updated_at = datetime.utcnow()

    session.add(row)
    session.commit()
    session.refresh(row)

    return {"success": True, "package_id": row.id}


@router.get("/ops/packages/default_actions")
async def get_default_operation_actions():
    return {
        "success": True,
        "items": [
            {"action_key": "monitor_new_message", "action_name": "监控新消息", "action_type": "listen.next"},
            {"action_key": "read_new_message", "action_name": "读取新消息内容", "action_type": "chat.messages"},
            {"action_key": "ai_parse_new_message", "action_name": "新消息AI解读设置", "action_type": "llm.core"},
            {"action_key": "input_reply_message", "action_name": "输入回复消息", "action_type": "ui.input"},
            {"action_key": "send_message", "action_name": "发消息", "action_type": "chat.send_text"},
            {"action_key": "read_history_message", "action_name": "读历史消息", "action_type": "chat.history"},
            {"action_key": "ai_summary_history", "action_name": "历史消息AI总结", "action_type": "crm.summary"},
            {"action_key": "update_user_tags", "action_name": "用户标签更新", "action_type": "crm.tags"},
        ],
    }


@router.get("/ops/packages")
async def list_operation_packages(enabled_only: bool = False, session: Session = Depends(get_session)):
    stmt = select(WechatOperationPackage).order_by(WechatOperationPackage.updated_at.desc())
    if enabled_only:
        stmt = stmt.where(WechatOperationPackage.enabled == True)

    rows = session.exec(stmt).all()
    return {
        "success": True,
        "items": [
            {
                "id": row.id,
                "package_code": row.package_code,
                "package_name": row.package_name,
                "enabled": row.enabled,
                "scene_type": row.scene_type,
                "profile_id": row.profile_id,
                "description": row.description,
                "version": row.version,
                "config": _json_loads(row.config_json, {}),
                "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            }
            for row in rows
        ],
    }


@router.post("/ops/packages/actions/upsert_batch")
async def upsert_operation_actions(payload: ActionBatchUpsertPayload, session: Session = Depends(get_session)):
    package = session.get(WechatOperationPackage, payload.package_id)
    if not package:
        raise HTTPException(status_code=404, detail="package不存在")

    affected = 0
    for idx, action in enumerate(payload.actions):
        action_key = str(action.get("action_key") or "").strip()
        if not action_key:
            continue

        row = session.exec(
            select(WechatOperationAction).where(
                WechatOperationAction.package_id == payload.package_id,
                WechatOperationAction.action_key == action_key,
            )
        ).first()

        if not row:
            row = WechatOperationAction(package_id=payload.package_id, action_key=action_key)

        row.action_name = str(action.get("action_name") or action_key)
        row.action_type = str(action.get("action_type") or "")
        row.enabled = bool(action.get("enabled", True))
        row.step_order = int(action.get("step_order", idx) or idx)
        row.control_uid = str(action.get("control_uid") or "")
        row.api_route = str(action.get("api_route") or "")
        row.llm_scene = str(action.get("llm_scene") or "")
        row.db_hook = str(action.get("db_hook") or "")
        row.params_json = _json_dumps(action.get("params") or {})
        row.expected_json = _json_dumps(action.get("expected") or {})
        row.on_fail_action = str(action.get("on_fail_action") or "")
        row.updated_at = datetime.utcnow()

        session.add(row)
        affected += 1

    session.commit()
    return {"success": True, "affected": affected}


@router.get("/ops/packages/actions")
async def list_operation_actions(package_id: int, session: Session = Depends(get_session)):
    rows = session.exec(
        select(WechatOperationAction)
        .where(WechatOperationAction.package_id == package_id)
        .order_by(WechatOperationAction.step_order.asc(), WechatOperationAction.id.asc())
    ).all()

    return {
        "success": True,
        "items": [
            {
                "id": row.id,
                "action_key": row.action_key,
                "action_name": row.action_name,
                "action_type": row.action_type,
                "enabled": row.enabled,
                "step_order": row.step_order,
                "control_uid": row.control_uid,
                "api_route": row.api_route,
                "llm_scene": row.llm_scene,
                "db_hook": row.db_hook,
                "params": _json_loads(row.params_json, {}),
                "expected": _json_loads(row.expected_json, {}),
                "on_fail_action": row.on_fail_action,
                "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            }
            for row in rows
        ],
    }


@router.post("/chat/runtime/upsert")
async def upsert_chat_runtime(payload: RuntimeUpsertPayload, session: Session = Depends(get_session)):
    row = session.exec(
        select(WechatChatRuntime).where(
            WechatChatRuntime.session_id == payload.session_id,
            WechatChatRuntime.chat_name == payload.chat_name,
            WechatChatRuntime.msg_id == payload.msg_id,
        )
    ).first()

    if not row:
        row = WechatChatRuntime(
            session_id=payload.session_id,
            chat_name=payload.chat_name,
            msg_id=payload.msg_id,
        )

    row.msg_type = payload.msg_type
    row.sender = payload.sender
    row.content = payload.content
    row.content_json = _json_dumps(payload.content_json)
    row.acked = payload.acked
    row.created_at = datetime.utcnow()

    session.add(row)
    session.commit()
    session.refresh(row)

    return {"success": True, "id": row.id}


@router.get("/chat/runtime/list")
async def list_chat_runtime(
    session_id: Optional[str] = None,
    chat_name: Optional[str] = None,
    acked: Optional[bool] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    session: Session = Depends(get_session),
):
    stmt = select(WechatChatRuntime)
    if session_id:
        stmt = stmt.where(WechatChatRuntime.session_id == session_id)
    if chat_name:
        stmt = stmt.where(WechatChatRuntime.chat_name == chat_name)
    if acked is not None:
        stmt = stmt.where(WechatChatRuntime.acked == acked)

    rows = session.exec(stmt.order_by(WechatChatRuntime.created_at.desc()).limit(limit)).all()
    return {
        "success": True,
        "items": [
            {
                "id": row.id,
                "session_id": row.session_id,
                "chat_name": row.chat_name,
                "msg_id": row.msg_id,
                "msg_type": row.msg_type,
                "sender": row.sender,
                "content": row.content,
                "content_json": _json_loads(row.content_json, {}),
                "acked": row.acked,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


@router.post("/chat/runtime/flush_to_history")
async def flush_runtime_to_history(payload: RuntimeFlushPayload, session: Session = Depends(get_session)):
    stmt = select(WechatChatRuntime)
    if payload.session_id:
        stmt = stmt.where(WechatChatRuntime.session_id == payload.session_id)

    runtime_rows = session.exec(stmt.order_by(WechatChatRuntime.created_at.asc())).all()

    imported = 0
    skipped = 0
    for row in runtime_rows:
        msg_id = row.msg_id or f"rt_{row.id}"
        exists = session.exec(
            select(WechatChatHistory).where(
                WechatChatHistory.customer_id == payload.customer_id,
                WechatChatHistory.msg_id == msg_id,
            )
        ).first()
        if exists:
            skipped += 1
            continue

        session.add(
            WechatChatHistory(
                customer_id=payload.customer_id,
                session_id=row.session_id,
                msg_id=msg_id,
                msg_type=row.msg_type,
                sender=row.sender,
                content_raw=row.content,
                content_text=row.content,
                content_json=row.content_json,
                send_time=row.created_at or datetime.utcnow(),
            )
        )
        imported += 1

    if payload.clear_after_flush and runtime_rows:
        for row in runtime_rows:
            session.delete(row)

    session.commit()
    return {
        "success": True,
        "imported": imported,
        "skipped": skipped,
        "cleared": bool(payload.clear_after_flush),
    }


@router.post("/listen/state/upsert")
async def upsert_listen_state(payload: ListenStateUpsertPayload, session: Session = Depends(get_session)):
    row = session.exec(
        select(WechatListenState).where(WechatListenState.listener_key == payload.listener_key)
    ).first()

    if not row:
        row = WechatListenState(listener_key=payload.listener_key)

    row.running = payload.running
    row.chats_json = _json_dumps(payload.chats)
    row.last_msg_id = payload.last_msg_id
    row.last_poll_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()

    session.add(row)
    session.commit()
    session.refresh(row)

    return {"success": True, "id": row.id}


@router.get("/listen/state")
async def get_listen_state(listener_key: str = "default", session: Session = Depends(get_session)):
    row = session.exec(
        select(WechatListenState).where(WechatListenState.listener_key == listener_key)
    ).first()

    if not row:
        return {
            "success": True,
            "state": {
                "listener_key": listener_key,
                "running": False,
                "chats": [],
                "last_msg_id": "",
                "last_poll_at": "",
            },
        }

    return {
        "success": True,
        "state": {
            "listener_key": row.listener_key,
            "running": row.running,
            "chats": _json_loads(row.chats_json, []),
            "last_msg_id": row.last_msg_id,
            "last_poll_at": row.last_poll_at.isoformat() if row.last_poll_at else "",
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        },
    }


@router.get("/ops/action_types")
async def list_operation_action_types():
    return {
        "success": True,
        "items": [
            {
                "action_type": "chat.send_text",
                "label": "发送消息(聚焦输入->输入->点击发送)",
                "params_schema": {
                    "text": "{{message}}",
                    "input_bounds": {"x": 0, "y": 0, "width": 0, "height": 0},
                    "send_bounds": {"x": 0, "y": 0, "width": 0, "height": 0},
                },
            },
            {
                "action_type": "ui.click_bounds",
                "label": "点击控件区域",
                "params_schema": {
                    "bounds": {"x": 0, "y": 0, "width": 0, "height": 0},
                    "control_uid": "",
                },
            },
            {
                "action_type": "ui.input_text",
                "label": "拟人输入文本",
                "params_schema": {"text": "{{message}}"},
            },
            {
                "action_type": "wait.ms",
                "label": "等待毫秒",
                "params_schema": {"ms": 500},
            },
            {
                "action_type": "atspi.extract_contacts_unread",
                "label": "读取联系人与未读数(depth=15,list item)",
                "params_schema": {},
            },
            {
                "action_type": "atspi.extract_chat_messages",
                "label": "读取当前聊天消息(depth=14,list item)",
                "params_schema": {},
            },
            {
                "action_type": "flow.if",
                "label": "条件分支(命中则跳转then_action_key，否则else_action_key)",
                "params_schema": {
                    "var": "unread_count",
                    "op": ">",
                    "value": 0,
                    "then_action_key": "ai_parse_new_message",
                    "else_action_key": "",
                },
            },
        ],
    }


@router.get("/ops/env/check")
async def check_operation_environment():
    return _build_ops_env_status()


@router.get("/ops/packages/export_yaml")
async def export_operation_package_yaml(
    package_id: Optional[int] = None,
    package_code: Optional[str] = None,
    session: Session = Depends(get_session),
):
    if yaml is None:
        raise HTTPException(status_code=500, detail="缺少PyYAML依赖，请安装 pyyaml")

    package: Optional[WechatOperationPackage] = None
    if package_id:
        package = session.get(WechatOperationPackage, int(package_id))
    elif package_code:
        package = session.exec(
            select(WechatOperationPackage).where(WechatOperationPackage.package_code == str(package_code))
        ).first()

    if not package:
        raise HTTPException(status_code=404, detail="package不存在")

    actions = session.exec(
        select(WechatOperationAction)
        .where(WechatOperationAction.package_id == int(package.id))
        .order_by(WechatOperationAction.step_order.asc(), WechatOperationAction.id.asc())
    ).all()

    doc = {
        "package": {
            "id": package.id,
            "package_code": package.package_code,
            "package_name": package.package_name,
            "enabled": package.enabled,
            "scene_type": package.scene_type,
            "profile_id": package.profile_id,
            "description": package.description,
            "version": package.version,
            "config": _json_loads(package.config_json, {}),
        },
        "actions": [
            {
                "action_key": row.action_key,
                "action_name": row.action_name,
                "action_type": row.action_type,
                "enabled": row.enabled,
                "step_order": row.step_order,
                "control_uid": row.control_uid,
                "api_route": row.api_route,
                "llm_scene": row.llm_scene,
                "db_hook": row.db_hook,
                "params": _json_loads(row.params_json, {}),
                "expected": _json_loads(row.expected_json, {}),
                "on_fail_action": row.on_fail_action,
            }
            for row in actions
        ],
    }

    yaml_text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
    return {
        "success": True,
        "package_id": package.id,
        "package_code": package.package_code,
        "yaml_text": yaml_text,
    }


@router.post("/ops/packages/import_yaml")
async def import_operation_package_yaml(payload: PackageYamlImportPayload, session: Session = Depends(get_session)):
    if yaml is None:
        raise HTTPException(status_code=500, detail="缺少PyYAML依赖，请安装 pyyaml")

    raw = str(payload.yaml_text or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="yaml_text为空")

    try:
        doc = yaml.safe_load(raw) or {}
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"YAML解析失败: {err}")

    package_data = doc.get("package") or {}
    actions_data = doc.get("actions") or []
    package_code = str(package_data.get("package_code") or "").strip()
    if not package_code:
        raise HTTPException(status_code=400, detail="package.package_code不能为空")

    package = session.exec(
        select(WechatOperationPackage).where(WechatOperationPackage.package_code == package_code)
    ).first()
    if package and not payload.upsert:
        raise HTTPException(status_code=409, detail="package已存在，upsert=false")
    if not package:
        package = WechatOperationPackage(package_code=package_code)

    package.package_name = str(package_data.get("package_name") or package_code)
    package.enabled = bool(package_data.get("enabled", True))
    package.scene_type = str(package_data.get("scene_type") or "chat")
    package.profile_id = package_data.get("profile_id")
    package.description = str(package_data.get("description") or "")
    package.version = str(package_data.get("version") or "v1")
    package.config_json = _json_dumps(package_data.get("config") or {})
    package.updated_at = datetime.utcnow()
    session.add(package)
    session.commit()
    session.refresh(package)

    affected = 0
    for idx, action in enumerate(actions_data):
        action_key = str(action.get("action_key") or "").strip()
        if not action_key:
            continue
        row = session.exec(
            select(WechatOperationAction).where(
                WechatOperationAction.package_id == int(package.id),
                WechatOperationAction.action_key == action_key,
            )
        ).first()
        if not row:
            row = WechatOperationAction(package_id=int(package.id), action_key=action_key)

        row.action_name = str(action.get("action_name") or action_key)
        row.action_type = str(action.get("action_type") or "")
        row.enabled = bool(action.get("enabled", True))
        row.step_order = int(action.get("step_order", idx) or idx)
        row.control_uid = str(action.get("control_uid") or "")
        row.api_route = str(action.get("api_route") or "")
        row.llm_scene = str(action.get("llm_scene") or "")
        row.db_hook = str(action.get("db_hook") or "")
        row.params_json = _json_dumps(action.get("params") or {})
        row.expected_json = _json_dumps(action.get("expected") or {})
        row.on_fail_action = str(action.get("on_fail_action") or "")
        row.updated_at = datetime.utcnow()
        session.add(row)
        affected += 1

    session.commit()
    return {
        "success": True,
        "package_id": package.id,
        "package_code": package.package_code,
        "affected_actions": affected,
    }


@router.post("/ops/packages/execute")
async def execute_operation_package(payload: PackageExecutePayload, session: Session = Depends(get_session)):
    package: Optional[WechatOperationPackage] = None
    if payload.package_id:
        package = session.get(WechatOperationPackage, int(payload.package_id))
    elif payload.package_code:
        package = session.exec(
            select(WechatOperationPackage).where(WechatOperationPackage.package_code == str(payload.package_code))
        ).first()

    if not package:
        raise HTTPException(status_code=404, detail="package不存在")

    actions = session.exec(
        select(WechatOperationAction)
        .where(WechatOperationAction.package_id == int(package.id), WechatOperationAction.enabled == True)
        .order_by(WechatOperationAction.step_order.asc(), WechatOperationAction.id.asc())
    ).all()
    if not actions:
        raise HTTPException(status_code=400, detail="package下没有可执行动作")

    from .rpa_compatibility import get_wechat_manager, rpa_available

    if not payload.dry_run and not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    manager = get_wechat_manager() if not payload.dry_run else None
    run_id = f"oprun_{uuid.uuid4().hex[:10]}"
    ctx_vars: Dict[str, Any] = dict(payload.variables or {})
    results: List[Dict[str, Any]] = []
    started = time.perf_counter()
    success = True
    error_message = ""

    action_index_by_key = {
        str(action.action_key or "").strip(): idx
        for idx, action in enumerate(actions)
        if str(action.action_key or "").strip()
    }

    cursor = 0
    loop_guard = 0
    max_loops = max(200, len(actions) * 10)

    while 0 <= cursor < len(actions):
        loop_guard += 1
        if loop_guard > max_loops:
            success = False
            error_message = "执行中检测到可能的循环跳转，已中止"
            break

        action = actions[cursor]
        step_started = time.perf_counter()
        step_result: Dict[str, Any]
        try:
            if str(action.action_type or "").strip().lower() == "flow.if":
                branch_params = _render_payload(_json_loads(action.params_json, {}), ctx_vars)
                branch_eval = _evaluate_condition(branch_params, ctx_vars)
                then_key = str(branch_params.get("then_action_key") or "").strip()
                else_key = str(branch_params.get("else_action_key") or "").strip()
                target_key = then_key if branch_eval["result"] else else_key
                jump_to_index = action_index_by_key.get(target_key)
                if target_key and jump_to_index is None:
                    step_result = {
                        "success": False,
                        "message": f"分支跳转目标不存在: {target_key}",
                        "branch": branch_eval,
                    }
                else:
                    step_result = {
                        "success": True,
                        "branch": branch_eval,
                        "jump_to_action_key": target_key,
                        "jumped": jump_to_index is not None,
                    }
                    cursor = jump_to_index if jump_to_index is not None else cursor + 1
            else:
                step_result = await _execute_action(
                    action=action,
                    package=package,
                    manager=manager,
                    variables=ctx_vars,
                    session=session,
                    dry_run=bool(payload.dry_run),
                )
                cursor += 1
        except Exception as err:
            step_result = {"success": False, "error": str(err)}
            cursor += 1

        elapsed_ms = int((time.perf_counter() - step_started) * 1000)
        step_success = bool(step_result.get("success", False))
        log_row = WechatOperationRunLog(
            package_id=package.id,
            action_id=action.id,
            run_id=run_id,
            success=step_success,
            request_json=_json_dumps({"variables": ctx_vars, "dry_run": payload.dry_run}),
            response_json=_json_dumps(step_result),
            error_message=str(step_result.get("error") or step_result.get("message") or "") if not step_success else "",
            elapsed_ms=elapsed_ms,
            created_at=datetime.utcnow(),
        )
        session.add(log_row)

        results.append(
            {
                "action_id": action.id,
                "action_key": action.action_key,
                "action_name": action.action_name,
                "action_type": action.action_type,
                "success": step_success,
                "elapsed_ms": elapsed_ms,
                "result": step_result,
            }
        )

        if not step_success:
            success = False
            error_message = str(step_result.get("error") or step_result.get("message") or "执行失败")
            break

        human_pause_ms = _apply_humanized_step_pause(action, ctx_vars, bool(payload.dry_run))
        if human_pause_ms > 0:
            step_result["human_pause_ms"] = human_pause_ms

    session.commit()

    total_ms = int((time.perf_counter() - started) * 1000)
    return {
        "success": success,
        "run_id": run_id,
        "package_id": package.id,
        "package_code": package.package_code,
        "dry_run": bool(payload.dry_run),
        "elapsed_ms": total_ms,
        "error_message": error_message,
        "variables": ctx_vars,
        "steps": results,
    }


@router.post("/ops/run_logs")
async def create_operation_run_log(payload: Dict[str, Any], session: Session = Depends(get_session)):
    row = WechatOperationRunLog(
        package_id=payload.get("package_id"),
        action_id=payload.get("action_id"),
        run_id=str(payload.get("run_id") or ""),
        success=bool(payload.get("success", True)),
        request_json=_json_dumps(payload.get("request") or {}),
        response_json=_json_dumps(payload.get("response") or {}),
        error_message=str(payload.get("error_message") or ""),
        elapsed_ms=int(payload.get("elapsed_ms", 0) or 0),
        created_at=datetime.utcnow(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"success": True, "id": row.id}


@router.get("/ops/run_logs")
async def list_operation_run_logs(
    package_id: Optional[int] = None,
    run_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    session: Session = Depends(get_session),
):
    stmt = select(WechatOperationRunLog)
    if package_id is not None:
        stmt = stmt.where(WechatOperationRunLog.package_id == package_id)
    if run_id:
        stmt = stmt.where(WechatOperationRunLog.run_id == run_id)

    rows = session.exec(stmt.order_by(WechatOperationRunLog.created_at.desc()).limit(limit)).all()
    return {
        "success": True,
        "items": [
            {
                "id": row.id,
                "package_id": row.package_id,
                "action_id": row.action_id,
                "run_id": row.run_id,
                "success": row.success,
                "request": _json_loads(row.request_json, {}),
                "response": _json_loads(row.response_json, {}),
                "error_message": row.error_message,
                "elapsed_ms": row.elapsed_ms,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }
