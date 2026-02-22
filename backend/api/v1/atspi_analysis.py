from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import delete, func, or_, text
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import importlib
import logging
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.parse

import cv2

from db.session import get_session
from db.models import WechatATSPINode
from backend.core.atspi_tree_service import ATSPIQueryOptions, collect_best_snapshot

logger = logging.getLogger(__name__)
router = APIRouter()

# 导入 C++ RPA 模块
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
    logger.warning(f"AT-SPI分析模块加载失败: {e}")
    WeChatManager = None
    rpa_available = False


_CAPTURE_ROOT = Path("data/atspi_capture")
_CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)

_ocr_engine: Any = None
_ocr_init_error: Optional[str] = None


def _get_wechat_manager() -> Any:
    if not rpa_available or not WeChatManager:
        raise HTTPException(status_code=500, detail="C++ RPA模块不可用")
    manager = WeChatManager()
    if not manager.initialize():
        raise HTTPException(status_code=500, detail="微信管理器初始化失败")
    return manager


def _build_path(parent_path: str, child_index: int) -> str:
    if not parent_path:
        return "root"
    return f"{parent_path}/child[{child_index}]"


def _to_two_digit(num: int) -> str:
    value = int(num) if int(num) >= 0 else 0
    if value > 99:
        value = 99
    return f"{value:02d}"


def _encode_path_and_depth(access_path: str, depth: int) -> Tuple[str, str]:
    # 规则：root=99，后续 child 索引固定两位并用 | 分隔
    path = str(access_path or "").strip().lower()
    child_indexes = [int(match) for match in re.findall(r"child\[(\d+)\]", path)]
    path_codes = ["99"] + [_to_two_digit(idx) for idx in child_indexes]
    path_numeric_code = "|".join(path_codes)
    depth_code = _to_two_digit(depth)
    return path_numeric_code, depth_code


def _ensure_atspi_schema(session: Session) -> None:
    try:
        rows = session.exec(text("PRAGMA table_info(wechat_atspi_nodes)"))
        existing_cols = {str(row[1]) for row in rows if len(row) > 1}
    except Exception:
        existing_cols = set()

    ddl_statements: List[str] = []
    if "path_numeric_code" not in existing_cols:
        ddl_statements.append("ALTER TABLE wechat_atspi_nodes ADD COLUMN path_numeric_code VARCHAR(255) DEFAULT ''")
    if "depth_code" not in existing_cols:
        ddl_statements.append("ALTER TABLE wechat_atspi_nodes ADD COLUMN depth_code VARCHAR(8) DEFAULT '00'")

    for ddl in ddl_statements:
        session.exec(text(ddl))
    if ddl_statements:
        session.commit()


def _backfill_codes_if_needed(session: Session) -> None:
    rows = session.exec(
        select(WechatATSPINode).where(
            or_(
                WechatATSPINode.path_numeric_code == "",
                WechatATSPINode.path_numeric_code.is_(None),
                WechatATSPINode.depth_code == "",
                WechatATSPINode.depth_code.is_(None),
            )
        )
    ).all()
    if not rows:
        return

    changed = 0
    for row in rows:
        path_numeric_code, depth_code = _encode_path_and_depth(row.access_path, row.depth)
        if row.path_numeric_code != path_numeric_code or row.depth_code != depth_code:
            row.path_numeric_code = path_numeric_code
            row.depth_code = depth_code
            session.add(row)
            changed += 1

    if changed > 0:
        session.commit()


def _extract_window_info(window_obj: Any) -> Dict[str, Any]:
    return {
        "title": str(getattr(window_obj, "title", "") or ""),
        "window_class": str(getattr(window_obj, "window_class", "") or ""),
        "x": int(getattr(window_obj, "x", 0) or 0),
        "y": int(getattr(window_obj, "y", 0) or 0),
        "width": int(getattr(window_obj, "width", 0) or 0),
        "height": int(getattr(window_obj, "height", 0) or 0),
    }


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

        geo_ret = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", str(wid)],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if geo_ret.returncode != 0:
            return {"ok": False, "window_id": wid, "error": (geo_ret.stderr or "getwindowgeometry失败").strip()}

        info: Dict[str, Any] = {"ok": True, "window_id": wid, "x": 0, "y": 0, "width": 0, "height": 0, "name": ""}
        for line in (geo_ret.stdout or "").splitlines():
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


def _build_coordinate_diagnostics(raw_controls: List[Dict[str, Any]], window_info: Dict[str, Any]) -> Dict[str, Any]:
    wx = int(window_info.get("x", 0) or 0)
    wy = int(window_info.get("y", 0) or 0)
    ww = int(window_info.get("width", 0) or 0)
    wh = int(window_info.get("height", 0) or 0)
    tolerance = 2

    positioned = []
    for row in raw_controls or []:
        w = int(row.get("width", 0) or 0)
        h = int(row.get("height", 0) or 0)
        if w <= 0 or h <= 0:
            continue
        positioned.append({
            "x": int(row.get("x", 0) or 0),
            "y": int(row.get("y", 0) or 0),
            "width": w,
            "height": h,
        })

    total = len(positioned)
    if total == 0:
        return {"positioned_nodes": 0, "global_in_window_ratio": 0.0, "local_in_window_ratio": 0.0, "suspect_coordinate_bias": False}

    global_hits = 0
    local_hits = 0
    offset_samples_x: List[int] = []
    offset_samples_y: List[int] = []
    for node in positioned:
        gx_ok = (node["x"] >= wx - tolerance) and (node["x"] + node["width"] <= wx + ww + tolerance)
        gy_ok = (node["y"] >= wy - tolerance) and (node["y"] + node["height"] <= wy + wh + tolerance)
        if gx_ok and gy_ok:
            global_hits += 1

        lx_ok = (node["x"] >= -tolerance) and (node["x"] + node["width"] <= ww + tolerance)
        ly_ok = (node["y"] >= -tolerance) and (node["y"] + node["height"] <= wh + tolerance)
        if lx_ok and ly_ok:
            local_hits += 1
            offset_samples_x.append(wx - node["x"])
            offset_samples_y.append(wy - node["y"])

    global_ratio = round(float(global_hits) / float(total), 4)
    local_ratio = round(float(local_hits) / float(total), 4)
    suspect = local_ratio > (global_ratio + 0.15)

    tool_window = _get_active_window_geometry_xdotool()
    manager_vs_tool = {}
    if tool_window.get("ok"):
        manager_vs_tool = {
            "delta_x": int(tool_window.get("x", 0) or 0) - wx,
            "delta_y": int(tool_window.get("y", 0) or 0) - wy,
            "delta_width": int(tool_window.get("width", 0) or 0) - ww,
            "delta_height": int(tool_window.get("height", 0) or 0) - wh,
        }

    return {
        "positioned_nodes": total,
        "global_in_window_ratio": global_ratio,
        "local_in_window_ratio": local_ratio,
        "suspect_coordinate_bias": bool(suspect),
        "estimated_global_offset_if_local": {
            "x": int(statistics.median(offset_samples_x)) if offset_samples_x else 0,
            "y": int(statistics.median(offset_samples_y)) if offset_samples_y else 0,
        },
        "manager_window": {"x": wx, "y": wy, "width": ww, "height": wh},
        "tool_window": tool_window,
        "manager_vs_tool_delta": manager_vs_tool,
    }


def _get_ocr_engine() -> Any:
    global _ocr_engine, _ocr_init_error
    if _ocr_engine is not None:
        return _ocr_engine
    if _ocr_init_error is not None:
        raise RuntimeError(_ocr_init_error)
    try:
        from paddleocr import PaddleOCR

        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch")
        return _ocr_engine
    except Exception as e:
        _ocr_init_error = str(e)
        raise RuntimeError(_ocr_init_error) from e


def _ocr_from_image_path(image_path: str) -> Tuple[str, int]:
    if not image_path or not Path(image_path).exists():
        return "", 0

    try:
        engine = _get_ocr_engine()
        raw_result = engine.ocr(image_path, cls=True)
        text_parts: List[str] = []
        for line in raw_result or []:
            if not line:
                continue
            for item in line:
                if isinstance(item, list) and len(item) >= 2:
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and text_info:
                        text_parts.append(str(text_info[0]))
        merged = " ".join(part.strip() for part in text_parts if part and str(part).strip()).strip()
        numbers = [int(match) for match in re.findall(r"\d+", merged)]
        max_num = max(numbers) if numbers else 0
        return merged, max_num
    except Exception as e:
        logger.warning(f"OCR识别失败: {e}")
        return "", 0


def _normalize_tree_nodes(raw_controls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    path_to_row_index: Dict[str, int] = {}

    for row_idx, row in enumerate(raw_controls):
        depth = int(row.get("depth", 0) or 0)
        idx = int(row.get("index", row_idx) or row_idx)
        parent_index = int(row.get("parent_index", -1) or -1)

        path = str(row.get("path", "") or "").strip()
        if not path:
            if depth == 0:
                path = "root"
            else:
                parent_path = "root"
                if parent_index >= 0:
                    parent_path = next(
                        (n["access_path"] for n in nodes if int(n["index"]) == parent_index),
                        "root",
                    )
                path = _build_path(parent_path, idx)

        sibling_index = idx
        if "/child[" in path:
            try:
                sibling_index = int(path.split("/child[")[-1].split("]")[0])
            except Exception:
                sibling_index = idx

        path_to_row_index[path] = row_idx
        nodes.append(
            {
                "row_index": row_idx,
                "index": idx,
                "parent_index": parent_index,
                "access_path": path,
                "depth": depth,
                "sibling_index": sibling_index,
                "name": str(row.get("name", "") or ""),
                "role": str(row.get("role", "") or ""),
                "text": str(row.get("text", "") or ""),
                "x": int(row.get("x", 0) or 0),
                "y": int(row.get("y", 0) or 0),
                "width": int(row.get("width", 0) or 0),
                "height": int(row.get("height", 0) or 0),
            }
        )

    # 基于路径兜底 parent_index
    index_to_path = {int(n["index"]): n["access_path"] for n in nodes}
    for node in nodes:
        if int(node["depth"]) <= 0:
            node["parent_access_path"] = ""
            continue

        parent_path = ""
        if node["parent_index"] in index_to_path:
            parent_path = index_to_path[node["parent_index"]]
        elif "/child[" in node["access_path"]:
            parent_path = node["access_path"].rsplit("/child[", 1)[0]

        node["parent_access_path"] = parent_path

    return nodes


def _safe_crop(
    image,
    node_x: int,
    node_y: int,
    node_width: int,
    node_height: int,
    window_x: int,
    window_y: int,
):
    if image is None:
        return None

    h, w = image.shape[:2]
    if node_width <= 0 or node_height <= 0:
        return None

    rx = node_x - window_x
    ry = node_y - window_y
    # 如果传入坐标疑似已经是窗口内坐标，则直接使用
    if rx < 0 or ry < 0 or rx >= w or ry >= h:
        rx = node_x
        ry = node_y

    x1 = max(0, min(int(rx), w - 1))
    y1 = max(0, min(int(ry), h - 1))
    x2 = max(0, min(int(rx + node_width), w))
    y2 = max(0, min(int(ry + node_height), h))

    if x2 <= x1 or y2 <= y1:
        return None

    return image[y1:y2, x1:x2]


def _fetch_atspi_snapshot_once(manager: Any, max_nodes: int, max_depth: int) -> List[Dict[str, Any]]:
    def _capture_once() -> List[Dict[str, Any]]:
        used_tree = False
        if hasattr(manager, "get_atspi_tree_snapshot"):
            controls = manager.get_atspi_tree_snapshot(max_nodes, max_depth)
            used_tree = True
        elif hasattr(manager, "get_atspi_control_snapshot"):
            controls = manager.get_atspi_control_snapshot(max_nodes)
        else:
            raise HTTPException(status_code=500, detail="当前RPA模块缺少AT-SPI树快照接口")

        if not isinstance(controls, list):
            raise HTTPException(status_code=500, detail="AT-SPI树快照数据格式错误")

        if used_tree and len(controls) < 10 and hasattr(manager, "get_atspi_control_snapshot"):
            try:
                fallback_controls = manager.get_atspi_control_snapshot(max_nodes)
                if isinstance(fallback_controls, list) and len(fallback_controls) > len(controls):
                    controls = fallback_controls
            except Exception as err:
                logger.warning(f"AT-SPI树快照节点偏少，补抓control_snapshot失败: {err}")

        return controls

    raw_controls = _capture_once()

    if len(raw_controls) < 10 and hasattr(manager, "activate_wechat"):
        try:
            if bool(manager.activate_wechat()):
                time.sleep(0.8)
                retry_controls = _capture_once()
                if len(retry_controls) > len(raw_controls):
                    raw_controls = retry_controls
        except Exception as err:
            logger.warning(f"AT-SPI节点偏少时激活重抓失败: {err}")

    return raw_controls


def _count_positioned_nodes(raw_controls: List[Dict[str, Any]]) -> int:
    count = 0
    for row in raw_controls or []:
        if int(row.get("width", 0) or 0) > 0 and int(row.get("height", 0) or 0) > 0:
            count += 1
    return count


class CaptureRequest(BaseModel):
    max_nodes: int = Field(default=1200, ge=1, le=5000)
    max_depth: int = Field(default=-1, ge=-1, le=64)
    auto_activate: bool = False
    auto_refresh_tree: bool = False
    refresh_rounds: int = Field(default=1, ge=1, le=8)
    refresh_interval_ms: int = Field(default=0, ge=0, le=3000)
    page_type: str = ""
    function_type: str = ""


class UpdateRequest(BaseModel):
    id: int
    page_type: Optional[str] = None
    function_type: Optional[str] = None


class DeleteRequest(BaseModel):
    ids: List[int] = Field(default_factory=list)


class ClearRequest(BaseModel):
    confirm: bool = False


@router.post("/atspi/tree_snapshot")
async def atspi_tree_snapshot_alias(
    role_filter: Optional[str] = Query(default=None),
    name_filter: Optional[str] = Query(default=None),
    max_nodes: int = Query(default=5000),
    auto_activate: bool = Query(default=False),
    auto_refresh_tree: bool = Query(default=False),
    refresh_rounds: int = Query(default=1),
    refresh_interval_ms: int = Query(default=0),
    deep_search: bool = Query(default=True),
    include_common_keywords: bool = Query(default=False),
    extra_terms: Optional[str] = Query(default=None),
    require_keyword_match: Optional[bool] = Query(default=None),
    prefer_tree: bool = Query(default=True),
    max_depth: int = Query(default=-1),
    export_json: bool = Query(default=False),
    export_path: Optional[str] = Query(default=None),
    deduplicate: bool = Query(default=False),
):
    """AT-SPI树快照别名路由：兼容 /api/v1/atspi/tree_snapshot 调用。"""
    from .rpa_compatibility import get_atspi_tree_snapshot

    return await get_atspi_tree_snapshot(
        role_filter=role_filter,
        name_filter=name_filter,
        max_nodes=max_nodes,
        auto_activate=auto_activate,
        auto_refresh_tree=auto_refresh_tree,
        refresh_rounds=refresh_rounds,
        refresh_interval_ms=refresh_interval_ms,
        deep_search=deep_search,
        include_common_keywords=include_common_keywords,
        extra_terms=extra_terms,
        require_keyword_match=require_keyword_match,
        prefer_tree=prefer_tree,
        max_depth=max_depth,
        export_json=export_json,
        export_path=export_path,
        deduplicate=deduplicate,
    )


@router.post("/atspi/capture")
async def capture_atspi_tree(payload: CaptureRequest, session: Session = Depends(get_session)):
    """采集微信AT-SPI树+截图+OCR，并写入数据库。"""
    _ensure_atspi_schema(session)
    manager = _get_wechat_manager()

    activation_settle_seconds = 0.0
    if payload.auto_activate and hasattr(manager, "activate_wechat"):
        if bool(manager.activate_wechat()):
            activation_settle_seconds = 2.0
            time.sleep(2.0)

    if not hasattr(manager, "get_wechat_window"):
        raise HTTPException(status_code=500, detail="当前RPA模块缺少窗口信息接口")

    window_info = _extract_window_info(manager.get_wechat_window())

    snapshot_result = collect_best_snapshot(
        manager=manager,
        options=ATSPIQueryOptions(
            max_nodes=payload.max_nodes,
            auto_activate=False,
            auto_refresh_tree=payload.auto_refresh_tree,
            refresh_rounds=payload.refresh_rounds,
            refresh_interval_ms=payload.refresh_interval_ms,
            deep_search=True,
            prefer_tree=True,
            max_depth=payload.max_depth,
            deduplicate=False,
        ),
    )
    raw_controls = list(snapshot_result.get("best_controls", []))
    rounds = int(snapshot_result.get("rounds", 1) or 1)
    refresh_attempts = list(snapshot_result.get("refresh_attempts", []))

    coordinate_diagnostics = _build_coordinate_diagnostics(raw_controls, window_info)

    full_screenshot = None
    if hasattr(manager, "capture_full_window"):
        full_screenshot = manager.capture_full_window()
    elif hasattr(manager, "capture_message_area"):
        full_screenshot = manager.capture_message_area()

    if full_screenshot is None:
        raise HTTPException(status_code=500, detail="截图失败，无法继续采集")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_dir = _CAPTURE_ROOT / ts
    thumb_dir = capture_dir / "nodes"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    full_image_path = str((capture_dir / "full.png").resolve())
    cv2.imwrite(full_image_path, full_screenshot)

    normalized = _normalize_tree_nodes(raw_controls)

    index_to_db_id: Dict[int, int] = {}
    path_to_db_id: Dict[str, int] = {}
    inserted = 0

    # 深度优先，保证父节点先入库
    normalized.sort(key=lambda item: (int(item["depth"]), int(item["index"])))

    for node in normalized:
        crop = _safe_crop(
            image=full_screenshot,
            node_x=int(node["x"]),
            node_y=int(node["y"]),
            node_width=int(node["width"]),
            node_height=int(node["height"]),
            window_x=int(window_info["x"]),
            window_y=int(window_info["y"]),
        )

        shot_path = ""
        if crop is not None:
            shot_file = thumb_dir / f"node_{inserted + 1}.png"
            cv2.imwrite(str(shot_file), crop)
            shot_path = str(shot_file.resolve())

        ocr_text, ocr_number = _ocr_from_image_path(shot_path)

        parent_id = None
        parent_path = str(node.get("parent_access_path", "") or "")
        if parent_path and parent_path in path_to_db_id:
            parent_id = path_to_db_id[parent_path]
        elif int(node["parent_index"]) in index_to_db_id:
            parent_id = index_to_db_id[int(node["parent_index"])]

        path_numeric_code, depth_code = _encode_path_and_depth(str(node["access_path"]), int(node["depth"]))

        db_node = WechatATSPINode(
            window_title=str(window_info.get("title", "") or ""),
            window_class=str(window_info.get("window_class", "") or ""),
            access_path=str(node["access_path"]),
            path_numeric_code=path_numeric_code,
            depth=int(node["depth"]),
            depth_code=depth_code,
            parent_id=parent_id,
            index=int(node["sibling_index"]),
            name=str(node["name"]),
            role=str(node["role"]),
            text=str(node["text"]),
            ocr_text=ocr_text,
            ocr_number=int(ocr_number),
            x=int(node["x"]),
            y=int(node["y"]),
            width=int(node["width"]),
            height=int(node["height"]),
            client_x=int(node["x"]) - int(window_info["x"]),
            client_y=int(node["y"]) - int(window_info["y"]),
            screenshot_path=shot_path,
            full_image_path=full_image_path,
            page_type=str(payload.page_type or ""),
            function_type=str(payload.function_type or ""),
        )
        session.add(db_node)
        session.flush()

        if db_node.id is not None:
            index_to_db_id[int(node["index"])] = int(db_node.id)
            path_to_db_id[str(node["access_path"])] = int(db_node.id)
            inserted += 1

    session.commit()

    return {
        "success": True,
        "inserted": inserted,
        "capture_dir": str(capture_dir.resolve()),
        "full_image_path": full_image_path,
        "window_info": window_info,
        "activation_settle_seconds": activation_settle_seconds,
        "tree_refresh": {
            "enabled": bool(payload.auto_refresh_tree),
            "refresh_rounds": rounds,
            "refresh_interval_ms": payload.refresh_interval_ms,
            "attempts": refresh_attempts,
            "best_nodes": len(raw_controls),
            "best_positioned_nodes": _count_positioned_nodes(raw_controls),
            "raw_mode": str(snapshot_result.get("best_mode", "")),
            "data_source_status": snapshot_result.get("source_status", {}),
        },
        "coordinate_diagnostics": coordinate_diagnostics,
        "message": f"采集完成，共写入 {inserted} 条控件",
    }


@router.get("/atspi/list")
async def list_atspi_nodes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    depth: Optional[int] = None,
    depth_code: Optional[str] = None,
    path_code_prefix: Optional[str] = None,
    path_keyword: Optional[str] = None,
    page_type: Optional[str] = None,
    role: Optional[str] = None,
    text_keyword: Optional[str] = None,
    ocr_keyword: Optional[str] = None,
    x_min: Optional[int] = None,
    x_max: Optional[int] = None,
    y_min: Optional[int] = None,
    y_max: Optional[int] = None,
    non_empty_access_path: bool = Query(default=False),
    non_empty_path_numeric_code: bool = Query(default=False),
    non_empty_depth_code: bool = Query(default=False),
    non_empty_page_type: bool = Query(default=False),
    non_empty_role: bool = Query(default=False),
    non_empty_text: bool = Query(default=False),
    non_empty_ocr_text: bool = Query(default=False),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    session: Session = Depends(get_session),
):
    _ensure_atspi_schema(session)
    _backfill_codes_if_needed(session)
    conditions = []
    if depth is not None:
        conditions.append(WechatATSPINode.depth == depth)
    if depth_code:
        conditions.append(WechatATSPINode.depth_code == depth_code.strip())
    if path_code_prefix:
        conditions.append(WechatATSPINode.path_numeric_code.startswith(path_code_prefix.strip()))
    if path_keyword:
        conditions.append(WechatATSPINode.access_path.contains(path_keyword.strip()))
    if page_type:
        conditions.append(WechatATSPINode.page_type == page_type.strip())
    if role:
        conditions.append(WechatATSPINode.role.contains(role.strip()))
    if text_keyword:
        key = text_keyword.strip()
        conditions.append((WechatATSPINode.text.contains(key)) | (WechatATSPINode.name.contains(key)))
    if ocr_keyword:
        conditions.append(WechatATSPINode.ocr_text.contains(ocr_keyword.strip()))
    if x_min is not None:
        conditions.append(WechatATSPINode.x >= x_min)
    if x_max is not None:
        conditions.append(WechatATSPINode.x <= x_max)
    if y_min is not None:
        conditions.append(WechatATSPINode.y >= y_min)
    if y_max is not None:
        conditions.append(WechatATSPINode.y <= y_max)
    if non_empty_access_path:
        conditions.append(func.length(func.trim(WechatATSPINode.access_path)) > 0)
    if non_empty_path_numeric_code:
        conditions.append(func.length(func.trim(WechatATSPINode.path_numeric_code)) > 0)
    if non_empty_depth_code:
        conditions.append(func.length(func.trim(WechatATSPINode.depth_code)) > 0)
    if non_empty_page_type:
        conditions.append(func.length(func.trim(WechatATSPINode.page_type)) > 0)
    if non_empty_role:
        conditions.append(func.length(func.trim(WechatATSPINode.role)) > 0)
    if non_empty_text:
        conditions.append(
            (func.length(func.trim(WechatATSPINode.text)) > 0)
            | (func.length(func.trim(WechatATSPINode.name)) > 0)
        )
    if non_empty_ocr_text:
        conditions.append(func.length(func.trim(WechatATSPINode.ocr_text)) > 0)

    count_stmt = select(func.count()).select_from(WechatATSPINode)
    data_stmt = select(WechatATSPINode)

    if conditions:
        for condition in conditions:
            count_stmt = count_stmt.where(condition)
            data_stmt = data_stmt.where(condition)

    total = int(session.exec(count_stmt).one() or 0)

    sortable = {
        "depth": WechatATSPINode.depth,
        "index": WechatATSPINode.index,
        "x": WechatATSPINode.x,
        "y": WechatATSPINode.y,
        "depth_code": WechatATSPINode.depth_code,
        "path_numeric_code": WechatATSPINode.path_numeric_code,
        "created_at": WechatATSPINode.created_at,
    }
    order_column = sortable.get(sort_by, WechatATSPINode.created_at)
    data_stmt = data_stmt.order_by(order_column.desc() if sort_order.lower() == "desc" else order_column.asc())

    offset = (page - 1) * page_size
    rows = session.exec(data_stmt.offset(offset).limit(page_size)).all()

    items = []
    for row in rows:
        screenshot_url = ""
        full_image_url = ""
        if row.screenshot_path:
            screenshot_url = f"/api/v1/atspi/image?path={urllib.parse.quote(row.screenshot_path, safe='')}"
        if row.full_image_path:
            full_image_url = f"/api/v1/atspi/image?path={urllib.parse.quote(row.full_image_path, safe='')}"

        items.append(
            {
                "id": row.id,
                "window_title": row.window_title,
                "window_class": row.window_class,
                "access_path": row.access_path,
                "path_numeric_code": row.path_numeric_code,
                "depth": row.depth,
                "depth_code": row.depth_code,
                "parent_id": row.parent_id,
                "index": row.index,
                "name": row.name,
                "role": row.role,
                "text": row.text,
                "ocr_text": row.ocr_text,
                "ocr_number": row.ocr_number,
                "x": row.x,
                "y": row.y,
                "width": row.width,
                "height": row.height,
                "client_x": row.client_x,
                "client_y": row.client_y,
                "screenshot_path": row.screenshot_path,
                "full_image_path": row.full_image_path,
                "screenshot_url": screenshot_url,
                "full_image_url": full_image_url,
                "page_type": row.page_type,
                "function_type": row.function_type,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
        )

    return {
        "success": True,
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }


@router.post("/atspi/update")
async def update_atspi_node(payload: UpdateRequest, session: Session = Depends(get_session)):
    _ensure_atspi_schema(session)
    row = session.get(WechatATSPINode, payload.id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")

    if payload.page_type is not None:
        row.page_type = payload.page_type
    if payload.function_type is not None:
        row.function_type = payload.function_type

    session.add(row)
    session.commit()
    session.refresh(row)

    return {
        "success": True,
        "item": {
            "id": row.id,
            "page_type": row.page_type,
            "function_type": row.function_type,
        },
    }


@router.post("/atspi/delete")
async def delete_atspi_nodes(payload: DeleteRequest, session: Session = Depends(get_session)):
    _ensure_atspi_schema(session)
    ids = [int(item) for item in payload.ids if int(item) > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")

    rows = session.exec(select(WechatATSPINode).where(WechatATSPINode.id.in_(ids))).all()
    deleted = 0
    for row in rows:
        session.delete(row)
        deleted += 1
    session.commit()

    return {"success": True, "deleted": deleted}


@router.post("/atspi/clear")
@router.post("/rpa/atspi/clear")
async def clear_atspi_nodes(
    payload: Optional[ClearRequest] = None,
    confirm: Optional[bool] = Query(default=None),
    session: Session = Depends(get_session),
):
    _ensure_atspi_schema(session)
    confirmed = bool(confirm) or bool(payload.confirm if payload else False)
    if not confirmed:
        raise HTTPException(status_code=400, detail="请确认清空操作")

    total = int(session.exec(select(func.count()).select_from(WechatATSPINode)).one() or 0)
    if total <= 0:
        return {"success": True, "deleted": 0}

    session.exec(delete(WechatATSPINode))
    session.commit()

    remaining = int(session.exec(select(func.count()).select_from(WechatATSPINode)).one() or 0)

    return {"success": True, "deleted": total, "remaining": remaining}


@router.post("/atspi/clear_force")
@router.post("/rpa/atspi/clear_force")
async def clear_atspi_nodes_force(session: Session = Depends(get_session)):
    _ensure_atspi_schema(session)
    total = int(session.exec(select(func.count()).select_from(WechatATSPINode)).one() or 0)
    if total <= 0:
        return {"success": True, "deleted": 0, "remaining": 0}

    session.exec(delete(WechatATSPINode))
    session.commit()
    remaining = int(session.exec(select(func.count()).select_from(WechatATSPINode)).one() or 0)
    return {"success": True, "deleted": total, "remaining": remaining}


@router.get("/atspi/export")
async def export_for_agent(
    page_type: Optional[str] = None,
    role: Optional[str] = None,
    depth: Optional[int] = None,
    depth_code: Optional[str] = None,
    path_code_prefix: Optional[str] = None,
    no_filter: bool = Query(default=False),
    session: Session = Depends(get_session),
):
    _ensure_atspi_schema(session)
    _backfill_codes_if_needed(session)
    stmt = select(WechatATSPINode)
    if not no_filter:
        if page_type:
            stmt = stmt.where(WechatATSPINode.page_type == page_type)
        if role:
            stmt = stmt.where(WechatATSPINode.role.contains(role))
        if depth is not None:
            stmt = stmt.where(WechatATSPINode.depth == depth)
        if depth_code:
            stmt = stmt.where(WechatATSPINode.depth_code == depth_code)
        if path_code_prefix:
            stmt = stmt.where(WechatATSPINode.path_numeric_code.startswith(path_code_prefix))

    rows = session.exec(stmt.order_by(WechatATSPINode.depth.asc(), WechatATSPINode.index.asc())).all()
    data = []
    for row in rows:
        data.append(
            {
                "id": row.id,
                "path": row.access_path,
                "path_numeric_code": row.path_numeric_code,
                "depth": row.depth,
                "depth_code": row.depth_code,
                "index": row.index,
                "name": row.name,
                "text": row.text,
                "ocr_number": row.ocr_number,
                "page_type": row.page_type,
                "function_type": row.function_type,
                "client_x": row.client_x,
                "client_y": row.client_y,
                "width": row.width,
                "height": row.height,
                "screenshot_path": row.screenshot_path,
                "unique_code": f"{row.depth_code}|{row.path_numeric_code}|i{row.index}",
            }
        )

    return {
        "success": True,
        "count": len(data),
        "no_filter": bool(no_filter),
        "items": data,
    }


@router.get("/atspi/image")
async def read_atspi_image(path: str):
    """图片预览接口，限制在 data/atspi_capture 目录下读取。"""
    if not path:
        raise HTTPException(status_code=400, detail="path 不能为空")

    decoded = urllib.parse.unquote(path)
    file_path = Path(decoded).resolve()
    allowed_root = _CAPTURE_ROOT.resolve()

    try:
        file_path.relative_to(allowed_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="不允许访问该路径")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(str(file_path))


@router.get("/atspi/mysql_ddl")
async def get_mysql_ddl():
    ddl = """
CREATE TABLE IF NOT EXISTS wechat_atspi_nodes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  window_title VARCHAR(255) DEFAULT '',
  window_class VARCHAR(255) DEFAULT '',
  access_path VARCHAR(1024) NOT NULL,
    path_numeric_code VARCHAR(255) DEFAULT '',
  depth INT NOT NULL DEFAULT 0,
    depth_code VARCHAR(8) DEFAULT '00',
  parent_id BIGINT NULL,
  `index` INT NOT NULL DEFAULT 0,
  name VARCHAR(255) DEFAULT '',
  role VARCHAR(255) DEFAULT '',
  text TEXT,
  ocr_text TEXT,
  ocr_number INT NOT NULL DEFAULT 0,
  x INT NOT NULL DEFAULT 0,
  y INT NOT NULL DEFAULT 0,
  width INT NOT NULL DEFAULT 0,
  height INT NOT NULL DEFAULT 0,
  client_x INT NOT NULL DEFAULT 0,
  client_y INT NOT NULL DEFAULT 0,
  screenshot_path VARCHAR(1024) DEFAULT '',
  full_image_path VARCHAR(1024) DEFAULT '',
  page_type VARCHAR(128) DEFAULT '',
  function_type VARCHAR(128) DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_depth (depth),
    KEY idx_depth_code (depth_code),
  KEY idx_index (`index`),
    KEY idx_path_numeric_code (path_numeric_code),
  KEY idx_page_type (page_type),
  KEY idx_role (role),
  KEY idx_created_at (created_at),
  KEY idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """.strip()

    return {"success": True, "table": "wechat_atspi_nodes", "ddl": ddl}
