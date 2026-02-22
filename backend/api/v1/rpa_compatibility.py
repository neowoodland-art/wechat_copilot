from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List, Tuple
import logging
import sys
import os
import random
import time
import subprocess
import statistics
import threading
import uuid
from pydantic import BaseModel
import base64
import json
from datetime import datetime

import cv2
import numpy as np
import re

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

router = APIRouter(prefix="/rpa", tags=["rpa_compatibility"])

PROFILE_STORE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/ui_analysis_profiles.json")
)

SCAN_TASKS: Dict[str, Dict[str, Any]] = {}
SCAN_TASKS_LOCK = threading.Lock()
MANUAL_SCAN_SESSIONS: Dict[str, Dict[str, Any]] = {}
MANUAL_SCAN_SESSIONS_LOCK = threading.Lock()


class ScanCancelledError(Exception):
    pass


def _create_scan_task_state(task_id: str, request: "FullScanRequest") -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "stage": "queued",
        "message": "扫描任务已创建，等待执行",
        "cancel_requested": False,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
        "request": request.model_dump(),
        "result": None,
        "error": None,
    }


def _update_scan_task(task_id: str, **fields: Any) -> None:
    with SCAN_TASKS_LOCK:
        task = SCAN_TASKS.get(task_id)
        if not task:
            return
        task.update(fields)


def _get_scan_task(task_id: str) -> Optional[Dict[str, Any]]:
    with SCAN_TASKS_LOCK:
        task = SCAN_TASKS.get(task_id)
        if not task:
            return None
        return dict(task)


def _mark_scan_task_cancel_requested(task_id: str) -> bool:
    with SCAN_TASKS_LOCK:
        task = SCAN_TASKS.get(task_id)
        if not task:
            return False
        task["cancel_requested"] = True
        if task.get("status") == "queued":
            task["status"] = "cancelled"
            task["stage"] = "cancelled"
            task["message"] = "扫描任务已取消"
            task["finished_at"] = datetime.now().isoformat()
        return True


def _is_scan_task_cancel_requested(task_id: str) -> bool:
    with SCAN_TASKS_LOCK:
        task = SCAN_TASKS.get(task_id)
        return bool(task and task.get("cancel_requested"))


def _ensure_profile_store_exists() -> None:
    os.makedirs(os.path.dirname(PROFILE_STORE_PATH), exist_ok=True)
    if not os.path.exists(PROFILE_STORE_PATH):
        seed_data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "profiles": {}
        }
        with open(PROFILE_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(seed_data, f, ensure_ascii=False, indent=2)


def _load_profile_store() -> Dict[str, Any]:
    _ensure_profile_store_exists()
    with open(PROFILE_STORE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        data = {}
    if "profiles" not in data or not isinstance(data.get("profiles"), dict):
        data["profiles"] = {}
    data.setdefault("version", "1.0")
    data.setdefault("updated_at", datetime.now().isoformat())
    
    # 迁移现有profiles以支持新结构
    _migrate_profiles(data["profiles"])
    
    return data


def _migrate_profiles(profiles: Dict[str, Any]) -> None:
    """迁移现有profiles以支持regions和template_type"""
    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
            
        # 添加template_type如果不存在
        if "template_type" not in profile:
            profile["template_type"] = "chat"  # 默认聊天界面
            
        # 添加regions如果不存在
        if "regions" not in profile:
            window_lock = profile.get("window_lock", {})
            width = window_lock.get("width", 980)
            height = window_lock.get("height", 1025)
            # 使用默认的5区域估算
            profile["regions"] = _estimate_region_bounds({
                "width": width,
                "height": height,
                "x": window_lock.get("x", 0),
                "y": window_lock.get("y", 0)
            }, profile["template_type"])
            
        # 确保layers存在
        if "layers" not in profile:
            profile["layers"] = {
                "base_scan_layer": profile.get("base_scan_layer", []),
                "annotation_layer": profile.get("annotation_layer", []),
                "control_layer": profile.get("control_layer", []),
                "geometry_layer": profile.get("geometry_layer", []),
            }
            
        # 确保execution存在
        if "execution" not in profile:
            profile["execution"] = {
                "rescan_region_ids": [],
                "rescan_required_on_click": False,
            }
            
        # 确保stable_elements存在
        if "stable_elements" not in profile:
            profile["stable_elements"] = profile.get("annotation_layer", [])


def _save_profile_store(store: Dict[str, Any]) -> None:
    store["updated_at"] = datetime.now().isoformat()
    _ensure_profile_store_exists()
    with open(PROFILE_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _safe_window_info(window_info: Any) -> Dict[str, Any]:
    return {
        "id": int(getattr(window_info, "id", 0)),
        "title": str(getattr(window_info, "title", "")),
        "x": int(getattr(window_info, "x", 0)),
        "y": int(getattr(window_info, "y", 0)),
        "width": int(getattr(window_info, "width", 0)),
        "height": int(getattr(window_info, "height", 0)),
        "is_active": bool(getattr(window_info, "is_active", False)),
    }


def _is_window_locked(current: Dict[str, Any], expected: Dict[str, int], tolerance: int) -> bool:
    return (
        abs(int(current.get("x", 0)) - int(expected.get("x", 0))) <= tolerance
        and abs(int(current.get("y", 0)) - int(expected.get("y", 0))) <= tolerance
        and abs(int(current.get("width", 0)) - int(expected.get("width", 0))) <= tolerance
        and abs(int(current.get("height", 0)) - int(expected.get("height", 0))) <= tolerance
    )


def _force_set_window_geometry_x11(window_id: int, x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    """使用wmctrl + xdotool强制设置窗口几何（去最大化后再定位），用于窗口固定兜底。"""
    trace: List[Dict[str, Any]] = []
    wid_hex = hex(int(window_id))
    wid_dec = str(int(window_id))

    def run_cmd(cmd: List[str], timeout_sec: int = 3) -> Dict[str, Any]:
        try:
            ret = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
            result = {
                "cmd": " ".join(cmd),
                "returncode": ret.returncode,
                "stdout": (ret.stdout or "").strip(),
                "stderr": (ret.stderr or "").strip(),
                "ok": ret.returncode == 0,
            }
            trace.append(result)
            return result
        except Exception as err:
            result = {
                "cmd": " ".join(cmd),
                "returncode": -1,
                "stdout": "",
                "stderr": str(err),
                "ok": False,
            }
            trace.append(result)
            return result

    run_cmd(["wmctrl", "-i", "-r", wid_hex, "-b", "remove,maximized_vert,maximized_horz"], 3)
    run_cmd(["wmctrl", "-i", "-r", wid_hex, "-e", f"0,{x},{y},{width},{height}"], 3)
    run_cmd(["xdotool", "windowsize", "--sync", wid_dec, str(width), str(height)], 3)
    run_cmd(["xdotool", "windowmove", "--sync", wid_dec, str(x), str(y)], 3)
    run_cmd(["xdotool", "windowactivate", "--sync", wid_dec], 3)

    success = any(item.get("ok") for item in trace)
    return {"success": success, "trace": trace}


def _normalize_bounds(bounds: Dict[str, Any]) -> Dict[str, int]:
    x = int(bounds.get("x", 0))
    y = int(bounds.get("y", 0))
    width = int(bounds.get("width", 0))
    height = int(bounds.get("height", 0))
    return {"x": x, "y": y, "width": width, "height": height}


def _collect_mouse_scan_layer(manager: Any, timeout_seconds: int) -> List[Dict[str, Any]]:
    elements: List[Any] = []

    try:
        if hasattr(manager, "scan_interface_by_mouse_with_timeout"):
            elements = manager.scan_interface_by_mouse_with_timeout(int(timeout_seconds))
        elif hasattr(manager, "scan_interface_by_mouse_simple"):
            elements = manager.scan_interface_by_mouse_simple()
        elif hasattr(manager, "scan_interface_by_mouse"):
            elements = manager.scan_interface_by_mouse()
    except Exception as e:
        logger.warning(f"鼠标扫描层获取失败: {e}")
        elements = []

    normalized: List[Dict[str, Any]] = []
    for index, elem in enumerate(elements):
        x = int(getattr(elem, "x", 0))
        y = int(getattr(elem, "y", 0))
        width = int(getattr(elem, "width", 0))
        height = int(getattr(elem, "height", 0))
        if width <= 0 or height <= 0:
            continue

        normalized.append({
            "id": f"hover_{index}",
            "name": f"hover_region_{index}",
            "source": "mouse_hover_scan",
            "clickable_candidate": True,
            "bounds": {"x": x, "y": y, "width": width, "height": height}
        })

    return normalized


def _capture_scan_image(manager: Any) -> np.ndarray:
    if hasattr(manager, "capture_full_window"):
        return _ensure_image_ndarray(manager.capture_full_window())
    return _ensure_image_ndarray(manager.capture_message_area())


def _merge_rectangles(rects: List[Dict[str, int]], padding: int = 6) -> List[Dict[str, int]]:
    if not rects:
        return []

    merged = []
    for rect in rects:
        x1 = rect["x"]
        y1 = rect["y"]
        x2 = rect["x"] + rect["width"]
        y2 = rect["y"] + rect["height"]

        absorbed = False
        for target in merged:
            tx1 = target["x"] - padding
            ty1 = target["y"] - padding
            tx2 = target["x"] + target["width"] + padding
            ty2 = target["y"] + target["height"] + padding

            overlaps = not (x2 < tx1 or x1 > tx2 or y2 < ty1 or y1 > ty2)
            if overlaps:
                nx1 = min(target["x"], x1)
                ny1 = min(target["y"], y1)
                nx2 = max(target["x"] + target["width"], x2)
                ny2 = max(target["y"] + target["height"], y2)
                target["x"] = nx1
                target["y"] = ny1
                target["width"] = nx2 - nx1
                target["height"] = ny2 - ny1
                absorbed = True
                break

        if not absorbed:
            merged.append({
                "x": x1,
                "y": y1,
                "width": rect["width"],
                "height": rect["height"],
            })

    return merged


def _rect_iou(a: Dict[str, int], b: Dict[str, int]) -> float:
    ax1 = int(a.get("x", 0))
    ay1 = int(a.get("y", 0))
    ax2 = ax1 + int(a.get("width", 0))
    ay2 = ay1 + int(a.get("height", 0))

    bx1 = int(b.get("x", 0))
    by1 = int(b.get("y", 0))
    bx2 = bx1 + int(b.get("width", 0))
    by2 = by1 + int(b.get("height", 0))

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    denom = area_a + area_b - inter
    if denom <= 0:
        return 0.0
    return float(inter) / float(denom)


def _rect_union(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    ax1 = int(a.get("x", 0))
    ay1 = int(a.get("y", 0))
    ax2 = ax1 + int(a.get("width", 0))
    ay2 = ay1 + int(a.get("height", 0))

    bx1 = int(b.get("x", 0))
    by1 = int(b.get("y", 0))
    bx2 = bx1 + int(b.get("width", 0))
    by2 = by1 + int(b.get("height", 0))

    ux1 = min(ax1, bx1)
    uy1 = min(ay1, by1)
    ux2 = max(ax2, bx2)
    uy2 = max(ay2, by2)

    return {
        "x": int(ux1),
        "y": int(uy1),
        "width": int(max(0, ux2 - ux1)),
        "height": int(max(0, uy2 - uy1)),
    }


REGION_DEFAULT_ACTIONS = {
    "main_menu": "activate_panel",
    "contact_list": "select_contact",
    "chat_display": "view_or_open_message",
    "chat_input": "input_or_send",
    "search_bar": "search_or_quick_action",
}


def _normalize_region_bounds_for_window(bounds: Dict[str, Any], window_info: Dict[str, Any]) -> Optional[Dict[str, int]]:
    if not isinstance(bounds, dict):
        return None

    wx = int(window_info.get("x", 0))
    wy = int(window_info.get("y", 0))
    ww = max(1, int(window_info.get("width", 1)))
    wh = max(1, int(window_info.get("height", 1)))

    x = int(bounds.get("x", 0) or 0)
    y = int(bounds.get("y", 0) or 0)
    width = int(bounds.get("width", 0) or 0)
    height = int(bounds.get("height", 0) or 0)
    if width <= 0 or height <= 0:
        return None

    # 支持绝对坐标或窗口相对坐标
    if x >= wx and y >= wy and x <= wx + ww + 20 and y <= wy + wh + 20:
        x -= wx
        y -= wy

    x = max(0, min(ww - 1, x))
    y = max(0, min(wh - 1, y))
    width = max(1, min(ww - x, width))
    height = max(1, min(wh - y, height))

    return {
        "x": int(x),
        "y": int(y),
        "width": int(width),
        "height": int(height),
    }


def _load_regions_for_scan(profile_name: str, template_type: str, window_info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    regions = _estimate_region_bounds(window_info, template_type)
    try:
        store = _load_profile_store()
        profiles = store.get("profiles", {})
        lookup_names: List[str] = []

        normalized_profile_name = str(profile_name or "").strip()
        if normalized_profile_name:
            lookup_names.append(normalized_profile_name)

        if normalized_profile_name and not normalized_profile_name.endswith("_chat") and not normalized_profile_name.endswith("_contacts"):
            lookup_names.append(f"{normalized_profile_name}_{template_type}")

        if template_type in ["chat", "contacts"] and f"default_{template_type}" not in lookup_names:
            lookup_names.append(f"default_{template_type}")

        profile = None
        for name in lookup_names:
            maybe_profile = profiles.get(name)
            if isinstance(maybe_profile, dict):
                profile = maybe_profile
                break

        if isinstance(profile, dict):
            profile_regions = profile.get("regions", {})
            if isinstance(profile_regions, dict):
                merged = dict(regions)
                for region_id, region_value in profile_regions.items():
                    if not isinstance(region_value, dict):
                        continue
                    merged.setdefault(region_id, {})
                    merged[region_id]["name"] = str(region_value.get("name") or merged[region_id].get("name") or region_id)
                    if "function" in region_value:
                        merged[region_id]["function"] = region_value.get("function")
                    normalized = _normalize_region_bounds_for_window(region_value.get("bounds", {}), window_info)
                    if normalized:
                        merged[region_id]["bounds"] = normalized
                regions = merged
    except Exception as err:
        logger.warning(f"加载已保存区域配置失败，使用估算区域: {err}")
    return regions


def _generate_region_scan_points(region_id: str, bounds: Dict[str, int], step_x: int, step_y: int) -> List[Tuple[int, int]]:
    x0 = int(bounds.get("x", 0))
    y0 = int(bounds.get("y", 0))
    w = max(1, int(bounds.get("width", 1)))
    h = max(1, int(bounds.get("height", 1)))
    x1 = x0 + w
    y1 = y0 + h

    points: List[Tuple[int, int]] = []
    step_x = max(5, int(step_x))
    step_y = max(5, int(step_y))

    if region_id in ["main_menu", "contact_list"]:
        center_x = x0 + w // 2
        for y in range(y0 + 8, y1 - 8, max(20, step_y)):
            points.append((center_x, y))

    elif region_id == "chat_input":
        scan_y = min(y1 - 2, y0 + 15)
        for x in range(x0 + 6, x1 - 6, max(15, step_x)):
            points.append((x, scan_y))

    elif region_id == "chat_display":
        probe_x = max(x0 + 2, x1 - 20)
        probe_y = min(y1 - 2, y0 + 10)
        scrollbar_x = max(x0 + 1, x1 - 3)
        scrollbar_y = y0 + h // 2
        points.extend([(probe_x, probe_y), (scrollbar_x, scrollbar_y)])

    elif region_id == "search_bar":
        shrink_w = max(24, int(w * 0.7))
        shrink_h = max(18, int(h * 0.7))
        sx = x0 + (w - shrink_w) // 2
        sy = y0 + (h - shrink_h) // 2
        cy = sy + shrink_h // 2
        for x in range(sx + 4, sx + shrink_w - 4, max(15, step_x)):
            points.append((x, cy))

    else:
        for y in range(y0 + 6, y1 - 6, step_y):
            for x in range(x0 + 6, x1 - 6, step_x):
                points.append((x, y))

    if not points:
        points.append((x0 + w // 2, y0 + h // 2))
    return points


def _atspi_hover_name(manager: Any, abs_x: int, abs_y: int, radius: int = 90) -> Tuple[str, str]:
    if not hasattr(manager, "get_atspi_control_snapshot"):
        return "", ""
    try:
        controls = manager.get_atspi_control_snapshot(1000)
    except Exception:
        return "", ""

    best = None
    best_score = float("inf")
    for row in controls or []:
        x = int(row.get("x", 0) or 0)
        y = int(row.get("y", 0) or 0)
        w = int(row.get("width", 0) or 0)
        h = int(row.get("height", 0) or 0)
        if w <= 0 or h <= 0:
            continue
        cx = x + w // 2
        cy = y + h // 2
        dx = abs_x - cx
        dy = abs_y - cy
        dist = float(np.hypot(dx, dy))
        if dist > radius:
            continue
        if dist < best_score:
            best_score = dist
            best = row

    if not best:
        return "", ""
    return str(best.get("name", "") or ""), str(best.get("role", "") or "")


def _collect_mouse_scan_layer_by_regions(
    manager: Any,
    window_info: Dict[str, Any],
    regions: Dict[str, Dict[str, Any]],
    step_x: int,
    step_y: int,
    settle_ms: int,
    max_points: int,
    min_contour_area: int = 120,
    min_stable_hits: int = 1,
    progress_callback: Optional[Any] = None,
    should_cancel: Optional[Any] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    step_x = max(10, int(step_x))
    step_y = max(10, int(step_y))
    max_points = max(20, int(max_points))
    min_contour_area = max(30, int(min_contour_area))

    win_x = int(window_info.get("x", 0))
    win_y = int(window_info.get("y", 0))
    win_w = max(1, int(window_info.get("width", 1)))
    win_h = max(1, int(window_info.get("height", 1)))

    base = _capture_scan_image(manager)
    base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)

    points_scanned = 0
    ignored_noise = 0
    atspi_hits = 0
    send_button_action_clicked = False
    send_button_action_typed = False
    generated_candidates: List[Dict[str, Any]] = []
    region_debug: Dict[str, Dict[str, Any]] = {}

    def _progress(stage: str, message: str) -> None:
        if not progress_callback:
            return
        try:
            ratio = min(1.0, max(0.0, float(points_scanned) / float(max_points)))
            progress = int(15 + ratio * 65)
            progress_callback(progress=progress, stage=stage, message=message)
        except Exception:
            pass

    def _ensure_not_cancelled() -> None:
        if should_cancel and bool(should_cancel()):
            raise ScanCancelledError("扫描任务已取消")

    def _clip_rect(rect: Dict[str, int], region_rect: Dict[str, int]) -> Optional[Dict[str, int]]:
        rx = int(region_rect["x"])
        ry = int(region_rect["y"])
        rw = int(region_rect["width"])
        rh = int(region_rect["height"])

        x1 = max(rx, int(rect.get("x", 0)))
        y1 = max(ry, int(rect.get("y", 0)))
        x2 = min(rx + rw, x1 + int(rect.get("width", 0)))
        y2 = min(ry + rh, y1 + int(rect.get("height", 0)))
        if x2 <= x1 or y2 <= y1:
            return None
        return {
            "x": int(x1),
            "y": int(y1),
            "width": int(x2 - x1),
            "height": int(y2 - y1),
        }

    def _merge_region_candidates(items: List[Dict[str, Any]], iou_threshold: float = 0.35) -> List[Dict[str, Any]]:
        reduced: List[Dict[str, Any]] = []
        for item in items:
            matched_idx = -1
            for idx, ex in enumerate(reduced):
                if _rect_iou(ex["bounds"], item["bounds"]) >= iou_threshold:
                    matched_idx = idx
                    break
            if matched_idx < 0:
                reduced.append(item)
                continue

            reduced[matched_idx]["bounds"] = _rect_union(reduced[matched_idx]["bounds"], item["bounds"])
            reduced[matched_idx]["hover_hits"] = int(reduced[matched_idx].get("hover_hits", 1)) + int(item.get("hover_hits", 1))
            if not reduced[matched_idx].get("matched_atspi_name") and item.get("matched_atspi_name"):
                reduced[matched_idx]["matched_atspi_name"] = item.get("matched_atspi_name")
            if not reduced[matched_idx].get("matched_atspi_role") and item.get("matched_atspi_role"):
                reduced[matched_idx]["matched_atspi_role"] = item.get("matched_atspi_role")
        return reduced

    def _build_candidate(
        region_id: str,
        region_item: Dict[str, Any],
        name: str,
        control_type: str,
        bounds: Dict[str, int],
        source: str,
        hover_hits: int = 1,
        probe_abs_x: Optional[int] = None,
        probe_abs_y: Optional[int] = None,
    ) -> Dict[str, Any]:
        nonlocal atspi_hits
        matched_name = ""
        matched_role = ""
        if probe_abs_x is not None and probe_abs_y is not None:
            matched_name, matched_role = _atspi_hover_name(manager, abs_x=int(probe_abs_x), abs_y=int(probe_abs_y))
            if matched_name or matched_role:
                atspi_hits += 1

        candidate = {
            "id": "",
            "name": matched_name or name,
            "type": matched_role or control_type,
            "region_id": region_id,
            "ui_scene": str(region_item.get("name") or region_id),
            "function": REGION_DEFAULT_ACTIONS.get(region_id, "unknown_action"),
            "needs_rescan_after_click": region_id in ["chat_display", "chat_input"],
            "clickable_candidate": True,
            "source": source,
            "hover_hits": int(max(1, hover_hits)),
            "bounds": bounds,
            "matched_atspi_name": matched_name,
            "matched_atspi_role": matched_role,
        }
        return candidate

    def _extract_change_rects(
        region_bounds: Dict[str, int],
        probe_rel_x: int,
        probe_rel_y: int,
        settle_ms_local: int,
        diff_floor: int = 12,
        require_quad: bool = True,
    ) -> List[Dict[str, int]]:
        nonlocal points_scanned, ignored_noise

        _ensure_not_cancelled()

        if points_scanned >= max_points:
            return []

        abs_x = win_x + int(probe_rel_x)
        abs_y = win_y + int(probe_rel_y)
        move = subprocess.run(
            ["xdotool", "mousemove", "--sync", str(abs_x), str(abs_y)],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if move.returncode != 0:
            return []

        time.sleep(max(100, int(settle_ms_local)) / 1000.0)
        _ensure_not_cancelled()
        snap = _capture_scan_image(manager)
        snap_gray = cv2.cvtColor(snap, cv2.COLOR_BGR2GRAY)

        rx = int(region_bounds["x"])
        ry = int(region_bounds["y"])
        rw = int(region_bounds["width"])
        rh = int(region_bounds["height"])

        roi_base = base_gray[ry:ry + rh, rx:rx + rw]
        roi_snap = snap_gray[ry:ry + rh, rx:rx + rw]
        points_scanned += 1
        _progress("mouse_scan", f"鼠标扫描中 {points_scanned}/{max_points}")
        if roi_base.size == 0 or roi_snap.size == 0:
            return []

        diff = cv2.absdiff(roi_base, roi_snap)

        cursor_mask = np.ones_like(diff, dtype=np.uint8) * 255
        local_px = int(probe_rel_x - rx)
        local_py = int(probe_rel_y - ry)
        cv2.circle(cursor_mask, (local_px, local_py), 18, 0, -1)
        diff = cv2.bitwise_and(diff, cursor_mask)

        mean_val = float(np.mean(diff))
        std_val = float(np.std(diff))
        adaptive_threshold = int(max(diff_floor, min(96, mean_val + 1.5 * std_val)))
        _, binary = cv2.threshold(diff, adaptive_threshold, 255, cv2.THRESH_BINARY)

        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rects: List[Dict[str, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_contour_area:
                ignored_noise += 1
                continue

            if require_quad:
                peri = cv2.arcLength(contour, True)
                if peri <= 0:
                    ignored_noise += 1
                    continue
                approx = cv2.approxPolyDP(contour, 0.03 * peri, True)
                if len(approx) < 4:
                    ignored_noise += 1
                    continue

            bx, by, bw, bh = cv2.boundingRect(contour)
            if bw <= 2 or bh <= 2:
                ignored_noise += 1
                continue
            rects.append({
                "x": int(rx + bx),
                "y": int(ry + by),
                "width": int(bw),
                "height": int(bh),
            })

        return _merge_rectangles(rects, padding=4)

    ordered_region_ids = ["search_bar", "main_menu", "contact_list", "chat_display", "chat_input"]
    for region_id in ordered_region_ids:
        _ensure_not_cancelled()
        _progress("mouse_scan", f"正在扫描区域: {region_id}")
        region_start_points = int(points_scanned)
        region_item = regions.get(region_id) or {}
        local_bounds = _normalize_region_bounds_for_window(region_item.get("bounds", {}), window_info)
        if not local_bounds:
            region_debug[region_id] = {
                "used": False,
                "reason": "invalid_or_empty_bounds",
                "bounds": region_item.get("bounds", {}),
                "scanned_points": 0,
                "candidates_before_merge": 0,
                "candidates_after_merge": 0,
            }
            continue

        rx = int(local_bounds["x"])
        ry = int(local_bounds["y"])
        rw = int(local_bounds["width"])
        rh = int(local_bounds["height"])
        r_x1 = rx + rw
        r_y1 = ry + rh

        region_candidates: List[Dict[str, Any]] = []

        # 区域1：搜索栏固定规则（不做移动扫描）
        if region_id == "search_bar":
            input_w = max(20, int(rw * 0.7))
            input_h = max(14, int(rh * 0.7))
            input_x = rx + (rw - input_w) // 2
            input_y = ry + (rh - input_h) // 2
            input_bounds = {
                "x": int(input_x),
                "y": int(input_y),
                "width": int(input_w),
                "height": int(input_h),
            }
            input_cx = win_x + input_bounds["x"] + input_bounds["width"] // 2
            input_cy = win_y + input_bounds["y"] + input_bounds["height"] // 2
            region_candidates.append(_build_candidate(
                region_id=region_id,
                region_item=region_item,
                name="搜索输入框",
                control_type="input",
                bounds=input_bounds,
                source="rule_fixed",
                probe_abs_x=input_cx,
                probe_abs_y=input_cy,
            ))

            quick_w = max(18, min(40, int(rw * 0.12)))
            quick_x = max(rx, r_x1 - 30)
            if quick_x + quick_w > r_x1:
                quick_w = max(8, r_x1 - quick_x)
            quick_bounds = {
                "x": int(quick_x),
                "y": int(input_y),
                "width": int(max(8, quick_w)),
                "height": int(input_h),
            }
            quick_cx = win_x + quick_bounds["x"] + quick_bounds["width"] // 2
            quick_cy = win_y + quick_bounds["y"] + quick_bounds["height"] // 2
            region_candidates.append(_build_candidate(
                region_id=region_id,
                region_item=region_item,
                name="快捷操作按钮",
                control_type="button",
                bounds=quick_bounds,
                source="rule_fixed",
                probe_abs_x=quick_cx,
                probe_abs_y=quick_cy,
            ))

        # 区域2/3：沿Y轴单次扫描
        elif region_id in ["main_menu", "contact_list"]:
            scan_step_y = 20
            settle_ms_local = 500 if region_id == "contact_list" else 2500
            center_x = rx + rw // 2
            for probe_y in range(ry + 8, max(ry + 9, r_y1 - 8), scan_step_y):
                _ensure_not_cancelled()
                if points_scanned >= max_points:
                    break
                rects = _extract_change_rects(
                    region_bounds=local_bounds,
                    probe_rel_x=center_x,
                    probe_rel_y=probe_y,
                    settle_ms_local=settle_ms_local,
                    require_quad=True,
                )
                probe_abs_x = win_x + center_x
                probe_abs_y = win_y + probe_y
                for idx, rect in enumerate(rects):
                    clipped = _clip_rect(rect, local_bounds)
                    if not clipped:
                        continue
                    region_candidates.append(_build_candidate(
                        region_id=region_id,
                        region_item=region_item,
                        name=f"{region_id}_control_{idx + 1}",
                        control_type="button" if region_id == "main_menu" else "list_item",
                        bounds=clipped,
                        source="rule_vertical_scan",
                        probe_abs_x=probe_abs_x,
                        probe_abs_y=probe_abs_y,
                    ))

        # 区域4：两个固定探针点
        elif region_id == "chat_display":
            settle_ms_local = 3000
            probe_points = [
                {
                    "id": "chat_info_button",
                    "name": "聊天信息按钮",
                    "type": "button",
                    "x": max(rx + 4, r_x1 - 20),
                    "y": min(r_y1 - 4, ry + 10),
                    "fallback": {"x": max(rx + 2, r_x1 - 44), "y": max(ry + 2, ry + 2), "width": 40, "height": 20},
                },
                {
                    "id": "chat_scrollbar",
                    "name": "滑动按钮",
                    "type": "scrollbar",
                    "x": max(rx + 1, r_x1 - 3),
                    "y": ry + rh // 2,
                    "fallback": {"x": max(rx + 1, r_x1 - 6), "y": max(ry + 6, ry + rh // 2 - 80), "width": 5, "height": min(max(40, rh // 3), rh - 12)},
                },
            ]

            for point in probe_points:
                _ensure_not_cancelled()
                if points_scanned >= max_points:
                    break
                rects = _extract_change_rects(
                    region_bounds=local_bounds,
                    probe_rel_x=int(point["x"]),
                    probe_rel_y=int(point["y"]),
                    settle_ms_local=settle_ms_local,
                    require_quad=True,
                )
                probe_abs_x = win_x + int(point["x"])
                probe_abs_y = win_y + int(point["y"])
                if not rects:
                    fallback_rect = _clip_rect(point["fallback"], local_bounds)
                    if fallback_rect:
                        region_candidates.append(_build_candidate(
                            region_id=region_id,
                            region_item=region_item,
                            name=str(point["name"]),
                            control_type=str(point["type"]),
                            bounds=fallback_rect,
                            source="rule_probe_fallback",
                            probe_abs_x=probe_abs_x,
                            probe_abs_y=probe_abs_y,
                        ))
                    continue

                for rect in rects:
                    clipped = _clip_rect(rect, local_bounds)
                    if not clipped:
                        continue
                    region_candidates.append(_build_candidate(
                        region_id=region_id,
                        region_item=region_item,
                        name=str(point["name"]),
                        control_type=str(point["type"]),
                        bounds=clipped,
                        source="rule_probe_scan",
                        probe_abs_x=probe_abs_x,
                        probe_abs_y=probe_abs_y,
                    ))

        # 区域5：底部横向单次扫描 + 发送按钮专项动作
        elif region_id == "chat_input":
            scan_step_x = 15
            settle_ms_local = 2500
            probe_y = min(r_y1 - 2, ry + 10)

            for probe_x in range(rx + 6, max(rx + 7, r_x1 - 6), scan_step_x):
                _ensure_not_cancelled()
                if points_scanned >= max_points:
                    break
                rects = _extract_change_rects(
                    region_bounds=local_bounds,
                    probe_rel_x=probe_x,
                    probe_rel_y=probe_y,
                    settle_ms_local=settle_ms_local,
                    require_quad=True,
                )
                probe_abs_x = win_x + probe_x
                probe_abs_y = win_y + probe_y
                for idx, rect in enumerate(rects):
                    clipped = _clip_rect(rect, local_bounds)
                    if not clipped:
                        continue
                    region_candidates.append(_build_candidate(
                        region_id=region_id,
                        region_item=region_item,
                        name=f"chat_input_control_{idx + 1}",
                        control_type="button",
                        bounds=clipped,
                        source="rule_horizontal_scan",
                        probe_abs_x=probe_abs_x,
                        probe_abs_y=probe_abs_y,
                    ))

            # 发送按钮专项标注：区域中点点击 + 输入"1"
            if points_scanned < max_points:
                send_probe_x = rx + rw // 2
                send_probe_y = ry + rh // 2
                abs_send_x = win_x + send_probe_x
                abs_send_y = win_y + send_probe_y

                clicked = False
                typed = False
                try:
                    _ensure_not_cancelled()
                    if hasattr(manager, "humanized_click"):
                        clicked = bool(manager.humanized_click(abs_send_x, abs_send_y, 1))
                    if not clicked:
                        click_ret = subprocess.run(
                            ["xdotool", "mousemove", "--sync", str(abs_send_x), str(abs_send_y), "click", "1"],
                            capture_output=True,
                            text=True,
                            timeout=3,
                        )
                        clicked = click_ret.returncode == 0
                except Exception:
                    clicked = False

                try:
                    _ensure_not_cancelled()
                    if hasattr(manager, "humanized_input"):
                        typed = bool(manager.humanized_input("1"))
                    if not typed:
                        type_ret = subprocess.run(
                            ["xdotool", "type", "--delay", "60", "1"],
                            capture_output=True,
                            text=True,
                            timeout=3,
                        )
                        typed = type_ret.returncode == 0
                except Exception:
                    typed = False

                rects = _extract_change_rects(
                    region_bounds=local_bounds,
                    probe_rel_x=send_probe_x,
                    probe_rel_y=send_probe_y,
                    settle_ms_local=3000,
                    require_quad=True,
                )
                if not rects:
                    fallback_send = {
                        "x": max(rx + 2, send_probe_x - 40),
                        "y": max(ry + 2, send_probe_y - 14),
                        "width": min(80, max(24, rw // 4)),
                        "height": min(28, max(16, rh // 3)),
                    }
                    clipped_fallback_send = _clip_rect(fallback_send, local_bounds)
                    if clipped_fallback_send:
                        region_candidates.append(_build_candidate(
                            region_id=region_id,
                            region_item=region_item,
                            name="发送按钮",
                            control_type="button",
                            bounds=clipped_fallback_send,
                            source="rule_send_button_fallback",
                            probe_abs_x=abs_send_x,
                            probe_abs_y=abs_send_y,
                        ))
                else:
                    for rect in rects:
                        clipped = _clip_rect(rect, local_bounds)
                        if not clipped:
                            continue
                        region_candidates.append(_build_candidate(
                            region_id=region_id,
                            region_item=region_item,
                            name="发送按钮",
                            control_type="button",
                            bounds=clipped,
                            source="rule_send_button_action",
                            probe_abs_x=abs_send_x,
                            probe_abs_y=abs_send_y,
                        ))

                send_button_action_clicked = bool(clicked)
                send_button_action_typed = bool(typed)

        reduced = _merge_region_candidates(region_candidates, iou_threshold=0.35)
        for idx, item in enumerate(reduced):
            item["id"] = f"{region_id}_{idx}"
            if item.get("matched_atspi_name"):
                item["name"] = str(item.get("matched_atspi_name"))
            if item.get("matched_atspi_role"):
                item["type"] = str(item.get("matched_atspi_role"))
        generated_candidates.extend(reduced)

        region_debug[region_id] = {
            "used": True,
            "bounds": local_bounds,
            "scanned_points": max(0, int(points_scanned) - region_start_points),
            "candidates_before_merge": len(region_candidates),
            "candidates_after_merge": len(reduced),
            "atspi_name_hits": len([item for item in reduced if item.get("matched_atspi_name")]),
        }

    # 全局去重（仅针对可点击候选，保留动作标记）
    deduped: List[Dict[str, Any]] = []
    action_markers: List[Dict[str, Any]] = []
    for item in generated_candidates:
        if not bool(item.get("clickable_candidate", True)):
            action_markers.append(item)
            continue
        found = False
        for ex in deduped:
            if item.get("region_id") == ex.get("region_id") and _rect_iou(item["bounds"], ex["bounds"]) >= 0.45:
                ex["bounds"] = _rect_union(ex["bounds"], item["bounds"])
                ex["hover_hits"] = int(ex.get("hover_hits", 1)) + int(item.get("hover_hits", 1))
                found = True
                break
        if not found:
            deduped.append(item)

    final_candidates = deduped + action_markers
    final_candidates.sort(key=lambda x: (str(x.get("region_id", "")), -int(x.get("hover_hits", 0)), str(x.get("id", ""))))

    # 输出统一控件标注图（包含本轮所有控件坐标）
    annotated = base.copy()
    overlay = annotated.copy()
    for item in final_candidates:
        b = item.get("bounds", {})
        x1 = int(b.get("x", 0))
        y1 = int(b.get("y", 0))
        w = int(b.get("width", 0))
        h = int(b.get("height", 0))
        if w <= 0 or h <= 0:
            continue
        x2 = x1 + w
        y2 = y1 + h
        color = (40, 30, 190) if bool(item.get("clickable_candidate", True)) else (30, 160, 120)
        border = (0, 0, 255) if bool(item.get("clickable_candidate", True)) else (0, 140, 0)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), border, 2)
        label = f"{item.get('region_id')}:{item.get('name') or item.get('id')}"
        cv2.putText(annotated, label[:54], (x1, max(16, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, border, 1, cv2.LINE_AA)
    annotated = cv2.addWeighted(overlay, 0.25, annotated, 0.75, 0)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    annotated_path = f"/tmp/wechat_mouse_scan_regions_{ts}.png"
    cv2.imwrite(annotated_path, annotated)
    annotated_base64 = _encode_png_base64(annotated)

    return final_candidates, {
        "scan_mode": "region_rule_scan_v2",
        "rules_profile": "five_region_custom_2026_02_21",
        "step_x": step_x,
        "step_y": step_y,
        "settle_ms": settle_ms,
        "points_scanned": points_scanned,
        "regions_detected": len([item for item in final_candidates if bool(item.get("clickable_candidate", True))]),
        "ignored_noise_rects": ignored_noise,
        "atspi_name_hits": atspi_hits,
        "region_debug": region_debug,
        "send_button_action": {
            "clicked": bool(send_button_action_clicked),
            "typed_1": bool(send_button_action_typed),
        },
        "annotated_image": annotated_path,
        "annotated_image_data": f"data:image/png;base64,{annotated_base64}",
    }


def _collect_mouse_scan_layer_real(
    manager: Any,
    window_info: Dict[str, Any],
    step_x: int,
    step_y: int,
    settle_ms: int,
    max_points: int,
    direction: str,
    diff_threshold: int = 24,
    min_contour_area: int = 160,
    min_stable_hits: int = 3,
    overlay_alpha: float = 0.28,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if step_x <= 0:
        step_x = 80
    if step_y <= 0:
        step_y = 70
    if settle_ms < 40:
        settle_ms = 40
    if max_points <= 0:
        max_points = 180

    width = max(1, int(window_info.get("width", 1)))
    height = max(1, int(window_info.get("height", 1)))
    win_x = int(window_info.get("x", 0))
    win_y = int(window_info.get("y", 0))

    base = _capture_scan_image(manager)
    base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)

    if direction == "right_to_left":
        xs = list(range(max(20, width - 20), 20, -step_x))
    else:
        xs = list(range(20, max(21, width - 20), step_x))
    ys = list(range(60, max(61, height - 20), step_y))

    if not xs or not ys:
        return [], {
            "scan_mode": "real_mouse",
            "direction": direction,
            "points_scanned": 0,
            "annotated_image": "",
            "warning": "窗口尺寸过小，无法执行扫描"
        }

    region_tracks: List[Dict[str, Any]] = []
    active_track_id: Optional[str] = None
    track_index = 0
    transitions = 0
    points_scanned = 0
    points_with_change = 0
    points_without_change = 0
    ignored_noise_rects = 0

    diff_threshold = max(8, min(80, int(diff_threshold)))
    min_contour_area = max(40, min(2500, int(min_contour_area)))
    min_stable_hits = max(1, min(12, int(min_stable_hits)))
    overlay_alpha = max(0.05, min(0.75, float(overlay_alpha)))

    temporal_frames = 3
    temporal_interval_ms = 35
    caret_max_width = 5
    caret_max_height = 70
    cursor_min_width = 8
    cursor_max_width = 26
    cursor_min_height = 10
    cursor_max_height = 34
    scrollbar_edge_zone = 24
    scrollbar_max_width = max(18, int(width * 0.03))
    scrollbar_min_height = max(100, int(height * 0.12))

    def _is_noise_rect(rect: Dict[str, int], point_x: int, point_y: int) -> bool:
        rx = int(rect["x"])
        ry = int(rect["y"])
        rw = int(rect["width"])
        rh = int(rect["height"])

        if rw <= caret_max_width and rh <= caret_max_height:
            return True

        cursor_like = (
            cursor_min_width <= rw <= cursor_max_width
            and cursor_min_height <= rh <= cursor_max_height
        )
        near_cursor_point = (rx - 8) <= point_x <= (rx + rw + 8) and (ry - 8) <= point_y <= (ry + rh + 8)
        if cursor_like and near_cursor_point:
            return True

        near_right_edge = (rx + rw) >= (width - scrollbar_edge_zone)
        if near_right_edge and rw <= scrollbar_max_width and rh >= scrollbar_min_height:
            return True

        if rw <= 12 and rh >= 45 and (rh / max(1, rw)) >= 4.0:
            return True

        if rw * rh < min_contour_area:
            return True
        return False

    def _extract_stable_diff_rect(point_x: int, point_y: int) -> Optional[Dict[str, int]]:
        nonlocal ignored_noise_rects

        stable_mask: Optional[np.ndarray] = None
        for frame_idx in range(temporal_frames):
            if frame_idx > 0:
                time.sleep(temporal_interval_ms / 1000.0)
            snap = _capture_scan_image(manager)
            snap_gray = cv2.cvtColor(snap, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(base_gray, snap_gray)
            _, binary = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)
            if stable_mask is None:
                stable_mask = binary
            else:
                stable_mask = cv2.bitwise_and(stable_mask, binary)

        if stable_mask is None:
            return None

        kernel = np.ones((3, 3), np.uint8)
        stable_mask = cv2.morphologyEx(stable_mask, cv2.MORPH_OPEN, kernel)
        stable_mask = cv2.morphologyEx(stable_mask, cv2.MORPH_CLOSE, kernel)
        stable_mask = cv2.dilate(stable_mask, kernel, iterations=1)

        contours, _ = cv2.findContours(stable_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        current_rects: List[Dict[str, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_contour_area:
                continue
            rx, ry, rw, rh = cv2.boundingRect(contour)
            candidate = {"x": int(rx), "y": int(ry), "width": int(rw), "height": int(rh)}
            if _is_noise_rect(candidate, point_x=point_x, point_y=point_y):
                ignored_noise_rects += 1
                continue
            current_rects.append(candidate)

        if not current_rects:
            return None

        merged_current = _merge_rectangles(current_rects, padding=5)
        if not merged_current:
            return None

        merged_current.sort(key=lambda rect: rect["width"] * rect["height"], reverse=True)
        return merged_current[0]

    def _find_best_track(rect: Dict[str, int], min_iou: float = 0.35) -> Optional[Dict[str, Any]]:
        best_track: Optional[Dict[str, Any]] = None
        best_iou = 0.0
        for track in region_tracks:
            iou = _rect_iou(track["bounds"], rect)
            if iou > best_iou:
                best_iou = iou
                best_track = track
        if best_track is None or best_iou < min_iou:
            return None
        return best_track

    for y in ys:
        for x in xs:
            if points_scanned >= max_points:
                break

            abs_x = win_x + x
            abs_y = win_y + y

            move = subprocess.run(
                ["xdotool", "mousemove", "--sync", str(abs_x), str(abs_y)],
                capture_output=True,
                text=True,
                timeout=3
            )
            if move.returncode != 0:
                continue

            time.sleep(settle_ms / 1000.0)
            primary_rect = _extract_stable_diff_rect(point_x=int(x), point_y=int(y))

            if primary_rect is None:
                if active_track_id is not None:
                    transitions += 1
                active_track_id = None
                points_without_change += 1
                points_scanned += 1
                continue

            points_with_change += 1
            matched_track = None
            if active_track_id is not None:
                active_track = next((item for item in region_tracks if item["id"] == active_track_id), None)
                if active_track is not None and _rect_iou(active_track["bounds"], primary_rect) >= 0.35:
                    matched_track = active_track

            if matched_track is None:
                matched_track = _find_best_track(primary_rect, min_iou=0.35)

            if matched_track is None:
                track_id = f"hover_{track_index}"
                track_index += 1
                matched_track = {
                    "id": track_id,
                    "name": f"hover_region_{track_index - 1}",
                    "bounds": primary_rect,
                    "hits": 0,
                    "points": [],
                    "source": "real_mouse_hover_scan",
                }
                region_tracks.append(matched_track)
            elif active_track_id != matched_track["id"]:
                transitions += 1

            matched_track["hits"] += 1
            matched_track["bounds"] = _rect_union(matched_track["bounds"], primary_rect)
            matched_track["points"].append({"x": int(x), "y": int(y)})
            active_track_id = matched_track["id"]

            points_scanned += 1

        if points_scanned >= max_points:
            break

    scan_regions: List[Dict[str, Any]] = []
    effective_min_hits = min_stable_hits
    if points_with_change <= 4:
        effective_min_hits = 2

    stable_tracks = [track for track in region_tracks if int(track.get("hits", 0)) >= effective_min_hits]
    stable_tracks.sort(key=lambda item: int(item.get("hits", 0)), reverse=True)

    for track in stable_tracks:
        scan_regions.append({
            "id": track["id"],
            "name": track["name"],
            "source": track.get("source", "real_mouse_hover_scan"),
            "clickable_candidate": True,
            "bounds": track["bounds"],
            "hover_hits": int(track.get("hits", 0)),
            "hover_points": track.get("points", [])[:12],
            "stability": round(float(track.get("hits", 0)) / max(1, points_scanned), 4),
        })

    annotated = base.copy()
    overlay = annotated.copy()
    max_hits = max([int(item.get("hover_hits", 0)) for item in scan_regions], default=1)
    for item in scan_regions:
        b = item["bounds"]
        x1 = int(b["x"])
        y1 = int(b["y"])
        x2 = x1 + int(b["width"])
        y2 = y1 + int(b["height"])
        hit_ratio = float(int(item.get("hover_hits", 0))) / float(max_hits)
        color_depth = int(70 + 140 * hit_ratio)
        fill_color = (20, 20, max(0, min(255, color_depth)))
        cv2.rectangle(overlay, (x1, y1), (x2, y2), fill_color, -1)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{item['id']}({int(item.get('hover_hits', 0))})"
        cv2.putText(annotated, label, (x1, max(16, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)

    annotated = cv2.addWeighted(overlay, overlay_alpha, annotated, 1.0 - overlay_alpha, 0)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    annotated_path = f"/tmp/wechat_mouse_scan_{ts}.png"
    cv2.imwrite(annotated_path, annotated)
    annotated_base64 = _encode_png_base64(annotated)

    return scan_regions, {
        "scan_mode": "real_mouse",
        "direction": direction,
        "step_x": step_x,
        "step_y": step_y,
        "settle_ms": settle_ms,
        "diff_threshold": diff_threshold,
        "temporal_frames": temporal_frames,
        "min_stable_hits": min_stable_hits,
        "effective_min_hits": effective_min_hits,
        "overlay_alpha": overlay_alpha,
        "points_scanned": points_scanned,
        "points_with_change": points_with_change,
        "points_without_change": points_without_change,
        "ignored_noise_rects": ignored_noise_rects,
        "unstable_tracks_filtered": max(0, len(region_tracks) - len(stable_tracks)),
        "region_switches": transitions,
        "regions_detected": len(scan_regions),
        "annotated_image": annotated_path,
        "annotated_image_data": f"data:image/png;base64,{annotated_base64}",
    }


def _collect_control_layer(manager: Any) -> List[Dict[str, Any]]:
    controls = _extract_ui_elements(manager)
    merged: List[Dict[str, Any]] = []

    for item in controls:
        merged.append({
            "id": str(item.get("id", "")),
            "name": str(item.get("name", "")),
            "type": str(item.get("type", "other")),
            "source": "atspi_or_ui_analysis",
            "clickable_candidate": str(item.get("type", "")).lower() in ["button", "menu", "list"],
            "bounds": _normalize_bounds(item.get("bounds", {})),
        })

    if hasattr(manager, "find_all_buttons"):
        try:
            buttons = manager.find_all_buttons()
            for index, region in enumerate(buttons):
                width = int(getattr(region, "width", 0))
                height = int(getattr(region, "height", 0))
                if width <= 0 or height <= 0:
                    continue
                merged.append({
                    "id": f"button_{index}",
                    "name": f"button_{index}",
                    "type": "button",
                    "source": "button_detector",
                    "clickable_candidate": True,
                    "bounds": {
                        "x": int(getattr(region, "x", 0)),
                        "y": int(getattr(region, "y", 0)),
                        "width": width,
                        "height": height,
                    },
                })
        except Exception as e:
            logger.warning(f"按钮层获取失败: {e}")

    return merged


def _build_geometry_layer(window_info: Dict[str, Any]) -> Dict[str, Any]:
    width = max(1, int(window_info.get("width", 1)))
    height = max(1, int(window_info.get("height", 1)))
    return {
        "window": {
            "x": int(window_info.get("x", 0)),
            "y": int(window_info.get("y", 0)),
            "width": width,
            "height": height,
            "aspect_ratio": round(width / height, 4),
        },
        "grid": {
            "cols": 12,
            "rows": 12,
            "cell_width": round(width / 12, 2),
            "cell_height": round(height / 12, 2),
        }
    }


def _resolve_annotation_bounds(
    annotation: Dict[str, Any],
    candidate_by_id: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, int]]:
    direct_bounds = annotation.get("bounds")
    if isinstance(direct_bounds, dict):
        normalized = _normalize_bounds(direct_bounds)
        if normalized["width"] > 0 and normalized["height"] > 0:
            return normalized

    region_id = str(annotation.get("region_id", "")).strip()
    if region_id and region_id in candidate_by_id:
        bounds = _normalize_bounds(candidate_by_id[region_id].get("bounds", {}))
        if bounds["width"] > 0 and bounds["height"] > 0:
            return bounds

    return None


def _classify_element_type(element_name: str) -> str:
    name = element_name.lower()
    if "button" in name or "btn" in name:
        return "button"
    if "input" in name or "edit" in name or "text" in name:
        return "input"
    if "list" in name:
        return "list"
    if "menu" in name:
        return "menu"
    return "other"


def _safe_region_dict(region: Any, element_name: str) -> Optional[Dict[str, Any]]:
    if isinstance(region, dict):
        x = int(region.get("x", 0))
        y = int(region.get("y", 0))
        width = int(region.get("width", 0))
        height = int(region.get("height", 0))
    else:
        x = int(getattr(region, "x", 0))
        y = int(getattr(region, "y", 0))
        width = int(getattr(region, "width", 0))
        height = int(getattr(region, "height", 0))

    if width <= 0 or height <= 0:
        return None

    return {
        "id": str(element_name),
        "name": str(element_name),
        "type": _classify_element_type(str(element_name)),
        "bounds": {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
    }


def _extract_ui_elements(manager: Any) -> List[Dict[str, Any]]:
    if not hasattr(manager, "analyze_ui_elements"):
        return []

    raw_elements = manager.analyze_ui_elements()
    if not isinstance(raw_elements, dict):
        return []

    formatted_elements = []
    for name, region in raw_elements.items():
        item = _safe_region_dict(region, name)
        if item:
            formatted_elements.append(item)

    return formatted_elements


def _ensure_image_ndarray(image: Any) -> np.ndarray:
    if not isinstance(image, np.ndarray):
        image = np.array(image)
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if not image.flags["C_CONTIGUOUS"]:
        image = np.ascontiguousarray(image)
    return image


def _annotate_image(image: np.ndarray, elements: List[Dict[str, Any]]) -> np.ndarray:
    height, width = image.shape[:2]
    for element in elements:
        bounds = element.get("bounds", {})
        x = int(bounds.get("x", 0))
        y = int(bounds.get("y", 0))
        w = int(bounds.get("width", 0))
        h = int(bounds.get("height", 0))

        if w <= 0 or h <= 0:
            continue

        x1 = max(0, min(x, width - 1))
        y1 = max(0, min(y, height - 1))
        x2 = max(0, min(x + w, width - 1))
        y2 = max(0, min(y + h, height - 1))

        if x2 <= x1 or y2 <= y1:
            continue

        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            image,
            element.get("name", "unknown"),
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA
        )

    return image


def _encode_png_base64(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode('.png', image)
    if not ok:
        raise RuntimeError("截图编码失败")
    return base64.b64encode(buffer).decode('utf-8')


def _build_atspi_search_keywords(
    name_filter: Optional[str],
    extra_terms: Optional[str],
    include_common_keywords: bool,
) -> List[str]:
    common_keywords = [
        "发送", "发", "send", "submit", "post",
        "编辑", "输入", "edit", "input", "entry", "textbox", "text box", "compose",
        "留言", "消息", "信息", "message", "messages", "chat", "conversation", "msg",
        "更多", "more", "menu", "option", "options",
        "文件", "附件", "file", "attach", "attachment",
        "联系人", "通讯录", "contact", "contacts",
        "搜索", "查找", "search", "find",
        "确认", "确定", "ok", "confirm",
        "取消", "cancel",
    ]

    synonyms = {
        "发送": ["send", "submit", "post", "发"],
        "send": ["发送", "发", "submit", "post"],
        "编辑": ["edit", "input", "entry", "textbox", "输入"],
        "edit": ["编辑", "输入", "entry", "textbox"],
        "留言": ["message", "messages", "chat", "信息", "消息"],
        "message": ["留言", "消息", "信息", "chat", "messages"],
        "信息": ["message", "messages", "消息", "留言"],
        "消息": ["message", "messages", "信息", "留言"],
        "更多": ["more", "menu", "option", "options"],
        "more": ["更多", "menu", "option", "options"],
        "文件": ["file", "attach", "attachment", "附件"],
        "file": ["文件", "附件", "attach", "attachment"],
        "联系人": ["contact", "contacts", "通讯录"],
        "contact": ["联系人", "contacts", "通讯录"],
        "搜索": ["search", "find", "查找"],
        "search": ["搜索", "查找", "find"],
    }

    seeds: List[str] = []
    if include_common_keywords:
        seeds.extend(common_keywords)

    if name_filter:
        parts = [item.strip().lower() for item in name_filter.replace("，", ",").split(",") if item.strip()]
        seeds.extend(parts)

    if extra_terms:
        parts = [item.strip().lower() for item in extra_terms.replace("，", ",").split(",") if item.strip()]
        seeds.extend(parts)

    expanded: List[str] = []
    seen = set()
    for term in seeds:
        t = term.strip().lower()
        if not t:
            continue

        if t not in seen:
            seen.add(t)
            expanded.append(t)

        for key, values in synonyms.items():
            if t == key or t in values:
                if key not in seen:
                    seen.add(key)
                    expanded.append(key)
                for alias in values:
                    alias_n = alias.strip().lower()
                    if alias_n and alias_n not in seen:
                        seen.add(alias_n)
                        expanded.append(alias_n)

    return expanded


def _atspi_term_hit(searchable: str, term: str) -> bool:
    t = (term or "").strip().lower()
    if not t:
        return False

    # 中文等非ASCII词沿用子串匹配
    if re.search(r"[^\x00-\x7F]", t):
        return t in searchable

    # 英文/数字词使用单词边界，避免 chat 命中 wechat
    escaped = re.escape(t)
    pattern = rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])"
    return re.search(pattern, searchable) is not None


def _random_delay(min_seconds: float = 0.08, max_seconds: float = 0.28) -> float:
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay


def _is_send_like_element(element_id: str) -> bool:
    element_name = str(element_id).lower()
    send_keywords = ["send", "发送", "submit", "commit"]
    return any(keyword in element_name for keyword in send_keywords)


def _get_element_bounds_by_id(manager: Any, element_id: str) -> Optional[Dict[str, int]]:
    element_name = str(element_id)

    elements = _extract_ui_elements(manager)
    for item in elements:
        if str(item.get("id", "")) == element_name:
            bounds = item.get("bounds", {})
            return {
                "x": int(bounds.get("x", 0)),
                "y": int(bounds.get("y", 0)),
                "width": int(bounds.get("width", 0)),
                "height": int(bounds.get("height", 0)),
            }

    if element_name.startswith("button_") and hasattr(manager, "find_all_buttons"):
        try:
            index = int(element_name.split("_", 1)[1])
            buttons = manager.find_all_buttons()
            if 0 <= index < len(buttons):
                region = buttons[index]
                return {
                    "x": int(getattr(region, "x", 0)),
                    "y": int(getattr(region, "y", 0)),
                    "width": int(getattr(region, "width", 0)),
                    "height": int(getattr(region, "height", 0)),
                }
        except Exception as e:
            logger.warning(f"解析按钮坐标失败({element_name}): {e}")

    return None


def _humanized_coordinate_click(manager: Any, bounds: Dict[str, int]) -> Dict[str, Any]:
    x = int(bounds.get("x", 0))
    y = int(bounds.get("y", 0))
    width = int(bounds.get("width", 0))
    height = int(bounds.get("height", 0))

    if width <= 0 or height <= 0:
        return {"success": False, "reason": "元素坐标尺寸无效"}

    center_x = x + width // 2
    center_y = y + height // 2

    jitter_x = random.randint(-max(1, width // 8), max(1, width // 8))
    jitter_y = random.randint(-max(1, height // 8), max(1, height // 8))
    target_x = center_x + jitter_x
    target_y = center_y + jitter_y

    pre_delay = _random_delay(0.10, 0.35)

    if hasattr(manager, "humanized_click"):
        success = manager.humanized_click(target_x, target_y, 1)
        return {
            "success": bool(success),
            "target": {"x": target_x, "y": target_y},
            "delay": pre_delay,
            "engine": "wechat_rpa.humanized_click"
        }

    move_cmd = ["xdotool", "mousemove", "--sync", str(target_x), str(target_y)]
    click_cmd = ["xdotool", "click", "1"]

    move_ret = subprocess.run(move_cmd, capture_output=True, text=True, timeout=3)
    if move_ret.returncode != 0:
        return {
            "success": False,
            "reason": f"坐标移动失败: {move_ret.stderr.strip() or move_ret.stdout.strip() or 'unknown'}"
        }

    _random_delay(0.05, 0.15)
    click_ret = subprocess.run(click_cmd, capture_output=True, text=True, timeout=3)
    if click_ret.returncode != 0:
        return {
            "success": False,
            "reason": f"坐标点击失败: {click_ret.stderr.strip() or click_ret.stdout.strip() or 'unknown'}"
        }

    return {
        "success": True,
        "target": {"x": target_x, "y": target_y},
        "delay": pre_delay,
        "engine": "xdotool"
    }


def _keyboard_send_fallback() -> Dict[str, Any]:
    _random_delay(0.08, 0.20)

    enter_ret = subprocess.run(
        ["xdotool", "key", "--clearmodifiers", "Return"],
        capture_output=True,
        text=True,
        timeout=3
    )
    if enter_ret.returncode == 0:
        return {"success": True, "key": "Return"}

    ctrl_enter_ret = subprocess.run(
        ["xdotool", "key", "--clearmodifiers", "ctrl+Return"],
        capture_output=True,
        text=True,
        timeout=3
    )
    if ctrl_enter_ret.returncode == 0:
        return {"success": True, "key": "ctrl+Return"}

    return {
        "success": False,
        "reason": (
            enter_ret.stderr.strip()
            or ctrl_enter_ret.stderr.strip()
            or "键盘发送失败，可能缺少焦点或xdotool不可用"
        )
    }


def _elapsed_ms(start_at: float) -> float:
    return round((time.perf_counter() - start_at) * 1000, 2)

# 5区域预定义
PREDEFINED_REGIONS = {
    "search_bar": {"name": "搜索栏区域", "function": "search_contacts"},
    "main_menu": {"name": "主菜单工具栏区域", "function": "switch_templates"},
    "contact_list": {"name": "联系人列表区域", "function": "select_contacts"},
    "chat_display": {"name": "聊天信息展示区域", "function": "view_messages"},
    "chat_input": {"name": "聊天输入发送区域", "function": "input_messages"}
}

def _estimate_region_bounds(window_info: Dict[str, Any], template_type: str) -> Dict[str, Dict[str, Any]]:
    """基于窗口尺寸估算5区域边界（比例估算，后续人工调整）"""
    width = int(window_info.get("width", 980))
    height = int(window_info.get("height", 1025))
    
    if template_type == "chat":
        # 聊天界面布局估算
        return {
            "search_bar": {
                "name": "搜索栏区域",
                "bounds": {"x": 20, "y": 10, "width": width - 40, "height": 40},
                "function": "search_contacts"
            },
            "main_menu": {
                "name": "主菜单工具栏区域", 
                "bounds": {"x": 0, "y": height - 60, "width": width, "height": 60},
                "function": "switch_templates"
            },
            "contact_list": {
                "name": "联系人列表区域",
                "bounds": {"x": 0, "y": 60, "width": int(width * 0.3), "height": height - 120},
                "function": "select_contacts"
            },
            "chat_display": {
                "name": "聊天信息展示区域",
                "bounds": {"x": int(width * 0.3), "y": 60, "width": int(width * 0.7), "height": int((height - 120) * 0.7)},
                "function": "view_messages"
            },
            "chat_input": {
                "name": "聊天输入发送区域",
                "bounds": {"x": int(width * 0.3), "y": int(height - 120 - (height - 120) * 0.3), "width": int(width * 0.7), "height": int((height - 120) * 0.3)},
                "function": "input_messages"
            }
        }
    else:  # contacts
        # 联系人界面布局估算
        return {
            "search_bar": {
                "name": "搜索栏区域",
                "bounds": {"x": 20, "y": 10, "width": width - 40, "height": 40},
                "function": "search_contacts"
            },
            "main_menu": {
                "name": "主菜单工具栏区域",
                "bounds": {"x": 0, "y": height - 60, "width": width, "height": 60},
                "function": "switch_templates"
            },
            "contact_list": {
                "name": "联系人列表区域",
                "bounds": {"x": 0, "y": 60, "width": width, "height": height - 120},
                "function": "select_contacts"
            },
            "chat_display": {
                "name": "聊天信息展示区域",
                "bounds": {"x": 0, "y": 0, "width": 0, "height": 0},  # 联系人界面无此区域
                "function": "view_messages"
            },
            "chat_input": {
                "name": "聊天输入发送区域",
                "bounds": {"x": 0, "y": 0, "width": 0, "height": 0},  # 联系人界面无此区域
                "function": "input_messages"
            }
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


def _annotate_via_atspi(region_id: str, template_type: str) -> Dict[str, Any]:
    """通过AT-SPI树进行标注"""
    try:
        engine = get_atspi_engine()
        manager = get_wechat_manager()
        
        # 获取微信窗口信息
        window_info = _safe_window_info(manager.get_wechat_window())
        
        # 根据region_id和template_type确定搜索关键词
        search_keywords = _get_region_keywords(region_id, template_type)
        
        # 搜索AT-SPI树中的元素
        candidates = []
        for keyword in search_keywords:
            elements = engine.find_elements_by_text(keyword, max_results=5)
            for elem in elements:
                if _is_element_in_region(elem, region_id, window_info, template_type):
                    candidates.append({
                        "bounds": {
                            "x": elem.get("x", 0),
                            "y": elem.get("y", 0),
                            "width": elem.get("width", 0),
                            "height": elem.get("height", 0)
                        },
                        "confidence": 0.8,
                        "source": "atspi",
                        "text": elem.get("text", ""),
                        "role": elem.get("role", "")
                    })
        
        return {
            "layer": "atspi",
            "candidates": candidates[:3],  # 最多返回3个候选
            "success": len(candidates) > 0
        }
    except Exception as e:
        logger.error(f"AT-SPI标注失败: {e}")
        return {
            "layer": "atspi",
            "candidates": [],
            "success": False,
            "error": str(e)
        }


def _annotate_via_mouse_scan(region_id: str, template_type: str) -> Dict[str, Any]:
    """通过鼠标扫描进行标注"""
    try:
        manager = get_wechat_manager()
        window_info = _safe_window_info(manager.get_wechat_window())
        
        # 获取区域预估边界
        regions = _estimate_region_bounds(window_info, template_type)
        region_bounds = regions.get(region_id, {}).get("bounds", {})
        
        if not region_bounds:
            return {
                "layer": "mouse_scan",
                "candidates": [],
                "success": False,
                "error": "无法获取区域边界"
            }
        
        # 在区域内进行鼠标扫描
        scan_result = _collect_mouse_scan_in_region(
            manager, region_bounds, step_x=40, step_y=35, settle_ms=100
        )
        
        candidates = []
        for item in scan_result.get("regions", [])[:3]:  # 最多3个
            candidates.append({
                "bounds": item.get("bounds", {}),
                "confidence": item.get("stability_score", 0.7),
                "source": "mouse_scan",
                "hover_hits": item.get("hover_hits", 0)
            })
        
        return {
            "layer": "mouse_scan",
            "candidates": candidates,
            "success": len(candidates) > 0
        }
    except Exception as e:
        logger.error(f"鼠标扫描标注失败: {e}")
        return {
            "layer": "mouse_scan",
            "candidates": [],
            "success": False,
            "error": str(e)
        }


def _annotate_via_ocr_ai(region_id: str, template_type: str) -> Dict[str, Any]:
    """通过OCR+AI进行标注"""
    try:
        manager = get_wechat_manager()
        window_info = _safe_window_info(manager.get_wechat_window())
        
        # 获取区域预估边界
        regions = _estimate_region_bounds(window_info, template_type)
        region_bounds = regions.get(region_id, {}).get("bounds", {})
        
        if not region_bounds:
            return {
                "layer": "ocr_ai",
                "candidates": [],
                "success": False,
                "error": "无法获取区域边界"
            }
        
        # 截取区域图像
        screenshot = manager.capture_wechat_window()
        if screenshot is None:
            return {
                "layer": "ocr_ai",
                "candidates": [],
                "success": False,
                "error": "截图失败"
            }
        
        # 裁剪到区域
        x, y, w, h = region_bounds["x"], region_bounds["y"], region_bounds["width"], region_bounds["height"]
        region_image = screenshot[y:y+h, x:x+w]
        
        # OCR识别
        ocr_results = _perform_ocr_on_image(region_image)
        
        # AI分析（简化版：基于关键词匹配）
        candidates = []
        expected_keywords = _get_region_keywords(region_id, template_type)
        
        for ocr_result in ocr_results:
            text = ocr_result.get("text", "").lower()
            confidence = 0.0
            for keyword in expected_keywords:
                if keyword.lower() in text:
                    confidence = max(confidence, 0.9)
                    break
            
            if confidence > 0.5:
                candidates.append({
                    "bounds": {
                        "x": x + ocr_result.get("x", 0),
                        "y": y + ocr_result.get("y", 0),
                        "width": ocr_result.get("width", 0),
                        "height": ocr_result.get("height", 0)
                    },
                    "confidence": confidence,
                    "source": "ocr_ai",
                    "text": ocr_result.get("text", "")
                })
        
        return {
            "layer": "ocr_ai",
            "candidates": candidates[:3],  # 最多3个
            "success": len(candidates) > 0
        }
    except Exception as e:
        logger.error(f"OCR+AI标注失败: {e}")
        return {
            "layer": "ocr_ai",
            "candidates": [],
            "success": False,
            "error": str(e)
        }


def _get_region_keywords(region_id: str, template_type: str) -> List[str]:
    """获取区域的搜索关键词"""
    keywords_map = {
        "search_bar": ["搜索", "查找", "search"],
        "main_menu": ["菜单", "设置", "menu", "options"],
        "contact_list": ["联系人", "好友", "contacts", "friends"],
        "chat_display": ["聊天", "消息", "chat", "message"],
        "chat_input": ["输入", "发送", "input", "send"]
    }
    return keywords_map.get(region_id, [])


def _is_element_in_region(element: Dict[str, Any], region_id: str, window_info: Dict[str, Any], template_type: str) -> bool:
    """检查元素是否在指定区域内"""
    regions = _estimate_region_bounds(window_info, template_type)
    region_bounds = regions.get(region_id, {}).get("bounds", {})
    
    elem_x = element.get("x", 0)
    elem_y = element.get("y", 0)
    elem_w = element.get("width", 0)
    elem_h = element.get("height", 0)
    
    region_x = region_bounds.get("x", 0)
    region_y = region_bounds.get("y", 0)
    region_w = region_bounds.get("width", 0)
    region_h = region_bounds.get("height", 0)
    
    # 检查重叠
    return (elem_x < region_x + region_w and elem_x + elem_w > region_x and
            elem_y < region_y + region_h and elem_y + elem_h > region_y)


def _collect_mouse_scan_in_region(manager, region_bounds: Dict[str, Any], step_x: int = 40, step_y: int = 35, settle_ms: int = 100) -> Dict[str, Any]:
    """在指定区域内进行鼠标扫描"""
    # 简化的区域扫描实现
    regions = []
    x_start = region_bounds["x"]
    y_start = region_bounds["y"]
    width = region_bounds["width"]
    height = region_bounds["height"]
    
    # 网格扫描
    for y in range(y_start, y_start + height, step_y):
        for x in range(x_start, x_start + width, step_x):
            # 模拟鼠标移动和检测变化
            # 这里应该调用实际的鼠标扫描逻辑
            regions.append({
                "bounds": {"x": x, "y": y, "width": step_x, "height": step_y},
                "stability_score": 0.7,
                "hover_hits": 5
            })
    
    return {"regions": regions}


def _perform_ocr_on_image(image) -> List[Dict[str, Any]]:
    """对图像执行OCR识别"""
    # 简化的OCR实现
    # 实际应该使用tesseract或其他OCR库
    return [
        {"text": "示例文本", "x": 10, "y": 10, "width": 100, "height": 20}
    ]


class SendMessageRequest(BaseModel):
    contact: Optional[str] = None
    message: str

class SetWindowRequest(BaseModel):
    width: int
    height: int
    x: int
    y: int


class WindowLockRequest(BaseModel):
    width: int
    height: int
    x: int
    y: int
    tolerance: int = 6
    retries: int = 2
    force_x11_fallback: bool = True
    activate_before_fix: bool = False


class FullScanRequest(BaseModel):
    profile_name: str = "default"
    template_type: str = "chat"  # "chat" 或 "contacts"
    timeout_seconds: int = 45
    include_mouse_scan: bool = True
    include_control_layer: bool = True
    persist_as_baseline: bool = True
    use_real_mouse_scan: bool = True
    scan_direction: str = "right_to_left"
    scan_step_x: int = 15
    scan_step_y: int = 20
    scan_settle_ms: int = 3000
    scan_max_points: int = 180
    scan_diff_threshold: int = 24
    scan_min_contour_area: int = 160
    scan_min_stable_hits: int = 3
    scan_overlay_alpha: float = 0.28


class FullScanTaskQuery(BaseModel):
    task_id: str


class ManualScanStartRequest(BaseModel):
    profile_name: str = "default"
    template_type: str = "chat"
    region_name: str = "manual_region"
    control_type: str = "button"
    diff_threshold: int = 14
    min_contour_area: int = 120
    require_quad: bool = True
    cursor_ignore_radius: int = 18
    listen_global_hotkeys: bool = True


class ManualScanCaptureRequest(BaseModel):
    session_id: str


class ManualScanFinishRequest(BaseModel):
    session_id: str


class ManualScanAbortRequest(BaseModel):
    session_id: str


class RegionAnnotation(BaseModel):
    region_id: str  # 新增：关联到5区域之一
    function: str
    name: Optional[str] = None
    clickable: bool = True
    needs_rescan_after_click: bool = False
    control_type: Optional[str] = None
    bounds: Optional[Dict[str, int]] = None
    confidence: float = 1.0
    notes: Optional[str] = None


class BuildProfileRequest(BaseModel):
    profile_name: str
    annotations: List[RegionAnnotation]
    strict_window_match: bool = True


class ImportProfileRequest(BaseModel):
    profile_name: str
    profile: Dict[str, Any]


def _manual_scan_create_session(state: Dict[str, Any]) -> None:
    with MANUAL_SCAN_SESSIONS_LOCK:
        MANUAL_SCAN_SESSIONS[state["session_id"]] = state


def _manual_scan_get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with MANUAL_SCAN_SESSIONS_LOCK:
        row = MANUAL_SCAN_SESSIONS.get(session_id)
        if not row:
            return None
        return row


def _manual_scan_pop_session(session_id: str) -> Optional[Dict[str, Any]]:
    with MANUAL_SCAN_SESSIONS_LOCK:
        return MANUAL_SCAN_SESSIONS.pop(session_id, None)


def _get_mouse_position_xdotool() -> Optional[Tuple[int, int]]:
    try:
        ret = subprocess.run(
            ["xdotool", "getmouselocation", "--shell"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if ret.returncode != 0:
            return None
        x = None
        y = None
        for line in (ret.stdout or "").splitlines():
            if line.startswith("X="):
                x = int(line.split("=", 1)[1])
            elif line.startswith("Y="):
                y = int(line.split("=", 1)[1])
        if x is None or y is None:
            return None
        return int(x), int(y)
    except Exception:
        return None


def _get_active_window_geometry_xdotool() -> Dict[str, Any]:
    try:
        active_ret = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if active_ret.returncode != 0:
            return {"ok": False, "error": (active_ret.stderr or "getactivewindow失败").strip()}

        wid = int((active_ret.stdout or "0").strip() or 0)
        geom_ret = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", str(wid)],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if geom_ret.returncode != 0:
            return {
                "ok": False,
                "window_id": wid,
                "error": (geom_ret.stderr or "getwindowgeometry失败").strip(),
            }

        info: Dict[str, Any] = {
            "ok": True,
            "window_id": wid,
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "name": "",
        }
        for line in (geom_ret.stdout or "").splitlines():
            if line.startswith("X="):
                info["x"] = int(line.split("=", 1)[1])
            elif line.startswith("Y="):
                info["y"] = int(line.split("=", 1)[1])
            elif line.startswith("WIDTH="):
                info["width"] = int(line.split("=", 1)[1])
            elif line.startswith("HEIGHT="):
                info["height"] = int(line.split("=", 1)[1])

        name_ret = subprocess.run(
            ["xdotool", "getwindowname", str(wid)],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if name_ret.returncode == 0:
            info["name"] = (name_ret.stdout or "").strip()

        return info
    except Exception as err:
        return {"ok": False, "error": str(err)}


def _build_atspi_coordinate_diagnostics(
    raw_controls: List[Dict[str, Any]],
    manager_window_info: Dict[str, Any],
    tool_window_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    wx = int(manager_window_info.get("x", 0) or 0)
    wy = int(manager_window_info.get("y", 0) or 0)
    ww = int(manager_window_info.get("width", 0) or 0)
    wh = int(manager_window_info.get("height", 0) or 0)

    tolerance = 2
    positioned_nodes: List[Dict[str, int]] = []
    for row in raw_controls or []:
        w = int(row.get("width", 0) or 0)
        h = int(row.get("height", 0) or 0)
        if w <= 0 or h <= 0:
            continue
        positioned_nodes.append({
            "x": int(row.get("x", 0) or 0),
            "y": int(row.get("y", 0) or 0),
            "width": w,
            "height": h,
        })

    total = len(positioned_nodes)
    if total == 0:
        return {
            "positioned_nodes": 0,
            "global_in_window_ratio": 0.0,
            "local_in_window_ratio": 0.0,
            "suspect_coordinate_bias": False,
            "note": "无可用位置信息节点",
        }

    global_hits = 0
    local_hits = 0
    for n in positioned_nodes:
        gx_ok = (n["x"] >= wx - tolerance) and (n["x"] + n["width"] <= wx + ww + tolerance)
        gy_ok = (n["y"] >= wy - tolerance) and (n["y"] + n["height"] <= wy + wh + tolerance)
        if gx_ok and gy_ok:
            global_hits += 1

        lx_ok = (n["x"] >= -tolerance) and (n["x"] + n["width"] <= ww + tolerance)
        ly_ok = (n["y"] >= -tolerance) and (n["y"] + n["height"] <= wh + tolerance)
        if lx_ok and ly_ok:
            local_hits += 1

    global_ratio = round(float(global_hits) / float(total), 4)
    local_ratio = round(float(local_hits) / float(total), 4)

    offset_samples_x: List[int] = []
    offset_samples_y: List[int] = []
    for n in positioned_nodes[:400]:
        lx_ok = (n["x"] >= -tolerance) and (n["x"] + n["width"] <= ww + tolerance)
        ly_ok = (n["y"] >= -tolerance) and (n["y"] + n["height"] <= wh + tolerance)
        if lx_ok and ly_ok:
            offset_samples_x.append(wx - n["x"])
            offset_samples_y.append(wy - n["y"])

    estimated_offset = {
        "x": int(statistics.median(offset_samples_x)) if offset_samples_x else 0,
        "y": int(statistics.median(offset_samples_y)) if offset_samples_y else 0,
    }

    manager_vs_tool: Dict[str, Any] = {}
    if isinstance(tool_window_info, dict) and tool_window_info.get("ok"):
        manager_vs_tool = {
            "delta_x": int(tool_window_info.get("x", 0) or 0) - wx,
            "delta_y": int(tool_window_info.get("y", 0) or 0) - wy,
            "delta_width": int(tool_window_info.get("width", 0) or 0) - ww,
            "delta_height": int(tool_window_info.get("height", 0) or 0) - wh,
        }

    suspect_bias = local_ratio > (global_ratio + 0.15)

    return {
        "positioned_nodes": total,
        "global_in_window_ratio": global_ratio,
        "local_in_window_ratio": local_ratio,
        "suspect_coordinate_bias": bool(suspect_bias),
        "estimated_global_offset_if_local": estimated_offset,
        "manager_window": {
            "x": wx,
            "y": wy,
            "width": ww,
            "height": wh,
        },
        "tool_window": tool_window_info or {},
        "manager_vs_tool_delta": manager_vs_tool,
    }


def _extract_manual_scan_rects(
    base_gray: np.ndarray,
    snap_gray: np.ndarray,
    diff_threshold: int,
    min_contour_area: int,
    require_quad: bool,
    cursor_rel_pos: Optional[Tuple[int, int]] = None,
    cursor_ignore_radius: int = 18,
) -> List[Dict[str, int]]:
    if base_gray.size == 0 or snap_gray.size == 0:
        return []

    diff = cv2.absdiff(base_gray, snap_gray)
    diff = cv2.GaussianBlur(diff, (3, 3), 0)

    if cursor_rel_pos:
        cx, cy = int(cursor_rel_pos[0]), int(cursor_rel_pos[1])
        if 0 <= cx < diff.shape[1] and 0 <= cy < diff.shape[0]:
            cursor_mask = np.ones_like(diff, dtype=np.uint8) * 255
            cv2.circle(cursor_mask, (cx, cy), max(6, int(cursor_ignore_radius)), 0, -1)
            diff = cv2.bitwise_and(diff, cursor_mask)

    mean_val = float(np.mean(diff))
    std_val = float(np.std(diff))
    adaptive_threshold = int(max(int(diff_threshold), min(96, mean_val + 1.0 * std_val)))
    _, binary_abs = cv2.threshold(diff, adaptive_threshold, 255, cv2.THRESH_BINARY)

    # 强化“鼠标停留后颜色加深”这类变化（base 比 snap 更亮）
    darken = cv2.subtract(base_gray, snap_gray)
    darken = cv2.GaussianBlur(darken, (3, 3), 0)
    darken_threshold = max(4, int(diff_threshold * 0.55))
    _, binary_darken = cv2.threshold(darken, darken_threshold, 255, cv2.THRESH_BINARY)

    binary = cv2.bitwise_or(binary_abs, binary_darken)

    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects: List[Dict[str, int]] = []
    min_contour_area = max(30, int(min_contour_area))
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_contour_area:
            continue

        if require_quad:
            peri = cv2.arcLength(contour, True)
            if peri <= 0:
                continue
            approx = cv2.approxPolyDP(contour, 0.03 * peri, True)
            if len(approx) < 4:
                continue

        bx, by, bw, bh = cv2.boundingRect(contour)
        if bw <= 2 or bh <= 2:
            continue
        rects.append({"x": int(bx), "y": int(by), "width": int(bw), "height": int(bh)})

    return _merge_rectangles(rects, padding=4)


def _upsert_manual_candidates(
    existing: List[Dict[str, Any]],
    incoming_rects: List[Dict[str, int]],
    region_name: str,
    control_type: str,
    iou_threshold: float = 0.45,
) -> Tuple[List[Dict[str, Any]], int]:
    if not incoming_rects:
        return existing, 0

    added = 0
    for rect in incoming_rects:
        merged = False
        for row in existing:
            if _rect_iou(row.get("bounds", {}), rect) >= iou_threshold:
                row["bounds"] = _rect_union(row.get("bounds", {}), rect)
                row["hover_hits"] = int(row.get("hover_hits", 1)) + 1
                merged = True
                break
        if merged:
            continue

        existing.append({
            "id": "",
            "name": f"{region_name}_{len(existing) + 1}",
            "type": control_type,
            "region_id": region_name,
            "ui_scene": region_name,
            "function": "unknown_action",
            "needs_rescan_after_click": False,
            "clickable_candidate": True,
            "source": "manual_space_capture",
            "hover_hits": 1,
            "bounds": {
                "x": int(rect.get("x", 0)),
                "y": int(rect.get("y", 0)),
                "width": int(rect.get("width", 0)),
                "height": int(rect.get("height", 0)),
            },
        })
        added += 1

    existing.sort(key=lambda x: -int(x.get("hover_hits", 0)))
    for idx, row in enumerate(existing):
        row["id"] = f"{region_name}_{idx}"
    return existing, added


def _render_manual_scan_annotated(base_image: np.ndarray, candidates: List[Dict[str, Any]]) -> np.ndarray:
    annotated = base_image.copy()
    overlay = annotated.copy()
    for item in candidates:
        b = item.get("bounds", {})
        x1 = int(b.get("x", 0))
        y1 = int(b.get("y", 0))
        w = int(b.get("width", 0))
        h = int(b.get("height", 0))
        if w <= 0 or h <= 0:
            continue
        x2 = x1 + w
        y2 = y1 + h
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (40, 30, 190), -1)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{item.get('id')}:{item.get('type') or 'control'}"
        cv2.putText(annotated, label[:54], (x1, max(16, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 255), 1, cv2.LINE_AA)
    return cv2.addWeighted(overlay, 0.25, annotated, 0.75, 0)


def _manual_scan_capture_once(state: Dict[str, Any]) -> Dict[str, Any]:
    manager = get_wechat_manager()
    baseline_gray = state.get("baseline_gray")
    if baseline_gray is None:
        raise HTTPException(status_code=400, detail="会话基准图缺失，请重新启动")

    snap = _capture_scan_image(manager)
    snap_gray = cv2.cvtColor(snap, cv2.COLOR_BGR2GRAY)

    cursor_rel_pos = None
    mouse_abs = _get_mouse_position_xdotool()
    if mouse_abs:
        wx = int(state.get("window_info", {}).get("x", 0))
        wy = int(state.get("window_info", {}).get("y", 0))
        cursor_rel_pos = (int(mouse_abs[0]) - wx, int(mouse_abs[1]) - wy)

    scan_region_bounds = state.get("scan_region_bounds") or {}
    region_x = int(scan_region_bounds.get("x", 0) or 0)
    region_y = int(scan_region_bounds.get("y", 0) or 0)
    region_w = int(scan_region_bounds.get("width", 0) or 0)
    region_h = int(scan_region_bounds.get("height", 0) or 0)

    if region_w > 0 and region_h > 0:
        x1 = max(0, region_x)
        y1 = max(0, region_y)
        x2 = min(baseline_gray.shape[1], region_x + region_w)
        y2 = min(baseline_gray.shape[0], region_y + region_h)
        if x2 > x1 and y2 > y1:
            base_for_diff = baseline_gray[y1:y2, x1:x2]
            snap_for_diff = snap_gray[y1:y2, x1:x2]

            cursor_for_diff = None
            if cursor_rel_pos:
                local_cx = int(cursor_rel_pos[0]) - x1
                local_cy = int(cursor_rel_pos[1]) - y1
                if 0 <= local_cx < (x2 - x1) and 0 <= local_cy < (y2 - y1):
                    cursor_for_diff = (local_cx, local_cy)

            local_rects = _extract_manual_scan_rects(
                base_gray=base_for_diff,
                snap_gray=snap_for_diff,
                diff_threshold=int(state.get("diff_threshold", 14)),
                min_contour_area=int(state.get("min_contour_area", 120)),
                require_quad=bool(state.get("require_quad", True)),
                cursor_rel_pos=cursor_for_diff,
                cursor_ignore_radius=int(state.get("cursor_ignore_radius", 18)),
            )
            rects = [
                {
                    "x": int(rect.get("x", 0)) + x1,
                    "y": int(rect.get("y", 0)) + y1,
                    "width": int(rect.get("width", 0)),
                    "height": int(rect.get("height", 0)),
                }
                for rect in local_rects
            ]
        else:
            rects = []
    else:
        rects = _extract_manual_scan_rects(
            base_gray=baseline_gray,
            snap_gray=snap_gray,
            diff_threshold=int(state.get("diff_threshold", 14)),
            min_contour_area=int(state.get("min_contour_area", 120)),
            require_quad=bool(state.get("require_quad", True)),
            cursor_rel_pos=cursor_rel_pos,
            cursor_ignore_radius=int(state.get("cursor_ignore_radius", 18)),
        )

    candidates = list(state.get("candidates", []))
    candidates, added = _upsert_manual_candidates(
        existing=candidates,
        incoming_rects=rects,
        region_name=str(state.get("region_name", "manual_region")),
        control_type=str(state.get("control_type", "button")),
        iou_threshold=0.45,
    )

    state["captures"] = int(state.get("captures", 0)) + 1
    state["raw_rects"] = int(state.get("raw_rects", 0)) + len(rects)
    state["candidates"] = candidates
    state["updated_at"] = datetime.now().isoformat()
    state["last_event"] = "space"

    return {
        "capture_index": int(state.get("captures", 0)),
        "rects_detected_this_capture": len(rects),
        "new_candidates_added": int(added),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _manual_scan_finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    candidates = list(state.get("candidates", []))
    baseline = state.get("baseline_image")
    if baseline is None:
        raise HTTPException(status_code=400, detail="会话基准图缺失")

    annotated = _render_manual_scan_annotated(baseline, candidates)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f"/tmp/wechat_manual_scan_{ts}.png"
    csv_path = f"/tmp/wechat_manual_scan_{ts}.csv"
    points_path = f"/tmp/wechat_manual_points_{ts}.json"

    cv2.imwrite(image_path, annotated)

    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("region_name,x1,y1,x2,y2,control_type\n")
        for row in candidates:
            b = row.get("bounds", {})
            x1 = int(b.get("x", 0))
            y1 = int(b.get("y", 0))
            x2 = x1 + int(b.get("width", 0))
            y2 = y1 + int(b.get("height", 0))
            f.write(f"{row.get('region_id')},{x1},{y1},{x2},{y2},{row.get('type', 'button')}\n")

    points_payload = {
        "profile_name": state.get("profile_name"),
        "template_type": state.get("template_type"),
        "region_name": state.get("region_name"),
        "generated_at": datetime.now().isoformat(),
        "points": [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "type": row.get("type"),
                "x": int(row.get("bounds", {}).get("x", 0)) + int(row.get("bounds", {}).get("width", 0)) // 2,
                "y": int(row.get("bounds", {}).get("y", 0)) + int(row.get("bounds", {}).get("height", 0)) // 2,
                "bounds": row.get("bounds", {}),
            }
            for row in candidates
        ],
    }
    with open(points_path, "w", encoding="utf-8") as f:
        json.dump(points_payload, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "captures": int(state.get("captures", 0)),
        "candidate_count": len(candidates),
        "annotated_image_path": image_path,
        "annotated_image_data": f"data:image/png;base64,{_encode_png_base64(annotated)}",
        "coordinate_file_path": csv_path,
        "points_file_path": points_path,
        "candidates": candidates,
        "message": "手动扫描完成，已输出标注图与坐标文件",
    }


def _manual_scan_hotkey_worker(session_id: str) -> None:
    try:
        try:
            from pynput import keyboard
        except Exception as import_err:
            state = _manual_scan_get_session(session_id)
            if state:
                state["status"] = "error"
                state["last_error"] = f"全局热键监听不可用: {import_err}"
                state["hotkey_listener_active"] = False
                state["updated_at"] = datetime.now().isoformat()
            return

        def on_press(key):
            state = _manual_scan_get_session(session_id)
            if not state:
                return False
            if state.get("status") not in ["running", "starting"]:
                return False

            try:
                if key == keyboard.Key.space:
                    _manual_scan_capture_once(state)
                    return True
                if key == keyboard.Key.enter:
                    result = _manual_scan_finalize(state)
                    state["status"] = "finished"
                    state["last_event"] = "enter"
                    state["final_result"] = result
                    state["updated_at"] = datetime.now().isoformat()
                    return False
                if key == keyboard.Key.esc:
                    state["status"] = "aborted"
                    state["last_event"] = "esc"
                    state["updated_at"] = datetime.now().isoformat()
                    return False
            except Exception as err:
                state["status"] = "error"
                state["last_error"] = str(err)
                state["updated_at"] = datetime.now().isoformat()
                return False
            return True

        state = _manual_scan_get_session(session_id)
        if state:
            state["status"] = "running"
            state["hotkey_listener_active"] = True
            state["updated_at"] = datetime.now().isoformat()

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except Exception as err:
        state = _manual_scan_get_session(session_id)
        if state:
            state["status"] = "error"
            state["last_error"] = str(err)
            state["updated_at"] = datetime.now().isoformat()
    finally:
        state = _manual_scan_get_session(session_id)
        if state:
            state["hotkey_listener_active"] = False
            state["updated_at"] = datetime.now().isoformat()


@router.post("/wechat/ui_profile/manual_scan/start")
async def start_manual_scan(request: ManualScanStartRequest):
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        if hasattr(manager, "activate_wechat"):
            manager.activate_wechat()
            _random_delay(0.08, 0.2)

        window_info = _safe_window_info(manager.get_wechat_window())
        baseline = _capture_scan_image(manager)
        baseline_gray = cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY)

        session_id = str(uuid.uuid4())
        regions = _load_regions_for_scan(
            profile_name=str(request.profile_name or "default"),
            template_type=str(request.template_type or "chat"),
            window_info=window_info,
        )

        requested_region = str(request.region_name or "").strip() or "chat_input"
        selected_region_id = requested_region if requested_region in regions else "chat_input"
        if selected_region_id not in regions and regions:
            selected_region_id = next(iter(regions.keys()))

        selected_region = regions.get(selected_region_id, {}) if isinstance(regions, dict) else {}
        selected_region_bounds = _normalize_region_bounds_for_window(selected_region.get("bounds", {}), window_info) if isinstance(selected_region, dict) else None

        state = {
            "session_id": session_id,
            "profile_name": str(request.profile_name or "default"),
            "template_type": str(request.template_type or "chat"),
            "region_name": str(selected_region_id or "chat_input"),
            "control_type": str(request.control_type or "button"),
            "diff_threshold": max(6, int(request.diff_threshold)),
            "min_contour_area": max(30, int(request.min_contour_area)),
            "require_quad": bool(request.require_quad),
            "cursor_ignore_radius": max(6, int(request.cursor_ignore_radius)),
            "window_info": window_info,
            "scan_region_bounds": selected_region_bounds,
            "baseline_image": baseline,
            "baseline_gray": baseline_gray,
            "captures": 0,
            "raw_rects": 0,
            "candidates": [],
            "status": "starting",
            "last_event": "start",
            "last_error": "",
            "final_result": None,
            "hotkey_listener_active": False,
            "listen_global_hotkeys": bool(request.listen_global_hotkeys),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        _manual_scan_create_session(state)

        if bool(request.listen_global_hotkeys):
            worker = threading.Thread(
                target=_manual_scan_hotkey_worker,
                args=(session_id,),
                daemon=True,
            )
            worker.start()
        else:
            state["status"] = "running"

        return {
            "success": True,
            "session_id": session_id,
            "selected_region": {
                "region_id": str(selected_region_id),
                "bounds": selected_region_bounds or {},
            },
            "window_lock": {
                "x": int(window_info.get("x", 0)),
                "y": int(window_info.get("y", 0)),
                "width": int(window_info.get("width", 0)),
                "height": int(window_info.get("height", 0)),
            },
            "baseline_image": f"data:image/png;base64,{_encode_png_base64(baseline)}",
            "listen_global_hotkeys": bool(request.listen_global_hotkeys),
            "message": "手动扫描已启动：仅比较所选区域，请在微信窗口按 空格 采样、回车完成、ESC退出",
        }
    except Exception as e:
        logger.error(f"启动手动扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动手动扫描失败: {str(e)}")


@router.get("/wechat/ui_profile/manual_scan/status")
async def get_manual_scan_status(session_id: str):
    state = _manual_scan_get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="手动扫描会话不存在")

    return {
        "success": True,
        "session": {
            "session_id": session_id,
            "profile_name": state.get("profile_name"),
            "template_type": state.get("template_type"),
            "region_name": state.get("region_name"),
            "captures": int(state.get("captures", 0)),
            "raw_rects": int(state.get("raw_rects", 0)),
            "candidate_count": len(state.get("candidates", [])),
            "status": state.get("status", "running"),
            "last_event": state.get("last_event", ""),
            "last_error": state.get("last_error", ""),
            "hotkey_listener_active": bool(state.get("hotkey_listener_active", False)),
            "listen_global_hotkeys": bool(state.get("listen_global_hotkeys", False)),
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
        },
    }


@router.post("/wechat/ui_profile/manual_scan/capture")
async def capture_manual_scan(request: ManualScanCaptureRequest):
    state = _manual_scan_get_session(request.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="手动扫描会话不存在")

    if state.get("status") in ["finished", "aborted", "error"]:
        raise HTTPException(status_code=409, detail=f"当前会话状态为 {state.get('status')}，不可继续采样")

    try:
        outcome = _manual_scan_capture_once(state)

        annotated = _render_manual_scan_annotated(state.get("baseline_image"), outcome.get("candidates", []))

        return {
            "success": True,
            "session_id": request.session_id,
            "capture_index": int(outcome.get("capture_index", 0)),
            "rects_detected_this_capture": int(outcome.get("rects_detected_this_capture", 0)),
            "new_candidates_added": int(outcome.get("new_candidates_added", 0)),
            "candidate_count": int(outcome.get("candidate_count", 0)),
            "annotated_image_data": f"data:image/png;base64,{_encode_png_base64(annotated)}",
            "candidates": outcome.get("candidates", []),
            "message": f"已记录第 {int(state.get('captures', 0))} 次采样",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动扫描采样失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动扫描采样失败: {str(e)}")


@router.post("/wechat/ui_profile/manual_scan/finish")
async def finish_manual_scan(request: ManualScanFinishRequest):
    state = _manual_scan_get_session(request.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="手动扫描会话不存在")

    try:
        if state.get("status") == "finished" and isinstance(state.get("final_result"), dict):
            result = dict(state.get("final_result") or {})
        elif state.get("status") == "aborted":
            raise HTTPException(status_code=409, detail="会话已被ESC退出，不可汇总")
        elif state.get("status") == "error":
            raise HTTPException(status_code=409, detail=f"会话异常: {state.get('last_error') or 'unknown'}")
        else:
            result = _manual_scan_finalize(state)
            state["status"] = "finished"
            state["last_event"] = "enter_api"
            state["final_result"] = result
            state["updated_at"] = datetime.now().isoformat()

        _manual_scan_pop_session(request.session_id)
        return {
            **result,
            "session_id": request.session_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"结束手动扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"结束手动扫描失败: {str(e)}")


@router.post("/wechat/ui_profile/manual_scan/abort")
async def abort_manual_scan(request: ManualScanAbortRequest):
    state = _manual_scan_get_session(request.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="手动扫描会话不存在")

    state["status"] = "aborted"
    state["last_event"] = "esc_api"
    state["updated_at"] = datetime.now().isoformat()
    _manual_scan_pop_session(request.session_id)

    return {
        "success": True,
        "session_id": request.session_id,
        "captures": int(state.get("captures", 0)),
        "message": "已强制退出手动扫描，未保存",
    }


@router.post("/wechat/ui_profile/fix_window")
async def fix_window_for_stable_analysis(request: WindowLockRequest):
    """在分析前固定微信窗口尺寸与位置，保证区域一致性"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        if request.activate_before_fix and hasattr(manager, "activate_wechat"):
            manager.activate_wechat()
            _random_delay(0.08, 0.2)

        before_info = _safe_window_info(manager.get_wechat_window())
        expected = {
            "width": int(request.width),
            "height": int(request.height),
            "x": int(request.x),
            "y": int(request.y),
        }

        from .layout_control import set_window_position

        set_window_position("wechat", expected["x"], expected["y"], expected["width"], expected["height"])

        locked = False
        after_info = before_info
        fallback_trace: List[Dict[str, Any]] = []
        for _ in range(max(1, int(request.retries) + 1)):
            _random_delay(0.12, 0.24)
            after_info = _safe_window_info(manager.get_wechat_window())
            locked = _is_window_locked(after_info, expected, int(request.tolerance))
            if locked:
                break

        if not locked and request.force_x11_fallback and int(before_info.get("id", 0)) > 0:
            fallback_result = _force_set_window_geometry_x11(
                int(before_info["id"]),
                expected["x"],
                expected["y"],
                expected["width"],
                expected["height"],
            )
            fallback_trace = fallback_result.get("trace", [])

            for _ in range(max(1, int(request.retries) + 1)):
                _random_delay(0.14, 0.28)
                after_info = _safe_window_info(manager.get_wechat_window())
                locked = _is_window_locked(after_info, expected, int(request.tolerance))
                if locked:
                    break

        before_geometry = (before_info.get("x"), before_info.get("y"), before_info.get("width"), before_info.get("height"))
        after_geometry = (after_info.get("x"), after_info.get("y"), after_info.get("width"), after_info.get("height"))
        geometry_unchanged = before_geometry == after_geometry
        fallback_all_ok = len(fallback_trace) > 0 and all(bool(item.get("ok")) for item in fallback_trace)
        likely_wm_or_wayland_restriction = (not locked) and geometry_unchanged and fallback_all_ok

        if locked:
            message = "窗口固定成功"
            reason = "strict_lock"
            suggestions: List[str] = []
        elif likely_wm_or_wayland_restriction:
            message = "窗口管理器限制：命令执行成功但窗口几何未变化"
            reason = "wm_restriction"
            suggestions = [
                "确认当前会话是X11而非Wayland（Wayland下窗口外部控制常受限）",
                "关闭窗口平铺/吸附规则后重试",
                "先手动取消最大化，再调用固定接口",
                "若无法改动窗口，直接以当前窗口几何作为稳定基线进行扫描",
            ]
        else:
            message = "窗口已尝试固定，但未完全达到目标尺寸/坐标"
            reason = "partial_or_failed_lock"
            suggestions = [
                "增加retries后重试",
                "调大tolerance到10~20做宽容校验",
                "先调用激活微信，再执行固定窗口",
            ]

        return {
            "success": True,
            "locked": locked,
            "tolerance": int(request.tolerance),
            "force_x11_fallback": bool(request.force_x11_fallback),
            "activate_before_fix": bool(request.activate_before_fix),
            "expected": expected,
            "before": before_info,
            "after": after_info,
            "fallback_trace": fallback_trace,
            "geometry_unchanged": geometry_unchanged,
            "reason": reason,
            "suggestions": suggestions,
            "message": message
        }
    except Exception as e:
        logger.error(f"固定窗口失败: {e}")
        raise HTTPException(status_code=500, detail=f"固定窗口失败: {str(e)}")


def _execute_full_scan(request: FullScanRequest, progress_callback: Optional[Any] = None, should_cancel: Optional[Any] = None) -> Dict[str, Any]:
    def _progress(progress: int, stage: str, message: str) -> None:
        if progress_callback:
            progress_callback(progress=int(max(0, min(100, progress))), stage=stage, message=message)

    def _ensure_not_cancelled() -> None:
        if should_cancel and bool(should_cancel()):
            raise ScanCancelledError("扫描任务已取消")

    manager = get_wechat_manager()
    _progress(2, "prepare", "准备激活微信窗口")
    if hasattr(manager, "activate_wechat"):
        manager.activate_wechat()
        _random_delay(0.08, 0.2)

    _ensure_not_cancelled()
    window_info = _safe_window_info(manager.get_wechat_window())
    regions_for_scan = _load_regions_for_scan(
        profile_name=request.profile_name,
        template_type=request.template_type,
        window_info=window_info,
    )

    _progress(8, "prepare", "获取当前窗口截图")
    screenshot_data = None
    try:
        screenshot = manager.capture_wechat_window()
        if screenshot is not None:
            _, buffer = cv2.imencode('.png', screenshot)
            screenshot_data = base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.warning(f"截图失败: {e}")

    _ensure_not_cancelled()
    base_scan_layer: List[Dict[str, Any]] = []
    mouse_scan_meta: Dict[str, Any] = {}
    if request.include_mouse_scan:
        _progress(12, "mouse_scan", "开始鼠标扫描")
        base_scan_layer, mouse_scan_meta = _collect_mouse_scan_layer_by_regions(
            manager=manager,
            window_info=window_info,
            regions=regions_for_scan,
            step_x=int(request.scan_step_x),
            step_y=int(request.scan_step_y),
            settle_ms=int(request.scan_settle_ms),
            max_points=int(request.scan_max_points),
            min_contour_area=int(request.scan_min_contour_area),
            min_stable_hits=int(request.scan_min_stable_hits),
            progress_callback=_progress,
            should_cancel=should_cancel,
        )
        mouse_scan_meta["legacy_mode_removed"] = True
        mouse_scan_meta["requested_use_real_mouse_scan"] = bool(request.use_real_mouse_scan)

    _ensure_not_cancelled()
    control_layer: List[Dict[str, Any]] = []
    if request.include_control_layer:
        _progress(82, "control_layer", "生成控件层")
        control_layer = _collect_control_layer(manager)

    _ensure_not_cancelled()
    _progress(88, "geometry", "生成几何层")
    geometry_layer = _build_geometry_layer(window_info)
    estimated_regions = regions_for_scan

    profile_payload = {
        "profile_name": request.profile_name,
        "template_type": request.template_type,
        "status": "baseline",
        "updated_at": datetime.now().isoformat(),
        "window_lock": {
            "x": window_info["x"],
            "y": window_info["y"],
            "width": window_info["width"],
            "height": window_info["height"],
        },
        "screenshot": screenshot_data,
        "regions": estimated_regions,
        "layers": {
            "base_scan_layer": base_scan_layer,
            "annotation_layer": [],
            "control_layer": control_layer,
            "geometry_layer": geometry_layer,
        },
        "execution": {
            "rescan_region_ids": [],
            "rescan_required_on_click": False,
        },
        "stable_elements": [],
        "mouse_scan_meta": mouse_scan_meta,
    }

    if request.persist_as_baseline:
        _ensure_not_cancelled()
        _progress(94, "persist", "保存扫描结果")
        store = _load_profile_store()
        store["profiles"][request.profile_name] = profile_payload
        _save_profile_store(store)

    _progress(100, "done", "全面扫描完成")
    return {
        "success": True,
        "profile_name": request.profile_name,
        "persisted": bool(request.persist_as_baseline),
        "window_lock": profile_payload["window_lock"],
        "base_scan_candidates": base_scan_layer,
        "layer_counts": {
            "base_scan_layer": len(base_scan_layer),
            "control_layer": len(control_layer),
            "annotation_layer": 0,
        },
        "mouse_scan_meta": mouse_scan_meta,
        "message": "全面扫描完成"
    }


@router.post("/wechat/ui_profile/full_scan")
async def full_scan_ui_layers(request: FullScanRequest):
    """全面扫描：生成基础层(hover扫描) + 控件层 + 几何层，可持久化为baseline"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        return _execute_full_scan(request)
    except ScanCancelledError:
        raise HTTPException(status_code=409, detail="扫描任务已取消")
    except Exception as e:
        logger.error(f"全面扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"全面扫描失败: {str(e)}")


def _run_full_scan_task(task_id: str, request_dict: Dict[str, Any]) -> None:
    _update_scan_task(
        task_id,
        status="running",
        stage="prepare",
        progress=1,
        message="开始执行扫描任务",
        started_at=datetime.now().isoformat(),
    )

    def _task_progress(progress: int, stage: str, message: str) -> None:
        _update_scan_task(task_id, progress=int(progress), stage=stage, message=message)

    def _task_should_cancel() -> bool:
        return _is_scan_task_cancel_requested(task_id)

    try:
        if _task_should_cancel():
            raise ScanCancelledError("扫描任务已取消")

        request = FullScanRequest(**request_dict)
        result = _execute_full_scan(request, progress_callback=_task_progress, should_cancel=_task_should_cancel)

        _update_scan_task(
            task_id,
            status="success",
            progress=100,
            stage="done",
            message="全面扫描完成",
            result=result,
            finished_at=datetime.now().isoformat(),
        )
    except ScanCancelledError as err:
        _update_scan_task(
            task_id,
            status="cancelled",
            stage="cancelled",
            message=str(err) or "扫描任务已取消",
            finished_at=datetime.now().isoformat(),
        )
    except Exception as err:
        logger.error(f"异步全面扫描失败(task_id={task_id}): {err}")
        _update_scan_task(
            task_id,
            status="error",
            stage="error",
            message="全面扫描失败",
            error=str(err),
            finished_at=datetime.now().isoformat(),
        )


@router.post("/wechat/ui_profile/full_scan_async/start")
async def start_full_scan_task(request: FullScanRequest):
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    task_id = str(uuid.uuid4())
    task_state = _create_scan_task_state(task_id, request)
    with SCAN_TASKS_LOCK:
        SCAN_TASKS[task_id] = task_state

    worker = threading.Thread(
        target=_run_full_scan_task,
        args=(task_id, request.model_dump()),
        daemon=True,
    )
    worker.start()

    return {
        "success": True,
        "task_id": task_id,
        "status": "queued",
        "message": "扫描任务已启动"
    }


@router.get("/wechat/ui_profile/full_scan_async/status")
async def get_full_scan_task_status(task_id: str):
    task = _get_scan_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    return {
        "success": True,
        "task": task,
    }


@router.post("/wechat/ui_profile/full_scan_async/cancel")
async def cancel_full_scan_task(request: FullScanTaskQuery):
    task = _get_scan_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    if task.get("status") in ["success", "error", "cancelled"]:
        return {
            "success": True,
            "task_id": request.task_id,
            "status": task.get("status"),
            "message": "任务已结束，无需取消",
        }

    _mark_scan_task_cancel_requested(request.task_id)
    return {
        "success": True,
        "task_id": request.task_id,
        "status": "cancelling",
        "message": "已请求取消扫描任务",
    }


@router.post("/wechat/ui_profile/switch_template")
async def switch_template(template_type: str):
    """切换到指定模板界面（聊天或联系人）"""
    if template_type not in ["chat", "contacts"]:
        raise HTTPException(status_code=400, detail="template_type必须是'chat'或'contacts'")
    
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()
        if hasattr(manager, "activate_wechat"):
            manager.activate_wechat()
            _random_delay(0.08, 0.2)

        # 模拟点击主菜单按钮切换模板
        # 这里需要根据实际UI结构调整坐标，暂时使用估算坐标
        window_info = _safe_window_info(manager.get_wechat_window())
        width = window_info["width"]
        height = window_info["height"]
        
        if template_type == "chat":
            # 点击聊天按钮（估算位置：底部左侧）
            click_x = int(width * 0.15)
            click_y = height - 30
        else:  # contacts
            # 点击联系人按钮（估算位置：底部右侧）
            click_x = int(width * 0.35)
            click_y = height - 30
        
        # 执行点击
        click_result = _humanized_coordinate_click(manager, {
            "x": click_x - 20, "y": click_y - 10, 
            "width": 40, "height": 20
        })
        
        if not click_result.get("success"):
            raise HTTPException(status_code=500, detail=f"模板切换失败: {click_result.get('reason')}")

        return {
            "success": True,
            "template_type": template_type,
            "message": f"已切换到{template_type}模板界面"
        }
    except Exception as e:
        logger.error(f"模板切换失败: {e}")
        raise HTTPException(status_code=500, detail=f"模板切换失败: {str(e)}")


class AnnotateRegionRequest(BaseModel):
    profile_name: str
    region_id: str
    bounds: Dict[str, int]
    name: Optional[str] = None
    notes: Optional[str] = None


class MultiLayerAnnotationRequest(BaseModel):
    profile_name: str
    region_id: str
    template_type: str = "chat"
    include_atspi: bool = True
    include_mouse_scan: bool = True
    include_ocr: bool = True
    manual_bounds: Optional[Dict[str, int]] = None


class ConfirmAnnotationRequest(BaseModel):
    profile_name: str
    region_id: str
    selected_layer: str  # "atspi", "mouse_scan", "ocr", "manual"
    bounds: Dict[str, int]
    confidence: float = 1.0
    notes: Optional[str] = None


@router.post("/wechat/ui_profile/annotate_region")
async def annotate_region(request: AnnotateRegionRequest):
    """提交单个区域的标注调整"""
    try:
        store = _load_profile_store()
        profile = store.get("profiles", {}).get(request.profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到对应profile")

        regions = profile.get("regions", {})
        if request.region_id not in regions:
            raise HTTPException(status_code=400, detail=f"无效的region_id: {request.region_id}")

        # 更新区域边界
        regions[request.region_id]["bounds"] = request.bounds
        if request.name:
            regions[request.region_id]["name"] = request.name
        if request.notes:
            regions[request.region_id]["notes"] = request.notes

        profile["regions"] = regions
        profile["updated_at"] = datetime.now().isoformat()
        _save_profile_store(store)

        return {
            "success": True,
            "profile_name": request.profile_name,
            "region_id": request.region_id,
            "message": "区域标注已更新"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"区域标注失败: {e}")
        raise HTTPException(status_code=500, detail=f"区域标注失败: {str(e)}")


@router.post("/wechat/ui_profile/annotate_multi_layer")
async def annotate_multi_layer(request: MultiLayerAnnotationRequest):
    """多层标注：AT-SPI + 鼠标扫描 + OCR+AI + 手动确认"""
    try:
        layers = {}
        
        # AT-SPI层标注
        if request.include_atspi:
            layers["atspi"] = _annotate_via_atspi(request.region_id, request.template_type)
        
        # 鼠标扫描层标注
        if request.include_mouse_scan:
            layers["mouse_scan"] = _annotate_via_mouse_scan(request.region_id, request.template_type)
        
        # OCR+AI层标注
        if request.include_ocr:
            layers["ocr_ai"] = _annotate_via_ocr_ai(request.region_id, request.template_type)
        
        # 手动层（如果提供）
        if request.manual_bounds:
            layers["manual"] = {
                "layer": "manual",
                "candidates": [{
                    "bounds": request.manual_bounds,
                    "confidence": 1.0,
                    "source": "manual"
                }],
                "success": True
            }
        
        return {
            "success": True,
            "profile_name": request.profile_name,
            "region_id": request.region_id,
            "layers": layers,
            "message": "多层标注完成"
        }
    except Exception as e:
        logger.error(f"多层标注失败: {e}")
        raise HTTPException(status_code=500, detail=f"多层标注失败: {str(e)}")


@router.post("/wechat/ui_profile/confirm_annotation")
async def confirm_annotation(request: ConfirmAnnotationRequest):
    """确认并保存选定的标注结果"""
    try:
        store = _load_profile_store()
        profile = store.get("profiles", {}).get(request.profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到对应profile")

        regions = profile.get("regions", {})
        if request.region_id not in regions:
            raise HTTPException(status_code=400, detail=f"无效的region_id: {request.region_id}")

        # 更新区域边界和元数据
        regions[request.region_id]["bounds"] = request.bounds
        regions[request.region_id]["confidence"] = request.confidence
        regions[request.region_id]["annotation_source"] = request.selected_layer
        if request.notes:
            regions[request.region_id]["notes"] = request.notes

        profile["regions"] = regions
        profile["updated_at"] = datetime.now().isoformat()
        _save_profile_store(store)

        return {
            "success": True,
            "profile_name": request.profile_name,
            "region_id": request.region_id,
            "selected_layer": request.selected_layer,
            "message": "标注确认已保存"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认标注失败: {e}")
        raise HTTPException(status_code=500, detail=f"确认标注失败: {str(e)}")


@router.post("/wechat/ui_profile/build")
async def build_stable_ui_profile(request: BuildProfileRequest):
    """融合标注层与控件层，构建稳定可执行的UI分析结果并保存"""
    try:
        store = _load_profile_store()
        profile = store.get("profiles", {}).get(request.profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到对应profile，请先执行full_scan")

        layers = profile.get("layers", {})
        base_scan_layer = layers.get("base_scan_layer", [])
        control_layer = layers.get("control_layer", [])

        candidate_by_id: Dict[str, Dict[str, Any]] = {}
        for row in base_scan_layer + control_layer:
            row_id = str(row.get("id", "")).strip()
            if row_id:
                candidate_by_id[row_id] = row

        annotation_layer: List[Dict[str, Any]] = []
        stable_elements: List[Dict[str, Any]] = []
        unresolved_annotations: List[Dict[str, Any]] = []

        for index, ann in enumerate(request.annotations):
            ann_dict = ann.model_dump()
            resolved_bounds = _resolve_annotation_bounds(ann_dict, candidate_by_id)
            if not resolved_bounds:
                unresolved_annotations.append({
                    "region_id": ann.region_id,
                    "reason": "未提供有效bounds，且无法在扫描/控件层找到对应region_id"
                })
                continue

            entry_id = ann.region_id if ann.region_id else f"annotated_{index}"
            name = ann.name or entry_id
            function_name = ann.function.strip()

            geometry = {
                "center_x": resolved_bounds["x"] + resolved_bounds["width"] // 2,
                "center_y": resolved_bounds["y"] + resolved_bounds["height"] // 2,
                "area": resolved_bounds["width"] * resolved_bounds["height"],
            }

            annotation_entry = {
                "id": entry_id,
                "name": name,
                "function": function_name,
                "clickable": bool(ann.clickable),
                "needs_rescan_after_click": bool(ann.needs_rescan_after_click),
                "control_type": ann.control_type or "unknown",
                "confidence": float(ann.confidence),
                "notes": ann.notes or "",
                "bounds": resolved_bounds,
                "geometry": geometry,
            }

            annotation_layer.append(annotation_entry)
            stable_elements.append(annotation_entry)

        rescan_region_ids = [
            item["id"] for item in stable_elements if item.get("needs_rescan_after_click")
        ]

        profile["status"] = "ready"
        profile["updated_at"] = datetime.now().isoformat()
        profile["layers"]["annotation_layer"] = annotation_layer
        profile["stable_elements"] = stable_elements
        profile["execution"] = {
            "rescan_region_ids": rescan_region_ids,
            "rescan_required_on_click": len(rescan_region_ids) > 0,
            "clickable_count": len([row for row in stable_elements if row.get("clickable")]),
        }

        if request.strict_window_match:
            manager = get_wechat_manager()
            current_window = _safe_window_info(manager.get_wechat_window())
            expected_window = profile.get("window_lock", {})
            profile["window_lock_match"] = _is_window_locked(current_window, expected_window, tolerance=6)
            profile["current_window"] = current_window

        store["profiles"][request.profile_name] = profile
        _save_profile_store(store)

        return {
            "success": True,
            "profile_name": request.profile_name,
            "status": profile["status"],
            "stable_element_count": len(stable_elements),
            "rescan_region_ids": rescan_region_ids,
            "unresolved_annotations": unresolved_annotations,
            "message": "标注融合完成，稳定配置已保存"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"构建稳定UI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"构建稳定UI配置失败: {str(e)}")


@router.get("/wechat/ui_profile/annotated_preview")
async def get_ui_profile_annotated_preview(profile_name: str):
    try:
        store = _load_profile_store()
        profile = store.get("profiles", {}).get(profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到对应profile")

        manager = get_wechat_manager()
        screenshot = _capture_scan_image(manager)

        layers = profile.get("layers", {}) if isinstance(profile, dict) else {}
        stable_elements = profile.get("stable_elements", []) if isinstance(profile, dict) else []
        annotation_layer = layers.get("annotation_layer", []) if isinstance(layers, dict) else []
        overlay_elements = stable_elements if isinstance(stable_elements, list) and stable_elements else annotation_layer

        normalized_elements: List[Dict[str, Any]] = []
        for idx, item in enumerate(overlay_elements):
            if not isinstance(item, dict):
                continue
            bounds = _normalize_bounds(item.get("bounds", {}))
            if bounds["width"] <= 0 or bounds["height"] <= 0:
                continue
            normalized_elements.append({
                "id": str(item.get("id") or f"annotated_{idx}"),
                "name": str(item.get("name") or item.get("id") or f"annotated_{idx}"),
                "type": str(item.get("control_type") or item.get("type") or "unknown"),
                "bounds": bounds,
            })

        annotated = _annotate_image(screenshot.copy(), normalized_elements)
        screenshot_base64 = _encode_png_base64(annotated)

        return {
            "success": True,
            "profile_name": profile_name,
            "annotated_count": len(normalized_elements),
            "screenshot": f"data:image/png;base64,{screenshot_base64}",
            "message": f"已生成标注预览图，标注数量 {len(normalized_elements)}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成UI配置标注预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成UI配置标注预览失败: {str(e)}")


@router.get("/wechat/ui_profile/get")
async def get_ui_profile(profile_name: str = "default"):
    """读取已保存的界面分析配置（设置文档）"""
    try:
        store = _load_profile_store()
        profile = store.get("profiles", {}).get(profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到对应profile")

        return {
            "success": True,
            "profile_name": profile_name,
            "profile": profile,
            "message": "读取成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取UI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取UI配置失败: {str(e)}")


@router.get("/wechat/ui_profile/list")
async def list_ui_profiles():
    """列出所有可直接调用的界面分析配置"""
    try:
        store = _load_profile_store()
        profiles = store.get("profiles", {})
        result = []
        for name, profile in profiles.items():
            stable_elements = profile.get("stable_elements", [])
            result.append({
                "profile_name": name,
                "status": profile.get("status", "unknown"),
                "updated_at": profile.get("updated_at", ""),
                "stable_element_count": len(stable_elements),
            })

        return {
            "success": True,
            "count": len(result),
            "profiles": result,
            "store_path": PROFILE_STORE_PATH,
        }
    except Exception as e:
        logger.error(f"列出UI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出UI配置失败: {str(e)}")


@router.get("/wechat/ui_profile/export")
async def export_ui_profile(profile_name: str = "default"):
    """导出单个profile（用于保存设置文件）"""
    try:
        store = _load_profile_store()
        profile = store.get("profiles", {}).get(profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到对应profile")

        return {
            "success": True,
            "profile_name": profile_name,
            "profile": profile,
            "exported_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出UI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出UI配置失败: {str(e)}")


@router.post("/wechat/ui_profile/import")
async def import_ui_profile(request: ImportProfileRequest):
    """导入单个profile（用于恢复设置文件）"""
    try:
        incoming = request.profile
        if not isinstance(incoming, dict):
            raise HTTPException(status_code=400, detail="profile格式无效")

        incoming.setdefault("profile_name", request.profile_name)
        incoming.setdefault("status", "ready")
        incoming.setdefault("updated_at", datetime.now().isoformat())
        incoming.setdefault("window_lock", {})
        incoming.setdefault("layers", {
            "base_scan_layer": [],
            "annotation_layer": [],
            "control_layer": [],
            "geometry_layer": {}
        })
        incoming.setdefault("execution", {
            "rescan_region_ids": [],
            "rescan_required_on_click": False
        })
        incoming.setdefault("stable_elements", [])

        store = _load_profile_store()
        store["profiles"][request.profile_name] = incoming
        _save_profile_store(store)

        return {
            "success": True,
            "profile_name": request.profile_name,
            "stable_element_count": len(incoming.get("stable_elements", [])),
            "message": "导入成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入UI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入UI配置失败: {str(e)}")


@router.post("/wechat/generate_annotated_screenshot")
async def generate_annotated_screenshot(request: Dict[str, Any]):
    """生成带有标注区域的窗口截图（用于区域标注完成后的确认预览）"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        profile_name = str(request.get("profile_name", "")).strip()
        if not profile_name:
            raise HTTPException(status_code=400, detail="profile_name不能为空")

        store = _load_profile_store()
        profile = (store.get("profiles") or {}).get(profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 '{profile_name}' 不存在")

        manager = get_wechat_manager()
        screenshot = manager.capture_full_window()
        screenshot = np.asarray(screenshot)

        if screenshot.ndim == 2:
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_GRAY2BGR)
        elif screenshot.ndim == 3 and screenshot.shape[2] == 1:
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_GRAY2BGR)
        elif screenshot.ndim == 3 and screenshot.shape[2] > 3:
            screenshot = screenshot[:, :, :3]

        if screenshot.dtype != np.uint8:
            screenshot = screenshot.astype(np.uint8, copy=False)

        screenshot = np.ascontiguousarray(screenshot).copy()

        regions = profile.get("regions", {}) or {}
        window_lock = profile.get("window_lock", {}) or {}
        lock_x = int(window_lock.get("x", 0) or 0)
        lock_y = int(window_lock.get("y", 0) or 0)

        image_height, image_width = screenshot.shape[:2]
        yellow = (0, 255, 255)
        drawn_count = 0

        def _inside_ratio(left: int, top: int, width: int, height: int) -> float:
            if width <= 0 or height <= 0:
                return 0.0
            right = left + width
            bottom = top + height
            inter_left = max(0, left)
            inter_top = max(0, top)
            inter_right = min(image_width, right)
            inter_bottom = min(image_height, bottom)
            inter_w = max(0, inter_right - inter_left)
            inter_h = max(0, inter_bottom - inter_top)
            inter_area = inter_w * inter_h
            total_area = width * height
            return inter_area / total_area if total_area > 0 else 0.0

        # 先判断本组坐标更像“窗口相对坐标”还是“屏幕绝对坐标”
        relative_score = 0.0
        absolute_score = 0.0
        for _, region_data in regions.items():
            bounds = (region_data or {}).get("bounds") or {}
            x = int(bounds.get("x", 0))
            y = int(bounds.get("y", 0))
            width = int(bounds.get("width", 0))
            height = int(bounds.get("height", 0))
            if width <= 0 or height <= 0:
                continue
            relative_score += _inside_ratio(x, y, width, height)
            absolute_score += _inside_ratio(x - lock_x, y - lock_y, width, height)

        use_absolute = absolute_score > relative_score

        for index, (region_id, region_data) in enumerate(regions.items()):
            bounds = (region_data or {}).get("bounds") or {}
            x = int(bounds.get("x", 0))
            y = int(bounds.get("y", 0))
            width = int(bounds.get("width", 0))
            height = int(bounds.get("height", 0))
            if width <= 0 or height <= 0:
                continue

            # 兼容两种坐标：
            # 1) 绝对屏幕坐标（减去 window_lock 偏移）
            # 2) 窗口相对坐标（直接使用）
            if use_absolute:
                draw_x, draw_y = x - lock_x, y - lock_y
            else:
                draw_x, draw_y = x, y

            x1 = max(0, draw_x)
            y1 = max(0, draw_y)
            x2 = min(image_width - 1, draw_x + width)
            y2 = min(image_height - 1, draw_y + height)
            if x2 <= x1 or y2 <= y1:
                continue

            cv2.rectangle(screenshot, (x1, y1), (x2, y2), yellow, 3)
            label = f"{index + 1}.{region_id}"
            cv2.putText(screenshot, label, (x1, max(y1 - 8, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, yellow, 2)
            drawn_count += 1

        ok, buffer = cv2.imencode('.png', screenshot)
        if not ok:
            raise HTTPException(status_code=500, detail="截图编码失败")

        screenshot_base64 = base64.b64encode(buffer).decode('utf-8')
        return {
            "success": True,
            "screenshot": screenshot_base64,
            "message": f"生成带有 {drawn_count} 个标注区域的截图成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成标注截图失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成标注截图失败: {str(e)}")

@router.post("/wechat/send_message")
async def send_wechat_message(request: SendMessageRequest):
    """发送微信消息"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        success = False

        if hasattr(manager, "send_message"):
            try:
                success = manager.send_message(request.message)
            except TypeError:
                if request.contact:
                    success = manager.send_message(request.contact, request.message)
                else:
                    return {
                        "success": False,
                        "message": "当前RPA实现需要联系人参数(contact)"
                    }
        elif hasattr(manager, "send_message_to_contact"):
            if request.contact:
                success = manager.send_message_to_contact(request.contact, request.message)
            else:
                return {
                    "success": False,
                    "message": "当前RPA实现需要联系人参数(contact)"
                }
        else:
            return {
                "success": False,
                "message": "当前RPA实现不支持发送消息接口"
            }
        
        return {
            "success": success,
            "message": "消息发送成功" if success else "消息发送失败"
        }
    except Exception as e:
        logger.error(f"发送微信消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送微信消息失败: {str(e)}")

@router.post("/wechat/capture_message_area")
async def capture_message_area():
    """截图微信消息区域"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        screenshot = manager.capture_message_area()
        
        # 获取截图形状信息
        height, width = screenshot.shape[:2]
        logger.info(f"消息区域截图尺寸: {width}x{height}")
        
        # 将截图数据转换为 Base64
        import base64
        import cv2
        _, buffer = cv2.imencode('.png', screenshot)
        screenshot_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "success": True,
            "screenshot": f"data:image/png;base64,{screenshot_base64}",
            "screenshot_shape": [height, width],
            "message": "截图成功"
        }
    except SystemExit:
        logger.error("系统退出信号被捕获")
        raise HTTPException(status_code=500, detail="系统退出信号被捕获")
    except KeyboardInterrupt:
        logger.error("键盘中断信号被捕获")
        raise HTTPException(status_code=500, detail="键盘中断信号被捕获")
    except MemoryError:
        logger.error("内存不足错误")
        raise HTTPException(status_code=500, detail="内存不足错误")
    except Exception as e:
        logger.error(f"截图消息区域失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图消息区域失败: {str(e)}")

@router.post("/wechat/fetch_ui_elements")
async def fetch_ui_elements():
    """获取界面元素"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        # 模拟获取界面元素
        elements = [
            {"id": "search_box", "type": "edit", "name": "搜索框"},
            {"id": "chat_list", "type": "list", "name": "聊天列表"},
            {"id": "message_input", "type": "edit", "name": "消息输入框"},
            {"id": "send_button", "type": "button", "name": "发送按钮"}
        ]
        
        return {
            "success": True,
            "elements": elements,
            "message": "获取界面元素成功"
        }
    except Exception as e:
        logger.error(f"获取界面元素失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取界面元素失败: {str(e)}")

@router.post("/wechat/analyze_ui_tree")
async def analyze_ui_tree():
    """分析控件树"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        # 模拟控件树分析
        analysis = {
            "root": {
                "type": "window",
                "name": "微信主窗口",
                "children": [
                    {
                        "type": "toolbar",
                        "name": "顶部工具栏",
                        "children": [
                            {"type": "button", "name": "聊天"},
                            {"type": "button", "name": "通讯录"},
                            {"type": "button", "name": "发现"},
                            {"type": "button", "name": "我"}
                        ]
                    },
                    {
                        "type": "panel",
                        "name": "聊天面板",
                        "children": [
                            {"type": "list", "name": "聊天列表"},
                            {"type": "button", "name": "新建聊天"}
                        ]
                    }
                ]
            }
        }
        
        return {
            "success": True,
            "analysis": analysis,
            "message": "分析控件树成功"
        }
    except Exception as e:
        logger.error(f"分析控件树失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析控件树失败: {str(e)}")

@router.post("/humanized-input")
async def humanized_input_endpoint(text: str):
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

# 添加AT-SPI相关的兼容接口
@router.post("/atspi/click_control")
async def click_control_by_name_endpoint(control_name: str):
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
async def input_text_to_control_endpoint(control_name: str, text: str):
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
async def get_text_from_control_endpoint(control_name: str):
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


@router.post("/atspi/tree_snapshot")
@router.post("/rpa/atspi/tree_snapshot")
async def get_atspi_tree_snapshot(
    role_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    max_nodes: int = 5000,
    auto_activate: bool = False,
    deep_search: bool = True,
    include_common_keywords: bool = False,
    extra_terms: Optional[str] = None,
    require_keyword_match: Optional[bool] = None,
    prefer_tree: bool = True,
    max_depth: int = -1,
    export_json: bool = False,
    export_path: Optional[str] = None,
    deduplicate: bool = False,
):
    """获取AT-SPI控件树快照（名称/角色/文本/位置/尺寸）"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")

    try:
        manager = get_wechat_manager()

        activated = False
        activation_settle_seconds = 0.0
        if auto_activate and hasattr(manager, "activate_wechat"):
            activated = bool(manager.activate_wechat())
            if activated:
                activation_settle_seconds = 2.0
                _random_delay(2.0, 2.2)

        manager_window_info = {}
        if hasattr(manager, "get_wechat_window"):
            try:
                manager_window_info = _safe_window_info(manager.get_wechat_window())
            except Exception as err:
                logger.warning(f"获取微信窗口信息失败: {err}")

        role_kw = (role_filter or "").strip().lower()
        requested_max_nodes = int(max_nodes)
        # max_nodes<=0 视为尽可能全量
        if requested_max_nodes <= 0:
            requested_max_nodes = 20000
        limit = max(1, min(requested_max_nodes, 20000))
        snapshot_limit = limit
        if deep_search:
            snapshot_limit = min(20000, max(limit * 4, 800))

        keywords = _build_atspi_search_keywords(
            name_filter=name_filter,
            extra_terms=extra_terms,
            include_common_keywords=include_common_keywords,
        )
        keyword_required = require_keyword_match
        if keyword_required is None:
            keyword_required = bool(name_filter or extra_terms)

        raw_mode = "control_snapshot"
        raw_controls: List[Dict[str, Any]] = []
        tree_attempted = False
        tree_nodes_count = 0
        tree_error = ""
        if prefer_tree and hasattr(manager, "get_atspi_tree_snapshot"):
            tree_attempted = True
            try:
                raw_controls = manager.get_atspi_tree_snapshot(snapshot_limit, int(max_depth))
                tree_nodes_count = len(raw_controls)
                raw_mode = "tree_snapshot"
            except Exception as tree_err:
                logger.warning(f"AT-SPI树快照失败，回退普通快照: {tree_err}")
                tree_error = str(tree_err)
                raw_controls = []

        if not raw_controls and hasattr(manager, "get_atspi_control_snapshot"):
            raw_controls = manager.get_atspi_control_snapshot(snapshot_limit)
            raw_mode = "control_snapshot"

        # 无过滤模式下，若树快照节点异常偏少，则自动回退普通快照并合并，避免只拿到顶层少量节点
        no_filter_mode = (
            not role_kw
            and not str(name_filter or "").strip()
            and not str(extra_terms or "").strip()
            and not bool(keyword_required)
            and not bool(deduplicate)
        )
        if no_filter_mode and hasattr(manager, "get_atspi_control_snapshot") and len(raw_controls) < 10:
            try:
                fallback_controls = manager.get_atspi_control_snapshot(snapshot_limit)
                if isinstance(fallback_controls, list) and len(fallback_controls) > len(raw_controls):
                    merged: List[Dict[str, Any]] = []
                    seen = set()
                    for row in list(raw_controls) + list(fallback_controls):
                        key = (
                            int(row.get("index", -1) or -1),
                            int(row.get("x", 0) or 0),
                            int(row.get("y", 0) or 0),
                            int(row.get("width", 0) or 0),
                            int(row.get("height", 0) or 0),
                            str(row.get("name", "") or "").strip(),
                            str(row.get("role", "") or "").strip(),
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        merged.append(row)
                    raw_controls = merged
                    raw_mode = "tree_plus_control_snapshot"
            except Exception as merge_err:
                logger.warning(f"AT-SPI普通快照补全失败: {merge_err}")

        tool_window_info = _get_active_window_geometry_xdotool()
        coordinate_diagnostics = _build_atspi_coordinate_diagnostics(
            raw_controls=raw_controls,
            manager_window_info=manager_window_info,
            tool_window_info=tool_window_info,
        )

        nodes = []
        dedup_keys = set()
        for row in raw_controls:
            index = int(row.get("index", len(nodes)))
            role_value = str(row.get("role", "") or "")
            name_value = str(row.get("name", "") or "")
            text_value = str(row.get("text", "") or "")

            if role_kw and role_kw not in role_value.lower():
                continue

            searchable = f"{name_value} {text_value} {role_value}".lower()
            matched_keywords = [term for term in keywords if _atspi_term_hit(searchable, term)]
            if keyword_required and not matched_keywords:
                continue

            x = int(row.get("x", 0) or 0)
            y = int(row.get("y", 0) or 0)
            width = int(row.get("width", 0) or 0)
            height = int(row.get("height", 0) or 0)
            depth_value = int(row.get("depth", 0) or 0)
            parent_index_value = int(row.get("parent_index", -1) or -1)
            path_value = str(row.get("path", f"Root -> Node[{index}]"))

            if deduplicate:
                dedup_key = (name_value.strip().lower(), role_value.strip().lower(), x, y, width, height)
                if dedup_key in dedup_keys:
                    continue
                dedup_keys.add(dedup_key)

            match_score = 0.0
            if matched_keywords:
                match_score += min(1.0, 0.2 * len(matched_keywords))
            if name_value and text_value:
                match_score += 0.1
            if width > 0 and height > 0:
                match_score += 0.1
            if "button" in role_value.lower() or "entry" in role_value.lower() or "text" in role_value.lower():
                match_score += 0.1

            node = {
                "node_id": f"node_{index}",
                "index": index,
                "depth": depth_value,
                "parent_index": parent_index_value,
                "path": path_value,
                "name": name_value,
                "role": role_value,
                "text": text_value,
                "bounds": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "center_x": x + width // 2,
                    "center_y": y + height // 2,
                },
                "clickable_hint": "button" in role_value.lower() or "menu" in role_value.lower(),
                "matched_keywords": matched_keywords[:12],
                "match_score": round(match_score, 3),
            }
            nodes.append(node)

        nodes.sort(
            key=lambda item: (
                float(item.get("match_score", 0.0)),
                int(item.get("bounds", {}).get("width", 0)) * int(item.get("bounds", {}).get("height", 0)),
            ),
            reverse=True,
        )
        nodes = nodes[:limit]

        export_file = ""
        if export_json:
            if export_path:
                export_file = export_path
            else:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_file = f"/tmp/wechat_atspi_tree_{ts}.json"
            payload = {
                "success": True,
                "count": len(nodes),
                "generated_at": datetime.now().isoformat(),
                "nodes": nodes,
                "filters": {
                    "role_filter": role_filter or "",
                    "name_filter": name_filter or "",
                    "max_nodes": limit,
                    "snapshot_limit": snapshot_limit,
                    "auto_activate": auto_activate,
                    "deep_search": deep_search,
                    "include_common_keywords": include_common_keywords,
                    "extra_terms": extra_terms or "",
                    "require_keyword_match": keyword_required,
                    "expanded_keywords": keywords,
                    "prefer_tree": prefer_tree,
                    "max_depth": max_depth,
                    "raw_mode": raw_mode,
                    "activation_settle_seconds": activation_settle_seconds,
                    "coordinate_diagnostics": coordinate_diagnostics,
                },
            }
            try:
                with open(export_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception as export_err:
                logger.warning(f"AT-SPI树导出失败: {export_err}")
                export_file = ""

        return {
            "success": True,
            "nodes": nodes,
            "count": len(nodes),
            "filters": {
                "role_filter": role_filter or "",
                "name_filter": name_filter or "",
                "max_nodes": limit,
                "snapshot_limit": snapshot_limit,
                "auto_activate": auto_activate,
                "deep_search": deep_search,
                "include_common_keywords": include_common_keywords,
                "extra_terms": extra_terms or "",
                "require_keyword_match": keyword_required,
                "expanded_keywords": keywords,
                "prefer_tree": prefer_tree,
                "max_depth": max_depth,
                "raw_mode": raw_mode,
                "tree_attempted": tree_attempted,
                "tree_nodes_count": tree_nodes_count,
                "tree_error": tree_error,
                "deduplicate": deduplicate,
                "activation_settle_seconds": activation_settle_seconds,
                "coordinate_diagnostics": coordinate_diagnostics,
            },
            "activated": activated,
            "export_file": export_file,
            "message": f"AT-SPI快照完成，返回 {len(nodes)} 个节点"
        }
    except Exception as e:
        logger.error(f"获取AT-SPI控件树快照失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取AT-SPI控件树快照失败: {str(e)}")


@router.post("/atspi/click_by_bounds")
@router.post("/rpa/atspi/click_by_bounds")
async def click_by_bounds(
    x: int,
    y: int,
    width: int = 0,
    height: int = 0,
    precise: bool = False,
    capture_validation: bool = True,
):
    """按屏幕绝对坐标执行拟人化点击（用于AT-SPI节点验证）"""
    try:
        raw_x = int(x)
        raw_y = int(y)
        target_x = raw_x
        target_y = raw_y
        w = max(0, int(width))
        h = max(0, int(height))
        offset_x = 0
        offset_y = 0

        # 当提供了宽高时，x/y按边界左上角处理，点击中心点更稳定
        if w > 0 and h > 0:
            target_x = raw_x + w // 2
            target_y = raw_y + h // 2

        # 非精确模式保留少量拟人化偏移
        if not precise:
            if w > 0:
                offset_x = random.randint(-max(1, w // 8), max(1, w // 8))
                target_x += offset_x
            if h > 0:
                offset_y = random.randint(-max(1, h // 8), max(1, h // 8))
                target_y += offset_y

        manager = None
        window_info = None
        before_image = None

        if capture_validation:
            try:
                manager = get_wechat_manager()
                if hasattr(manager, "get_wechat_window"):
                    window_info = _safe_window_info(manager.get_wechat_window())
                if hasattr(manager, "capture_full_window"):
                    before_image = _ensure_image_ndarray(manager.capture_full_window())
            except Exception as capture_err:
                logger.warning(f"点击前截图获取失败: {capture_err}")

        pre_delay = _random_delay(0.09, 0.28)
        move_ret = subprocess.run(
            ["xdotool", "mousemove", "--sync", str(target_x), str(target_y)],
            capture_output=True,
            text=True,
            timeout=3
        )
        if move_ret.returncode != 0:
            return {
                "success": False,
                "message": "坐标移动失败",
                "reason": move_ret.stderr.strip() or move_ret.stdout.strip() or "unknown"
            }

        _random_delay(0.05, 0.14)
        click_ret = subprocess.run(
            ["xdotool", "click", "1"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if click_ret.returncode != 0:
            return {
                "success": False,
                "message": "坐标点击失败",
                "reason": click_ret.stderr.strip() or click_ret.stdout.strip() or "unknown"
            }

        actual_mouse_x = target_x
        actual_mouse_y = target_y
        try:
            mouse_ret = subprocess.run(
                ["xdotool", "getmouselocation", "--shell"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if mouse_ret.returncode == 0:
                for line in (mouse_ret.stdout or "").splitlines():
                    if line.startswith("X="):
                        actual_mouse_x = int(line.split("=", 1)[1])
                    elif line.startswith("Y="):
                        actual_mouse_y = int(line.split("=", 1)[1])
        except Exception as mouse_err:
            logger.warning(f"获取鼠标位置失败: {mouse_err}")

        after_image = None
        if capture_validation and manager is not None:
            try:
                if hasattr(manager, "capture_full_window"):
                    after_image = _ensure_image_ndarray(manager.capture_full_window())
            except Exception as capture_err:
                logger.warning(f"点击后截图获取失败: {capture_err}")

        validation_images = {
            "before_data": "",
            "after_data": "",
            "before_path": "",
            "after_path": "",
        }
        click_measure = {
            "target": {"x": target_x, "y": target_y},
            "actual_mouse": {"x": actual_mouse_x, "y": actual_mouse_y},
            "delta": {"x": actual_mouse_x - target_x, "y": actual_mouse_y - target_y},
            "distance": round(float(np.hypot(actual_mouse_x - target_x, actual_mouse_y - target_y)), 2),
        }

        if capture_validation and window_info and (before_image is not None or after_image is not None):
            wx = int(window_info.get("x", 0))
            wy = int(window_info.get("y", 0))

            def _draw_markers(image: np.ndarray, label: str) -> np.ndarray:
                canvas = image.copy()
                target_rel = (max(0, target_x - wx), max(0, target_y - wy))
                actual_rel = (max(0, actual_mouse_x - wx), max(0, actual_mouse_y - wy))

                cv2.drawMarker(canvas, target_rel, (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=18, thickness=2)
                cv2.putText(canvas, "target", (target_rel[0] + 8, max(18, target_rel[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)

                cv2.drawMarker(canvas, actual_rel, (0, 255, 255), markerType=cv2.MARKER_TILTED_CROSS, markerSize=16, thickness=2)
                cv2.putText(canvas, "actual", (actual_rel[0] + 8, max(18, actual_rel[1] + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

                cv2.line(canvas, target_rel, actual_rel, (255, 0, 0), 1)
                cv2.putText(
                    canvas,
                    f"{label} dx={click_measure['delta']['x']} dy={click_measure['delta']['y']} d={click_measure['distance']}",
                    (12, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 0),
                    1,
                    cv2.LINE_AA,
                )
                return canvas

            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            if before_image is not None:
                before_marked = _draw_markers(before_image, "before")
                before_path = f"/tmp/atspi_click_before_{ts}.png"
                cv2.imwrite(before_path, before_marked)
                validation_images["before_path"] = before_path
                validation_images["before_data"] = f"data:image/png;base64,{_encode_png_base64(before_marked)}"

            if after_image is not None:
                after_marked = _draw_markers(after_image, "after")
                after_path = f"/tmp/atspi_click_after_{ts}.png"
                cv2.imwrite(after_path, after_marked)
                validation_images["after_path"] = after_path
                validation_images["after_data"] = f"data:image/png;base64,{_encode_png_base64(after_marked)}"

        return {
            "success": True,
            "message": "坐标点击验证完成",
            "precise": precise,
            "capture_validation": capture_validation,
            "input": {"x": raw_x, "y": raw_y, "width": w, "height": h},
            "base_target": {
                "x": raw_x + (w // 2 if w > 0 else 0),
                "y": raw_y + (h // 2 if h > 0 else 0)
            },
            "offset": {"x": offset_x, "y": offset_y},
            "target": {"x": target_x, "y": target_y},
            "click_measure": click_measure,
            "validation_images": validation_images,
            "delay": pre_delay
        }
    except Exception as e:
        logger.error(f"按坐标点击失败: {e}")
        raise HTTPException(status_code=500, detail=f"按坐标点击失败: {str(e)}")

# 添加UI元素分析功能
@router.post("/wechat/analyze_ui_elements")
async def analyze_ui_elements():
    """分析微信界面元素"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        formatted_elements = _extract_ui_elements(manager)
        
        return {
            "success": True,
            "elements": formatted_elements,
            "element_count": len(formatted_elements),
            "message": f"发现 {len(formatted_elements)} 个界面元素"
        }
    except Exception as e:
        logger.error(f"分析界面元素失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析界面元素失败: {str(e)}")

@router.post("/wechat/find_all_buttons")
async def find_all_buttons():
    """查找所有按钮"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        buttons = manager.find_all_buttons()
        
        formatted_buttons = []
        for i, region in enumerate(buttons):
            formatted_buttons.append({
                "id": f"button_{i}",
                "type": "button",
                "name": f"Button {i}",
                "bounds": {
                    "x": region.x,
                    "y": region.y,
                    "width": region.width,
                    "height": region.height
                }
            })
        
        return {
            "success": True,
            "buttons": formatted_buttons,
            "message": f"发现 {len(formatted_buttons)} 个按钮"
        }
    except Exception as e:
        logger.error(f"查找按钮失败: {e}")
        raise HTTPException(status_code=500, detail=f"查找按钮失败: {str(e)}")

# 添加点击特定元素的功能
@router.post("/wechat/click_element")
async def click_element(element_id: str):
    """点击特定界面元素"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        request_start = time.perf_counter()
        manager = get_wechat_manager()

        strategy_trace: List[Dict[str, Any]] = []

        # 1) 优先使用AT-SPI语义点击
        atspi_start = time.perf_counter()
        try:
            success = manager.click_control_by_atspi(element_id)
            strategy_trace.append({
                "strategy": "atspi_click",
                "target": element_id,
                "success": bool(success),
                "elapsed_ms": _elapsed_ms(atspi_start)
            })
            if success:
                return {
                    "success": True,
                    "message": f"成功通过ATSPI点击控件: {element_id}",
                    "strategy": "atspi_click",
                    "trace": strategy_trace,
                    "total_elapsed_ms": _elapsed_ms(request_start)
                }
        except Exception as e:
            strategy_trace.append({
                "strategy": "atspi_click",
                "target": element_id,
                "success": False,
                "reason": str(e),
                "elapsed_ms": _elapsed_ms(atspi_start)
            })

        # 2) 回退到坐标拟人化点击
        bounds = _get_element_bounds_by_id(manager, element_id)
        if bounds:
            coord_start = time.perf_counter()
            try:
                coord_result = _humanized_coordinate_click(manager, bounds)
                strategy_trace.append({
                    "strategy": "coordinate_click",
                    "bounds": bounds,
                    **coord_result,
                    "elapsed_ms": _elapsed_ms(coord_start)
                })
                if coord_result.get("success"):
                    return {
                        "success": True,
                        "message": f"成功通过坐标拟人化点击控件: {element_id}",
                        "strategy": "coordinate_click",
                        "trace": strategy_trace,
                        "total_elapsed_ms": _elapsed_ms(request_start)
                    }
            except Exception as e:
                strategy_trace.append({
                    "strategy": "coordinate_click",
                    "bounds": bounds,
                    "success": False,
                    "reason": str(e),
                    "elapsed_ms": _elapsed_ms(coord_start)
                })
        else:
            strategy_trace.append({
                "strategy": "coordinate_click",
                "success": False,
                "reason": "未找到元素坐标",
                "elapsed_ms": 0
            })

        # 3) 键盘兜底（发送类元素优先）
        if _is_send_like_element(element_id):
            keyboard_start = time.perf_counter()
            try:
                keyboard_result = _keyboard_send_fallback()
                strategy_trace.append({
                    "strategy": "keyboard_fallback",
                    **keyboard_result,
                    "elapsed_ms": _elapsed_ms(keyboard_start)
                })
                if keyboard_result.get("success"):
                    return {
                        "success": True,
                        "message": f"AT-SPI/坐标点击失败，已通过键盘兜底发送: {element_id}",
                        "strategy": "keyboard_fallback",
                        "trace": strategy_trace,
                        "total_elapsed_ms": _elapsed_ms(request_start)
                    }
            except Exception as e:
                strategy_trace.append({
                    "strategy": "keyboard_fallback",
                    "success": False,
                    "reason": str(e),
                    "elapsed_ms": _elapsed_ms(keyboard_start)
                })

        return {
            "success": False,
            "message": f"无法点击控件: {element_id}",
            "strategy": "failed",
            "trace": strategy_trace,
            "total_elapsed_ms": _elapsed_ms(request_start)
        }
    except Exception as e:
        logger.error(f"点击元素失败: {e}")
        raise HTTPException(status_code=500, detail=f"点击元素失败: {str(e)}")

# 添加缺失的布局控制API
@router.post("/layout_control/wechat/set_window")
async def set_window_size_and_position(width: int, height: int, x: int, y: int):
    """设置微信窗口大小和位置 - 兼容前端路径"""
    try:
        # 导入布局控制相关功能
        from .layout_control import set_window_position, get_screen_size
        
        # 实际设置窗口大小和位置
        success = set_window_position("wechat", x, y, width, height)
        
        result = {
            "success": True,
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "message": f"窗口已设置为 {width}x{height} 位置 ({x}, {y})"
        }
        
        if not success:
            result["warning"] = "窗口位置设置可能未完全生效，请检查系统权限"
        
        return result
    except Exception as e:
        logger.error(f"窗口大小设置失败: {e}")
        return {"success": False, "error": str(e)}

# 添加截图完整窗口的API
@router.post("/wechat/capture_full_window")
async def capture_full_window():
    """截图完整微信窗口"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        screenshot = _ensure_image_ndarray(manager.capture_full_window())
        
        # 获取截图形状信息
        height, width = screenshot.shape[:2]
        logger.info(f"完整窗口截图尺寸: {width}x{height}")
        
        screenshot_base64 = _encode_png_base64(screenshot)
        
        return {
            "success": True,
            "screenshot": f"data:image/png;base64,{screenshot_base64}",
            "screenshot_shape": [height, width],
            "message": "截图成功"
        }
    except SystemExit:
        logger.error("系统退出信号被捕获")
        raise HTTPException(status_code=500, detail="系统退出信号被捕获")
    except KeyboardInterrupt:
        logger.error("键盘中断信号被捕获")
        raise HTTPException(status_code=500, detail="键盘中断信号被捕获")
    except MemoryError:
        logger.error("内存不足错误")
        raise HTTPException(status_code=500, detail="内存不足错误")
    except Exception as e:
        logger.error(f"截图完整窗口失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图完整窗口失败: {str(e)}")

# 添加标注所有UI元素的API
@router.post("/wechat/capture_and_annotate_all_elements")
async def capture_and_annotate_all_elements():
    """截图并标注所有UI元素"""
    if not rpa_available:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    
    try:
        manager = get_wechat_manager()
        # 避免直接调用C++高风险接口（可能触发进程级SIGABRT）
        if hasattr(manager, "capture_full_window"):
            screenshot = manager.capture_full_window()
        else:
            screenshot = manager.capture_message_area()

        screenshot = _ensure_image_ndarray(screenshot)
        elements = []
        try:
            elements = _extract_ui_elements(manager)
            screenshot = _annotate_image(screenshot, elements)
        except Exception as annotate_error:
            logger.warning(f"Python层UI标注失败，返回原始截图: {annotate_error}")

        screenshot_base64 = _encode_png_base64(screenshot)
        height, width = screenshot.shape[:2]
        
        return {
            "success": True,
            "screenshot": f"data:image/png;base64,{screenshot_base64}",
            "screenshot_shape": [height, width],
            "elements": elements,
            "element_count": len(elements),
            "message": f"截图并标注完成，共 {len(elements)} 个元素"
        }
    except SystemExit:
        logger.error("系统退出信号被捕获")
        raise HTTPException(status_code=500, detail="系统退出信号被捕获")
    except KeyboardInterrupt:
        logger.error("键盘中断信号被捕获")
        raise HTTPException(status_code=500, detail="键盘中断信号被捕获")
    except MemoryError:
        logger.error("内存不足错误")
        raise HTTPException(status_code=500, detail="内存不足错误")
    except Exception as e:
        logger.error(f"截图并标注所有UI元素失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图并标注所有UI元素失败: {str(e)}")