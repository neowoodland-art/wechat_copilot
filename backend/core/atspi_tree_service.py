from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import json
import os
import time


@dataclass
class ATSPIQueryOptions:
    role_filter: Optional[str] = None
    name_filter: Optional[str] = None
    max_nodes: int = 5000
    auto_activate: bool = False
    auto_refresh_tree: bool = False
    refresh_rounds: int = 1
    refresh_interval_ms: int = 0
    deep_search: bool = True
    include_common_keywords: bool = False
    extra_terms: Optional[str] = None
    require_keyword_match: Optional[bool] = None
    prefer_tree: bool = True
    max_depth: int = -1
    export_json: bool = False
    export_path: Optional[str] = None
    deduplicate: bool = False


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _build_keywords(name_filter: Optional[str], extra_terms: Optional[str], include_common_keywords: bool) -> List[str]:
    terms: List[str] = []

    def _push(raw: Optional[str]) -> None:
        if not raw:
            return
        for token in str(raw).replace("，", ",").replace(";", ",").split(","):
            token = token.strip().lower()
            if token:
                terms.append(token)

    _push(name_filter)
    _push(extra_terms)

    if include_common_keywords:
        terms.extend(["搜索", "输入", "发送", "联系人", "聊天", "button", "entry", "text"])

    dedup: List[str] = []
    seen = set()
    for term in terms:
        if term not in seen:
            seen.add(term)
            dedup.append(term)
    return dedup


def _hit_keyword(searchable: str, term: str) -> bool:
    if not term:
        return False
    return term in searchable


def _normalize_row(item: Dict[str, Any], fallback_idx: int) -> Dict[str, Any]:
    idx = _to_int(item.get("index", fallback_idx), fallback_idx)
    depth = _to_int(item.get("depth", 0), 0)
    parent_index = _to_int(item.get("parent_index", -1), -1)
    path = str(item.get("path", "") or f"root/child[{idx}]")
    name = str(item.get("name", item.get("title", "")) or "")
    role = str(item.get("role", item.get("type", "")) or "")
    text = str(item.get("text", item.get("content", "")) or "")

    x = _to_int(item.get("x", item.get("left", 0)), 0)
    y = _to_int(item.get("y", item.get("top", 0)), 0)
    w = _to_int(item.get("width", item.get("w", 0)), 0)
    h = _to_int(item.get("height", item.get("h", 0)), 0)

    return {
        "index": idx,
        "depth": depth,
        "parent_index": parent_index,
        "path": path,
        "name": name,
        "role": role,
        "text": text,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }


def _capture_once(manager: Any, snapshot_limit: int, prefer_tree: bool, max_depth: int) -> Tuple[List[Dict[str, Any]], str, Dict[str, Dict[str, Any]]]:
    source_status = {
        "tree_snapshot": {"attempted": False, "nodes": 0, "error": ""},
        "control_snapshot": {"attempted": False, "nodes": 0, "error": ""},
    }

    tree_controls: List[Dict[str, Any]] = []
    control_controls: List[Dict[str, Any]] = []

    def _tree_first() -> bool:
        return bool(prefer_tree)

    if hasattr(manager, "get_atspi_tree_snapshot"):
        source_status["tree_snapshot"]["attempted"] = True
        try:
            tree_controls = list(manager.get_atspi_tree_snapshot(int(snapshot_limit), int(max_depth)) or [])
            source_status["tree_snapshot"]["nodes"] = len(tree_controls)
        except Exception as err:
            source_status["tree_snapshot"]["error"] = str(err)
            tree_controls = []

    if hasattr(manager, "get_atspi_control_snapshot"):
        source_status["control_snapshot"]["attempted"] = True
        try:
            control_controls = list(manager.get_atspi_control_snapshot(int(snapshot_limit)) or [])
            source_status["control_snapshot"]["nodes"] = len(control_controls)
        except Exception as err:
            source_status["control_snapshot"]["error"] = str(err)
            control_controls = []

    merged: List[Dict[str, Any]] = []
    seen = set()

    ordered_sources = [tree_controls, control_controls] if _tree_first() else [control_controls, tree_controls]
    for source in ordered_sources:
        for row in source:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path", "") or "").strip().lower()
            name = str(row.get("name", row.get("title", "")) or "").strip().lower()
            role = str(row.get("role", row.get("type", "")) or "").strip().lower()
            key = (
                path,
                name,
                role,
                _to_int(row.get("x", row.get("left", 0)), 0),
                _to_int(row.get("y", row.get("top", 0)), 0),
                _to_int(row.get("width", row.get("w", 0)), 0),
                _to_int(row.get("height", row.get("h", 0)), 0),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)

    mode = "merged_tree_control"
    if tree_controls and not control_controls:
        mode = "tree_snapshot"
    elif control_controls and not tree_controls:
        mode = "control_snapshot"

    return merged, mode, source_status


def _count_positioned(controls: List[Dict[str, Any]]) -> int:
    total = 0
    for row in controls:
        if _to_int(row.get("width", 0), 0) > 0 and _to_int(row.get("height", 0), 0) > 0:
            total += 1
    return total


def collect_best_snapshot(manager: Any, options: ATSPIQueryOptions) -> Dict[str, Any]:
    requested_max_nodes = _to_int(options.max_nodes, 5000)
    if requested_max_nodes <= 0:
        requested_max_nodes = 20000
    limit = max(1, min(requested_max_nodes, 20000))
    snapshot_limit = min(20000, max(limit * 4, 800)) if options.deep_search else limit

    if options.auto_activate and hasattr(manager, "activate_wechat"):
        try:
            manager.activate_wechat()
            time.sleep(0.25)
        except Exception:
            pass

    rounds = max(1, min(_to_int(options.refresh_rounds, 1), 8)) if options.auto_refresh_tree else 1
    interval_seconds = max(0.0, min(float(options.refresh_interval_ms), 3000.0) / 1000.0)

    best_controls: List[Dict[str, Any]] = []
    best_mode = "control_snapshot"
    best_score = -1
    best_round = 1
    refresh_attempts: List[Dict[str, Any]] = []
    final_source_status = {
        "tree_snapshot": {"attempted": False, "nodes": 0, "error": ""},
        "control_snapshot": {"attempted": False, "nodes": 0, "error": ""},
    }

    for idx in range(rounds):
        controls, mode, source_status = _capture_once(
            manager=manager,
            snapshot_limit=snapshot_limit,
            prefer_tree=bool(options.prefer_tree),
            max_depth=int(options.max_depth),
        )

        final_source_status["tree_snapshot"]["attempted"] = final_source_status["tree_snapshot"]["attempted"] or source_status["tree_snapshot"]["attempted"]
        final_source_status["control_snapshot"]["attempted"] = final_source_status["control_snapshot"]["attempted"] or source_status["control_snapshot"]["attempted"]
        final_source_status["tree_snapshot"]["nodes"] = max(final_source_status["tree_snapshot"]["nodes"], source_status["tree_snapshot"]["nodes"])
        final_source_status["control_snapshot"]["nodes"] = max(final_source_status["control_snapshot"]["nodes"], source_status["control_snapshot"]["nodes"])
        if source_status["tree_snapshot"]["error"]:
            final_source_status["tree_snapshot"]["error"] = source_status["tree_snapshot"]["error"]
        if source_status["control_snapshot"]["error"]:
            final_source_status["control_snapshot"]["error"] = source_status["control_snapshot"]["error"]

        normalized = [_normalize_row(row, i) for i, row in enumerate(controls) if isinstance(row, dict)]
        score = len(normalized) * 100000 + _count_positioned(normalized)
        refresh_attempts.append(
            {
                "round": idx + 1,
                "mode": mode,
                "nodes": len(normalized),
                "positioned_nodes": _count_positioned(normalized),
            }
        )

        if score > best_score:
            best_score = score
            best_controls = normalized
            best_mode = mode
            best_round = idx + 1

        if idx < rounds - 1 and interval_seconds > 0:
            time.sleep(interval_seconds)

    return {
        "best_controls": best_controls,
        "best_mode": best_mode,
        "best_round": best_round,
        "limit": limit,
        "snapshot_limit": snapshot_limit,
        "rounds": rounds,
        "refresh_attempts": refresh_attempts,
        "source_status": final_source_status,
    }


def build_snapshot_payload(manager: Any, options: ATSPIQueryOptions) -> Dict[str, Any]:
    role_kw = str(options.role_filter or "").strip().lower()
    depth_limit = int(options.max_depth)
    snapshot_result = collect_best_snapshot(manager=manager, options=options)
    best_controls = list(snapshot_result["best_controls"])
    best_mode = str(snapshot_result["best_mode"])
    best_round = int(snapshot_result["best_round"])
    limit = int(snapshot_result["limit"])
    snapshot_limit = int(snapshot_result["snapshot_limit"])
    rounds = int(snapshot_result["rounds"])
    refresh_attempts = list(snapshot_result["refresh_attempts"])
    final_source_status = dict(snapshot_result["source_status"])

    keywords = _build_keywords(options.name_filter, options.extra_terms, options.include_common_keywords)
    keyword_required = options.require_keyword_match
    if keyword_required is None:
        keyword_required = bool(options.name_filter or options.extra_terms)

    nodes: List[Dict[str, Any]] = []
    dedup_keys = set()

    for row in best_controls:
        role = str(row.get("role", "") or "")
        name = str(row.get("name", "") or "")
        text = str(row.get("text", "") or "")
        depth = _to_int(row.get("depth", 0), 0)

        if depth_limit >= 0 and depth > depth_limit:
            continue

        if role_kw and role_kw not in role.lower():
            continue

        searchable = f"{name} {text} {role}".lower()
        matched_keywords = [term for term in keywords if _hit_keyword(searchable, term)]
        if keyword_required and not matched_keywords:
            continue

        x = _to_int(row.get("x", 0), 0)
        y = _to_int(row.get("y", 0), 0)
        w = _to_int(row.get("width", 0), 0)
        h = _to_int(row.get("height", 0), 0)

        if options.deduplicate:
            dedup_key = (name.strip().lower(), role.strip().lower(), x, y, w, h)
            if dedup_key in dedup_keys:
                continue
            dedup_keys.add(dedup_key)

        score = 0.0
        if matched_keywords:
            score += min(1.0, 0.2 * len(matched_keywords))
        if name and text:
            score += 0.1
        if w > 0 and h > 0:
            score += 0.1
        if "button" in role.lower() or "entry" in role.lower() or "text" in role.lower():
            score += 0.1

        node = {
            "node_id": f"node_{row['index']}",
            "index": row["index"],
            "depth": depth,
            "parent_index": row["parent_index"],
            "path": row["path"],
            "name": name,
            "role": role,
            "text": text,
            "bounds": {
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "center_x": x + w // 2,
                "center_y": y + h // 2,
            },
            "clickable_hint": "button" in role.lower() or "menu" in role.lower(),
            "matched_keywords": matched_keywords[:12],
            "match_score": round(score, 3),
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
    if options.export_json:
        export_file = options.export_path or f"/tmp/wechat_atspi_tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "success": True,
            "count": len(nodes),
            "generated_at": datetime.now().isoformat(),
            "nodes": nodes,
            "filters": {
                "role_filter": options.role_filter or "",
                "name_filter": options.name_filter or "",
                "max_nodes": limit,
                "snapshot_limit": snapshot_limit,
                "prefer_tree": options.prefer_tree,
                "max_depth": options.max_depth,
                "raw_mode": best_mode,
            },
        }
        try:
            os.makedirs(os.path.dirname(export_file), exist_ok=True)
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            export_file = ""

    return {
        "success": True,
        "nodes": nodes,
        "count": len(nodes),
        "filters": {
            "role_filter": options.role_filter or "",
            "name_filter": options.name_filter or "",
            "max_nodes": limit,
            "snapshot_limit": snapshot_limit,
            "tree_attempted": bool(final_source_status.get("tree_snapshot", {}).get("attempted", False)),
            "tree_nodes_count": int(final_source_status.get("tree_snapshot", {}).get("nodes", 0) or 0),
            "auto_activate": bool(options.auto_activate),
            "deep_search": bool(options.deep_search),
            "include_common_keywords": bool(options.include_common_keywords),
            "extra_terms": options.extra_terms or "",
            "require_keyword_match": bool(keyword_required),
            "expanded_keywords": keywords,
            "prefer_tree": bool(options.prefer_tree),
            "max_depth": int(options.max_depth),
            "raw_mode": best_mode,
            "tree_refresh": {
                "enabled": bool(options.auto_refresh_tree),
                "refresh_rounds": rounds,
                "refresh_interval_ms": int(options.refresh_interval_ms),
                "best_round": best_round,
                "attempts": refresh_attempts,
                "best_nodes": len(best_controls),
                "best_positioned_nodes": _count_positioned(best_controls),
            },
            "deduplicate": bool(options.deduplicate),
            "data_source_status": final_source_status,
        },
        "activated": bool(options.auto_activate),
        "export_file": export_file,
        "message": f"AT-SPI快照完成，返回 {len(nodes)} 个节点",
    }
