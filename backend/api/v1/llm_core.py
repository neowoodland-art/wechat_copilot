from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import json
import logging
import time
import uuid

from db.session import get_session
from db.models import LLMRequestLog, LLMSceneConfig, LLMToolRegistry, WechatATSPINode

logger = logging.getLogger(__name__)
router = APIRouter()


SUPPORTED_SCENES = {
    "interface_analysis",
    "sop_generation",
    "multimodal_chat",
    "system_evolution",
}


SCENE_ALIASES = {
    "ui": "interface_analysis",
    "interface": "interface_analysis",
    "界面分析": "interface_analysis",
    "sop": "sop_generation",
    "客户维护": "sop_generation",
    "chat": "multimodal_chat",
    "multimodal": "multimodal_chat",
    "聊天回复": "multimodal_chat",
    "system": "system_evolution",
    "系统分析": "system_evolution",
}


ACTION_TYPES = [
    "send_text",
    "send_voice",
    "send_image",
    "send_emoji",
    "execute_tool",
    "open_window",
]


MODEL_PREFERENCES = ["auto", "local", "doubao", "alibaba"]


BUILTIN_TOOLS: List[Dict[str, Any]] = [
    {
        "tool_name": "ocr",
        "description": "图片文字/数字识别",
        "input_schema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "图片base64或URL"},
                "extract_numbers": {"type": "boolean", "default": True},
            },
            "required": ["image"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "numbers": {"type": "array", "items": {"type": "integer"}},
            },
        },
    },
    {
        "tool_name": "atspi_parse",
        "description": "辅助树结构解析",
        "input_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array"},
                "analysis_type": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "page_type": {"type": "string"},
                "controls": {"type": "array"},
            },
        },
    },
    {
        "tool_name": "hotspot_fetch",
        "description": "热点获取",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "category": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "hotspots": {"type": "array"},
            },
        },
    },
    {
        "tool_name": "file_analyze",
        "description": "文件内容识别",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {"type": "array"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
            },
        },
    },
    {
        "tool_name": "chat_analyze",
        "description": "聊天意图/情感分析",
        "input_schema": {
            "type": "object",
            "properties": {
                "history": {"type": "array"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "sentiment": {"type": "string"},
            },
        },
    },
    {
        "tool_name": "product_recommend",
        "description": "商品推荐",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_tags": {"type": "array"},
                "hotspots": {"type": "array"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "products": {"type": "array"},
            },
        },
    },
    {
        "tool_name": "tts",
        "description": "文本转语音",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "audio": {"type": "string"},
            },
        },
    },
    {
        "tool_name": "mark_as_read",
        "description": "消息标记已读",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_ids": {"type": "array"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
            },
        },
    },
]


class CoreContext(BaseModel):
    history: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: str = ""


class CoreInput(BaseModel):
    text: str = ""
    images: List[str] = Field(default_factory=list)
    audio: Optional[str] = None
    files: List[str] = Field(default_factory=list)
    structured_data: Dict[str, Any] = Field(default_factory=dict)


class CoreTools(BaseModel):
    enabled: List[str] = Field(default_factory=list)
    force_call: Optional[str] = None
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class CoreConfig(BaseModel):
    model_preference: str = "auto"
    response_format: str = "json"
    timeout: int = 30000
    ext: Dict[str, Any] = Field(default_factory=dict)


class LLMCoreRequest(BaseModel):
    request_id: str = ""
    scene_type: str = ""
    scene: str = ""
    level: int = 3
    user_id: str = ""
    context: CoreContext = Field(default_factory=CoreContext)
    input: CoreInput = Field(default_factory=CoreInput)
    tools: Union[CoreTools, List[str]] = Field(default_factory=CoreTools)
    config: CoreConfig = Field(default_factory=CoreConfig)

    # 极简协议兼容字段
    hist: List[Dict[str, Any]] = Field(default_factory=list)
    text: str = ""
    img: str = ""
    tools_enable: List[str] = Field(default_factory=list)
    need_struct_output: bool = True
    model_route: str = ""


class ToolRegisterRequest(BaseModel):
    tool_name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SceneConfigRequest(BaseModel):
    scene_type: str
    config_json: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


def _parse_json_text(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def _to_json_text(data: Dict[str, Any]) -> str:
    return json.dumps(data or {}, ensure_ascii=False)


def _resolve_scene(scene_type: str, scene_alias: str) -> str:
    value = (scene_type or "").strip()
    if value:
        return SCENE_ALIASES.get(value, value)
    alias = (scene_alias or "").strip()
    return SCENE_ALIASES.get(alias, alias)


def _ensure_tools_obj(request: LLMCoreRequest) -> CoreTools:
    if isinstance(request.tools, CoreTools):
        return request.tools
    if isinstance(request.tools, list):
        return CoreTools(enabled=[str(item).strip() for item in request.tools if str(item).strip()])
    return CoreTools()


def _normalize_request(request: LLMCoreRequest) -> None:
    request.scene_type = _resolve_scene(request.scene_type, request.scene)

    # 极简输入兼容
    if not request.input.text and request.text:
        request.input.text = request.text
    if not request.input.images and request.img:
        request.input.images = [request.img]
    if not request.context.history and request.hist:
        request.context.history = request.hist

    tools_obj = _ensure_tools_obj(request)
    if request.tools_enable:
        merged = list(dict.fromkeys(tools_obj.enabled + [str(item).strip() for item in request.tools_enable if str(item).strip()]))
        tools_obj.enabled = merged
    request.tools = tools_obj

    if request.model_route and request.config.model_preference == "auto":
        request.config.model_preference = request.model_route

    if request.config.model_preference not in MODEL_PREFERENCES:
        request.config.model_preference = "auto"


def _optimize_request_for_token(request: LLMCoreRequest) -> Dict[str, Any]:
    ext_cfg = request.config.ext or {}
    max_history = int(ext_cfg.get("max_history", 10) or 10)
    max_images = int(ext_cfg.get("max_images", 1) or 1)
    max_text_chars = int(ext_cfg.get("max_text_chars", 2000) or 2000)

    if max_history >= 0 and len(request.context.history) > max_history:
        request.context.history = request.context.history[-max_history:]

    if max_images >= 0 and len(request.input.images) > max_images:
        request.input.images = request.input.images[:max_images]

    if max_text_chars > 0 and len(request.input.text or "") > max_text_chars:
        request.input.text = (request.input.text or "")[:max_text_chars]

    return {
        "max_history": max_history,
        "max_images": max_images,
        "max_text_chars": max_text_chars,
        "history_after": len(request.context.history),
        "images_after": len(request.input.images),
        "text_after_chars": len(request.input.text or ""),
    }


def _build_compact_response(full_payload: Dict[str, Any]) -> Dict[str, Any]:
    output = (((full_payload or {}).get("data") or {}).get("output") or {})
    compact = {
        "text": output.get("text", ""),
        "emoji": output.get("emoji", ""),
        "struct": output.get("structured", {}),
        "tools": ((full_payload.get("data") or {}).get("tool_calls") or []),
        "actions": ((full_payload.get("data") or {}).get("actions") or []),
        "meta": {
            "request_id": full_payload.get("request_id", ""),
            "scene_type": full_payload.get("scene_type", ""),
            "model_used": full_payload.get("model_used", ""),
            "execution_time": full_payload.get("execution_time", 0),
        },
    }
    return compact


def _seed_builtin_tools(session: Session) -> None:
    existing = session.exec(select(LLMToolRegistry)).all()
    existing_names = {item.tool_name for item in existing}
    now = datetime.utcnow()
    inserted = False
    for tool in BUILTIN_TOOLS:
        if tool["tool_name"] in existing_names:
            continue
        row = LLMToolRegistry(
            tool_name=tool["tool_name"],
            description=tool.get("description", ""),
            input_schema=_to_json_text(tool.get("input_schema", {})),
            output_schema=_to_json_text(tool.get("output_schema", {})),
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        inserted = True
    if inserted:
        session.commit()


def _extract_numbers_from_text(text: str) -> List[int]:
    import re

    if not text:
        return []
    return [int(item) for item in re.findall(r"\d+", text)]


def _tool_ocr(request: LLMCoreRequest) -> Dict[str, Any]:
    source_text = request.input.text or ""
    if not source_text and request.input.structured_data:
        source_text = json.dumps(request.input.structured_data, ensure_ascii=False)
    return {
        "text": source_text[:800],
        "numbers": _extract_numbers_from_text(source_text),
    }


def _tool_atspi_parse(request: LLMCoreRequest) -> Dict[str, Any]:
    tree = request.input.structured_data.get("atspi_tree") or []
    controls = []
    for idx, node in enumerate(tree[:300]):
        controls.append(
            {
                "id": f"ctrl_{idx + 1}",
                "path": node.get("path", ""),
                "depth": int(node.get("depth", 0) or 0),
                "name": node.get("name", ""),
                "role": node.get("role", ""),
                "text": node.get("text", ""),
                "screen_coord": {
                    "x": int(node.get("x", 0) or 0),
                    "y": int(node.get("y", 0) or 0),
                    "w": int(node.get("width", 0) or 0),
                    "h": int(node.get("height", 0) or 0),
                },
            }
        )

    return {
        "page_type": request.input.structured_data.get("page_type_hint", "unknown"),
        "controls": controls,
        "count": len(controls),
    }


def _tool_hotspot_fetch(request: LLMCoreRequest) -> Dict[str, Any]:
    input_hotspots = request.input.structured_data.get("hotspots") or []
    if input_hotspots:
        return {"hotspots": input_hotspots}
    return {
        "hotspots": [
            {"topic": "AI智能手表", "heat": 92, "trend": "up"},
            {"topic": "节后复工效率", "heat": 80, "trend": "stable"},
        ]
    }


def _tool_file_analyze(request: LLMCoreRequest) -> Dict[str, Any]:
    files = request.input.files or []
    return {
        "summary": f"共收到 {len(files)} 个文件，已完成基础解析占位。",
        "files": files,
    }


def _tool_chat_analyze(request: LLMCoreRequest) -> Dict[str, Any]:
    text = request.input.text or ""
    sentiment = "neutral"
    if any(key in text for key in ["投诉", "生气", "不满", "差"]):
        sentiment = "negative"
    elif any(key in text for key in ["谢谢", "满意", "不错", "喜欢"]):
        sentiment = "positive"

    intent = "normal_conversation"
    if any(key in text for key in ["报价", "价格", "多少钱"]):
        intent = "price_inquiry"
    elif any(key in text for key in ["新品", "推荐", "买"]):
        intent = "purchase_intention"

    return {
        "intent": intent,
        "sentiment": sentiment,
        "urgency": "medium" if sentiment == "negative" else "low",
    }


def _tool_product_recommend(request: LLMCoreRequest) -> Dict[str, Any]:
    hotspots = request.input.structured_data.get("hotspots") or []
    top_topic = hotspots[0]["topic"] if hotspots and isinstance(hotspots[0], dict) and hotspots[0].get("topic") else "热点商品"
    return {
        "products": [
            {
                "id": "prod_001",
                "name": "AI智能手表Pro",
                "reason": f"结合热点 {top_topic} 与客户画像推荐",
            }
        ]
    }


def _tool_tts(request: LLMCoreRequest) -> Dict[str, Any]:
    text = request.input.text or ""
    fake_audio = f"tts://{len(text)}chars"
    return {"audio": fake_audio}


def _tool_mark_as_read(request: LLMCoreRequest) -> Dict[str, Any]:
    mids = request.input.structured_data.get("message_ids") or []
    return {"success": True, "message_ids": mids}


TOOL_IMPL = {
    "ocr": _tool_ocr,
    "atspi_parse": _tool_atspi_parse,
    "hotspot_fetch": _tool_hotspot_fetch,
    "file_analyze": _tool_file_analyze,
    "chat_analyze": _tool_chat_analyze,
    "product_recommend": _tool_product_recommend,
    "tts": _tool_tts,
    "mark_as_read": _tool_mark_as_read,
}


async def _call_llm_text(scene_type: str, prompt_text: str, context: Dict[str, Any], model_preference: str) -> Dict[str, Any]:
    try:
        if model_preference in ["auto", "local", "doubao", "alibaba"]:
            from core.ai_router import AIRouter

            router_obj = AIRouter()
            route_context = {
                "scene_type": scene_type,
                "model_preference": model_preference,
                **(context or {}),
            }
            route_result = await router_obj.route_request(prompt_text, route_context)
            return {
                "ok": bool(route_result.get("success", True)),
                "text": route_result.get("response", ""),
                "model_used": route_result.get("model_used", model_preference or "auto"),
            }
    except Exception as e:
        logger.warning(f"AI路由调用失败，使用降级文本: {e}")

    return {
        "ok": True,
        "text": "已完成结构化处理（当前使用本地降级回复）。",
        "model_used": "fallback",
    }


def _build_scene_structured(scene_type: str, request: LLMCoreRequest, tool_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if scene_type == "interface_analysis":
        parse_result = tool_results.get("atspi_parse", {})
        controls = parse_result.get("controls", [])
        return {
            "page_type": request.input.structured_data.get("analysis_type", "full_scan"),
            "controls": controls,
            "hierarchy": {
                "level_1": ["search_bar", "menu_bar", "chat_area", "input_area"],
                "level_2": [],
            },
            "hotspots": request.input.structured_data.get("hotspots", []),
        }

    if scene_type == "sop_generation":
        hotspots = tool_results.get("hotspot_fetch", {}).get("hotspots", request.input.structured_data.get("hotspots", []))
        products = tool_results.get("product_recommend", {}).get("products", [])
        customer = request.input.structured_data.get("customer_info", {})
        customer_name = customer.get("name", "客户")
        return {
            "sop_name": f"{customer_name} 客户维护SOP",
            "sop_version": "v1.0",
            "target_customer": ",".join(customer.get("tags", [])) or "普通客户",
            "steps": [
                {
                    "step_id": 1,
                    "step_name": "开场问候",
                    "trigger": "首次联系",
                    "script_template": f"{customer_name}您好，今天给您同步下最新信息。",
                    "required_actions": ["send_greeting", "check_in"],
                    "hotspot_recommendation": (hotspots[0]["topic"] if hotspots and isinstance(hotspots[0], dict) and hotspots[0].get("topic") else "结合当日热点")
                },
                {
                    "step_id": 2,
                    "step_name": "需求挖掘",
                    "trigger": "客户有回应",
                    "script_template": "您最近更关注功能、价格还是交付时效？",
                    "required_actions": ["ask_needs", "recommend"],
                    "tools": ["product_recommend"],
                },
            ],
            "recommended_products": products,
            "emoji_recommendations": ["😊", "👍", "🎉"],
            "risk_warnings": ["避免打扰时段", "避免敏感话题"],
            "ext": {},
        }

    if scene_type == "system_evolution":
        return {
            "analysis_scope": request.input.structured_data.get("analysis_scope", "full_system"),
            "bottlenecks": request.input.structured_data.get("bottlenecks", []),
            "optimization_actions": [
                {
                    "module": "llm_router",
                    "priority": "high",
                    "proposal": "启用小模型优先和无效响应快速回退",
                },
                {
                    "module": "sop_scheduler",
                    "priority": "medium",
                    "proposal": "将画像与SOP改为批处理缓存，减少实时token消耗",
                },
            ],
            "ext": {},
        }

    chat_result = tool_results.get("chat_analyze", {})
    ocr_result = tool_results.get("ocr", {})
    tts_result = tool_results.get("tts", {})
    unread = []
    nums = ocr_result.get("numbers", [])
    if nums:
        unread.append({"sender": "OCR", "content": ocr_result.get("text", ""), "count": max(nums)})

    return {
        "unread_messages": unread,
        "suggested_reply": "收到，我马上看并尽快回复您。",
        "sentiment": chat_result.get("sentiment", "neutral"),
        "tts": tts_result.get("audio", ""),
    }


def _build_actions(scene_type: str, request: LLMCoreRequest, structured: Dict[str, Any]) -> List[Dict[str, Any]]:
    if scene_type == "interface_analysis":
        return [{"action_type": "execute_tool", "params": {"tool": "atspi_parse", "args": {}}}]
    if scene_type == "sop_generation":
        return [{"action_type": "execute_tool", "params": {"tool": "product_recommend", "args": {}}}]
    if scene_type == "system_evolution":
        return [{"action_type": "execute_tool", "params": {"tool": "chat_analyze", "args": {"mode": "system"}}}]

    suggested_reply = structured.get("suggested_reply", "")
    actions = [{"action_type": "send_text", "params": {"text": suggested_reply}}]
    if request.input.audio:
        actions.append({"action_type": "send_voice", "params": {"audio": structured.get("tts", "")}})
    actions.append({"action_type": "send_emoji", "params": {"emoji": "👍"}})
    return actions


def _pick_enabled_tools(request: LLMCoreRequest, registered_tools: List[LLMToolRegistry]) -> List[str]:
    if request.tools.force_call:
        return [request.tools.force_call]

    registered_names = {tool.tool_name for tool in registered_tools if tool.enabled}
    if request.tools.enabled:
        return [name for name in request.tools.enabled if name in registered_names]

    if request.scene_type == "interface_analysis":
        defaults = ["atspi_parse", "ocr"]
    elif request.scene_type == "sop_generation":
        defaults = ["hotspot_fetch", "product_recommend", "chat_analyze"]
    else:
        defaults = ["ocr", "chat_analyze", "file_analyze", "tts", "mark_as_read"]

    return [name for name in defaults if name in registered_names]


def _log_request(
    session: Session,
    request: LLMCoreRequest,
    response_payload: Dict[str, Any],
    status_code: int,
    success: bool,
    execution_time_ms: int,
    model_used: str,
    error_message: str = "",
) -> None:
    try:
        req_id = request.request_id or f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        row = LLMRequestLog(
            request_id=req_id,
            scene_type=request.scene_type,
            user_id=request.user_id,
            model_used=model_used,
            status_code=status_code,
            success=success,
            execution_time_ms=execution_time_ms,
            request_json=_to_json_text(request.model_dump()),
            response_json=_to_json_text(response_payload),
            error_message=error_message,
        )
        session.add(row)
        session.commit()
    except Exception as err:
        session.rollback()
        logger.warning(f"写入LLM请求日志失败: {err}")


@router.get("/llm/tools")
async def list_tools(session: Session = Depends(get_session)):
    _seed_builtin_tools(session)
    tools = session.exec(select(LLMToolRegistry).order_by(LLMToolRegistry.tool_name.asc())).all()
    return {
        "success": True,
        "items": [
            {
                "tool_name": tool.tool_name,
                "description": tool.description,
                "input_schema": _parse_json_text(tool.input_schema),
                "output_schema": _parse_json_text(tool.output_schema),
                "enabled": tool.enabled,
            }
            for tool in tools
        ],
    }


@router.post("/llm/tools/register")
async def register_tool(payload: ToolRegisterRequest, session: Session = Depends(get_session)):
    row = session.exec(select(LLMToolRegistry).where(LLMToolRegistry.tool_name == payload.tool_name)).first()
    if row:
        row.description = payload.description
        row.input_schema = _to_json_text(payload.input_schema)
        row.output_schema = _to_json_text(payload.output_schema)
        row.enabled = payload.enabled
        row.updated_at = datetime.utcnow()
    else:
        row = LLMToolRegistry(
            tool_name=payload.tool_name,
            description=payload.description,
            input_schema=_to_json_text(payload.input_schema),
            output_schema=_to_json_text(payload.output_schema),
            enabled=payload.enabled,
        )
        session.add(row)
    session.commit()

    return {"success": True, "tool_name": payload.tool_name}


@router.get("/llm/scenes")
async def list_scene_configs(session: Session = Depends(get_session)):
    rows = session.exec(select(LLMSceneConfig).order_by(LLMSceneConfig.scene_type.asc())).all()
    return {
        "success": True,
        "items": [
            {
                "scene_type": row.scene_type,
                "config_json": _parse_json_text(row.config_json),
                "enabled": row.enabled,
            }
            for row in rows
        ],
    }


@router.post("/llm/scenes/config")
async def upsert_scene_config(payload: SceneConfigRequest, session: Session = Depends(get_session)):
    if payload.scene_type not in SUPPORTED_SCENES:
        raise HTTPException(status_code=400, detail=f"不支持的scene_type: {payload.scene_type}")

    row = session.exec(select(LLMSceneConfig).where(LLMSceneConfig.scene_type == payload.scene_type)).first()
    if row:
        row.config_json = _to_json_text(payload.config_json)
        row.enabled = payload.enabled
        row.updated_at = datetime.utcnow()
    else:
        row = LLMSceneConfig(
            scene_type=payload.scene_type,
            config_json=_to_json_text(payload.config_json),
            enabled=payload.enabled,
        )
        session.add(row)
    session.commit()

    return {"success": True, "scene_type": payload.scene_type}


@router.get("/llm/logs")
async def list_logs(limit: int = 30, session: Session = Depends(get_session)):
    safe_limit = max(1, min(200, int(limit)))
    rows = session.exec(select(LLMRequestLog).order_by(LLMRequestLog.created_at.desc()).limit(safe_limit)).all()
    return {
        "success": True,
        "items": [
            {
                "request_id": row.request_id,
                "scene_type": row.scene_type,
                "user_id": row.user_id,
                "model_used": row.model_used,
                "status_code": row.status_code,
                "success": row.success,
                "execution_time_ms": row.execution_time_ms,
                "error_message": row.error_message,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


@router.post("/llm/core")
async def llm_core(payload: LLMCoreRequest, session: Session = Depends(get_session)):
    start_at = time.perf_counter()

    _normalize_request(payload)

    req_id = payload.request_id.strip() if payload.request_id else ""
    if not req_id:
        req_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        payload.request_id = req_id

    if payload.scene_type not in SUPPORTED_SCENES:
        raise HTTPException(status_code=400, detail=f"不支持的scene_type: {payload.scene_type}")

    token_optimization = _optimize_request_for_token(payload)

    _seed_builtin_tools(session)

    scene_cfg = session.exec(select(LLMSceneConfig).where(LLMSceneConfig.scene_type == payload.scene_type)).first()
    if scene_cfg and not scene_cfg.enabled:
        raise HTTPException(status_code=403, detail=f"scene_type已禁用: {payload.scene_type}")

    registered_tools = session.exec(select(LLMToolRegistry)).all()
    selected_tools = _pick_enabled_tools(payload, registered_tools)

    tool_calls: List[Dict[str, Any]] = []
    tool_results: Dict[str, Dict[str, Any]] = {}
    for tool_name in selected_tools:
        fn = TOOL_IMPL.get(tool_name)
        if not fn:
            tool_calls.append(
                {
                    "tool_name": tool_name,
                    "status": "skipped",
                    "params": {},
                    "result": {"message": "tool not implemented"},
                }
            )
            continue

        try:
            result = fn(payload)
            tool_results[tool_name] = result
            tool_calls.append(
                {
                    "tool_name": tool_name,
                    "status": "success",
                    "params": payload.tools.custom_params.get(tool_name, {}),
                    "result": result,
                }
            )
        except Exception as tool_err:
            tool_calls.append(
                {
                    "tool_name": tool_name,
                    "status": "failed",
                    "params": payload.tools.custom_params.get(tool_name, {}),
                    "result": {"error": str(tool_err)},
                }
            )

    llm_prompt = (
        f"scene_type={payload.scene_type}\n"
        f"input_text={payload.input.text}\n"
        f"structured_data={json.dumps(payload.input.structured_data, ensure_ascii=False)}\n"
        f"tool_results={json.dumps(tool_results, ensure_ascii=False)}"
    )

    llm_result = await _call_llm_text(
        scene_type=payload.scene_type,
        prompt_text=llm_prompt,
        context=payload.context.model_dump(),
        model_preference=payload.config.model_preference,
    )

    output_structured = _build_scene_structured(payload.scene_type, payload, tool_results)
    output_text = llm_result.get("text", "")
    output_audio = tool_results.get("tts", {}).get("audio")
    output_images = payload.input.images[:1] if payload.input.images else []
    output_emoji = "😊" if payload.scene_type == "sop_generation" else "👍"

    actions = _build_actions(payload.scene_type, payload, output_structured)

    elapsed_ms = int((time.perf_counter() - start_at) * 1000)

    response_payload = {
        "code": 0,
        "msg": "success",
        "request_id": req_id,
        "scene_type": payload.scene_type,
        "model_used": llm_result.get("model_used", "fallback"),
        "execution_time": elapsed_ms,
        "data": {
            "output": {
                "text": output_text,
                "audio": output_audio,
                "images": output_images,
                "emoji": output_emoji,
                "structured": output_structured,
            },
            "tool_calls": tool_calls,
            "actions": actions,
            "ext": {
                "scene_config": _parse_json_text(scene_cfg.config_json) if scene_cfg else {},
                "selected_tools": selected_tools,
                "action_types": ACTION_TYPES,
                "token_optimization": token_optimization,
                "legacy_compat": {
                    "response": output_text,
                    "routing_intent": payload.scene_type,
                },
            },
        },
    }

    _log_request(
        session=session,
        request=payload,
        response_payload=response_payload,
        status_code=200,
        success=True,
        execution_time_ms=elapsed_ms,
        model_used=str(response_payload.get("model_used", "")),
    )

    if payload.config.response_format == "compact_json":
        return _build_compact_response(response_payload)
    return response_payload


@router.get("/llm/schema")
async def get_llm_schema():
    return {
        "success": True,
        "supported_scenes": sorted(list(SUPPORTED_SCENES)),
        "scene_aliases": SCENE_ALIASES,
        "model_preferences": MODEL_PREFERENCES,
        "action_types": ACTION_TYPES,
        "request_schema": {
            "request_id": "req_20260222_001",
            "scene_type": "interface_analysis",
            "user_id": "user_001",
            "context": {"history": [], "session_id": "session_xxx"},
            "input": {
                "text": "文字内容",
                "images": ["base64_1"],
                "audio": None,
                "files": ["file_url_1"],
                "structured_data": {},
            },
            "tools": {
                "enabled": ["ocr", "atspi_parse", "hotspot_fetch", "file_analyze"],
                "force_call": None,
                "custom_params": {},
            },
            "config": {
                "model_preference": "auto",
                "response_format": "json",
                "timeout": 30000,
                "ext": {
                    "max_history": 10,
                    "max_images": 1,
                    "max_text_chars": 2000,
                },
            },
        },
        "compact_request_schema": {
            "scene": "interface_analysis",
            "hist": [],
            "text": "请分析界面并输出结构化结果",
            "img": "base64_or_url",
            "tools": ["ocr", "atspi_parse"],
            "model_route": "auto",
            "need_struct_output": True,
        },
        "response_schema": {
            "code": 0,
            "msg": "success",
            "request_id": "req_20260222_001",
            "scene_type": "interface_analysis",
            "model_used": "local-llm",
            "execution_time": 1200,
            "data": {
                "output": {
                    "text": "文字回复",
                    "audio": None,
                    "images": [],
                    "emoji": "👍",
                    "structured": {},
                },
                "tool_calls": [],
                "actions": [],
                "ext": {},
            },
        },
        "compact_response_schema": {
            "text": "文字回复",
            "emoji": "👍",
            "struct": {},
            "tools": [],
            "actions": [],
            "meta": {
                "request_id": "req_20260222_001",
                "scene_type": "interface_analysis",
                "model_used": "local",
                "execution_time": 1200,
            },
        },
        "scene_contracts": {
            "interface_analysis": {
                "required_input": ["input.structured_data.window_info", "input.structured_data.atspi_tree"],
                "required_output": ["data.output.structured.page_type", "data.output.structured.controls"],
            },
            "sop_generation": {
                "required_input": ["input.structured_data.customer_info", "input.structured_data.chat_history"],
                "required_output": ["data.output.structured.sop_name", "data.output.structured.steps"],
            },
            "multimodal_chat": {
                "required_input": ["input.text|input.images|input.audio|input.files 任一"],
                "required_output": ["data.output.text", "data.actions"],
            },
            "system_evolution": {
                "required_input": ["input.structured_data.analysis_scope"],
                "required_output": ["data.output.structured.optimization_actions"],
            },
        },
        "token_policy": {
            "principles": [
                "local_first",
                "minimal_input",
                "minimal_output",
                "batch_and_cache",
                "structured_only",
            ],
            "default_limits": {
                "max_history": 10,
                "max_images": 1,
                "max_text_chars": 2000,
            },
        },
    }
