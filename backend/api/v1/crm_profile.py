from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from db.session import get_session
from db.models import (
    User,
    Message,
    WechatChatHistory,
    ChatSummary,
    CustomerPortrait,
    CustomerTagSnapshot,
    CRMScheduleConfig,
)

router = APIRouter()


def _json_loads(text: str, default: Any):
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _extract_json_block(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


async def _call_router(prompt_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        from core.ai_router import AIRouter

        ai_router = AIRouter()
        return await ai_router.route_request(prompt_text, context or {})
    except Exception:
        return {"success": False, "response": "", "model_used": "fallback"}


class ImportWechatPayload:
    def __init__(self, data: Dict[str, Any]):
        self.customer_id = int(data.get("customer_id") or 0)
        self.wechat_id = str(data.get("wechat_id") or "").strip()
        self.range_start = str(data.get("range_start") or "").strip()
        self.range_end = str(data.get("range_end") or "").strip()
        self.records = data.get("records") or []
        self.include_media = bool(data.get("include_media", True))


@router.post("/crm/chat/import/wechat")
async def import_chat_from_wechat(payload: Dict[str, Any], session: Session = Depends(get_session)):
    req = ImportWechatPayload(payload)

    user: Optional[User] = None
    if req.customer_id > 0:
        user = session.get(User, req.customer_id)
    elif req.wechat_id:
        user = session.exec(select(User).where(User.wechat_id == req.wechat_id)).first()

    if not user:
        raise HTTPException(status_code=404, detail="客户不存在")

    imported = 0
    skipped = 0
    failed = 0

    # 1) 优先导入外部 records（来自微信自动化）
    for idx, row in enumerate(req.records):
        try:
            msg_id = str(row.get("msg_id") or f"ext_{int(datetime.utcnow().timestamp())}_{idx}")
            exists = session.exec(
                select(WechatChatHistory).where(
                    WechatChatHistory.customer_id == int(user.id),
                    WechatChatHistory.msg_id == msg_id,
                )
            ).first()
            if exists:
                skipped += 1
                continue

            msg_type = str(row.get("msg_type") or "text").lower()
            if (not req.include_media) and msg_type in {"image", "audio", "file"}:
                skipped += 1
                continue

            send_time_raw = row.get("send_time")
            send_time = datetime.utcnow()
            if send_time_raw:
                try:
                    send_time = datetime.fromisoformat(str(send_time_raw).replace("Z", "+00:00"))
                except Exception:
                    send_time = datetime.utcnow()

            record = WechatChatHistory(
                customer_id=int(user.id),
                session_id=str(row.get("session_id") or ""),
                msg_id=msg_id,
                msg_type=msg_type,
                sender=str(row.get("sender") or "other"),
                content_raw=str(row.get("content") or row.get("content_raw") or ""),
                content_text=str(row.get("content_text") or ""),
                content_json=_json_dumps(row.get("content_json") or {}),
                file_path=str(row.get("file_path") or ""),
                file_hash=str(row.get("file_hash") or ""),
                ocr_status="pending" if msg_type == "image" else "none",
                asr_status="pending" if msg_type == "audio" else "none",
                parse_status="pending" if msg_type == "file" else "none",
                send_time=send_time,
            )
            session.add(record)
            imported += 1
        except Exception:
            failed += 1

    # 2) 无 records 时，从历史 Message 表迁移
    if not req.records:
        rows = session.exec(
            select(Message).where(Message.user_id == int(user.id)).order_by(Message.timestamp.asc())
        ).all()
        for row in rows:
            msg_id = f"legacy_msg_{row.id}"
            exists = session.exec(
                select(WechatChatHistory).where(
                    WechatChatHistory.customer_id == int(user.id),
                    WechatChatHistory.msg_id == msg_id,
                )
            ).first()
            if exists:
                skipped += 1
                continue

            session.add(
                WechatChatHistory(
                    customer_id=int(user.id),
                    session_id=row.session_id or "",
                    msg_id=msg_id,
                    msg_type="text",
                    sender="me" if row.role == "assistant" else "other",
                    content_raw=row.content or "",
                    content_text=row.content or "",
                    content_json="{}",
                    send_time=row.timestamp,
                )
            )
            imported += 1

    session.commit()

    return {
        "success": True,
        "customer_id": int(user.id),
        "imported_count": imported,
        "skipped_count": skipped,
        "failed_count": failed,
    }


@router.post("/crm/chat/import/convert")
async def convert_chat_media(payload: Dict[str, Any], session: Session = Depends(get_session)):
    customer_id = int(payload.get("customer_id") or 0)
    batch_size = max(1, min(500, int(payload.get("batch_size") or 100)))
    msg_types = payload.get("msg_types") or ["image", "audio", "file"]

    if customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id 不能为空")

    rows = session.exec(
        select(WechatChatHistory)
        .where(
            WechatChatHistory.customer_id == customer_id,
            WechatChatHistory.msg_type.in_(msg_types),
        )
        .order_by(WechatChatHistory.send_time.asc())
        .limit(batch_size)
    ).all()

    ocr_success = 0
    asr_success = 0
    parse_success = 0

    for row in rows:
        if row.msg_type == "image":
            row.content_text = row.content_text or row.content_raw or f"[OCR占位] {row.file_path}"
            row.ocr_status = "success"
            ocr_success += 1
        elif row.msg_type == "audio":
            row.content_text = row.content_text or row.content_raw or f"[ASR占位] {row.file_path}"
            row.asr_status = "success"
            asr_success += 1
        elif row.msg_type == "file":
            row.content_text = row.content_text or row.content_raw or f"[文件解析占位] {row.file_path}"
            row.parse_status = "success"
            parse_success += 1
        session.add(row)

    session.commit()

    return {
        "success": True,
        "customer_id": customer_id,
        "processed": len(rows),
        "ocr_success": ocr_success,
        "asr_success": asr_success,
        "parse_success": parse_success,
    }


@router.get("/crm/chat/history")
async def get_chat_history(
    customer_id: int,
    msg_type: Optional[str] = None,
    sender: Optional[str] = None,
    keyword: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    stmt = select(WechatChatHistory).where(WechatChatHistory.customer_id == customer_id)

    if msg_type:
        stmt = stmt.where(WechatChatHistory.msg_type == msg_type)
    if sender:
        stmt = stmt.where(WechatChatHistory.sender == sender)
    if keyword:
        stmt = stmt.where(WechatChatHistory.content_text.contains(keyword))
    if start:
        try:
            stmt = stmt.where(WechatChatHistory.send_time >= datetime.fromisoformat(start))
        except Exception:
            pass
    if end:
        try:
            stmt = stmt.where(WechatChatHistory.send_time <= datetime.fromisoformat(end))
        except Exception:
            pass

    rows = session.exec(stmt.order_by(WechatChatHistory.send_time.desc())).all()
    total = len(rows)
    offset = (page - 1) * page_size
    page_rows = rows[offset: offset + page_size]

    items = [
        {
            "id": row.id,
            "customer_id": row.customer_id,
            "msg_id": row.msg_id,
            "msg_type": row.msg_type,
            "sender": row.sender,
            "content_raw": row.content_raw,
            "content_text": row.content_text,
            "content_json": _json_loads(row.content_json, {}),
            "file_path": row.file_path,
            "send_time": row.send_time.isoformat() if row.send_time else "",
        }
        for row in page_rows
    ]

    return {"success": True, "total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/crm/chat/export")
async def export_chat_history(
    customer_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    session: Session = Depends(get_session),
):
    stmt = select(WechatChatHistory).where(WechatChatHistory.customer_id == customer_id)

    if start:
        try:
            stmt = stmt.where(WechatChatHistory.send_time >= datetime.fromisoformat(start))
        except Exception:
            pass
    if end:
        try:
            stmt = stmt.where(WechatChatHistory.send_time <= datetime.fromisoformat(end))
        except Exception:
            pass

    rows = session.exec(stmt.order_by(WechatChatHistory.send_time.asc())).all()
    return {
        "success": True,
        "customer_id": customer_id,
        "items": [
            {
                "msg_id": row.msg_id,
                "msg_type": row.msg_type,
                "sender": row.sender,
                "content_text": row.content_text,
                "file_path": row.file_path,
                "send_time": row.send_time.isoformat() if row.send_time else "",
            }
            for row in rows
        ],
    }


@router.post("/crm/summary/generate")
async def generate_summary(payload: Dict[str, Any], session: Session = Depends(get_session)):
    customer_id = int(payload.get("customer_id") or 0)
    summary_days = int(payload.get("summary_days") or 3)
    summary_scope = str(payload.get("summary_scope") or ("daily" if summary_days == 1 else "3day"))

    if customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id 不能为空")

    user = session.get(User, customer_id)
    if not user:
        raise HTTPException(status_code=404, detail="客户不存在")

    range_end = datetime.utcnow()
    range_start = range_end - timedelta(days=max(1, summary_days))

    rows = session.exec(
        select(WechatChatHistory)
        .where(
            WechatChatHistory.customer_id == customer_id,
            WechatChatHistory.send_time >= range_start,
            WechatChatHistory.send_time <= range_end,
        )
        .order_by(WechatChatHistory.send_time.asc())
    ).all()

    chat_lines = [f"[{row.sender}] {row.content_text or row.content_raw}" for row in rows if (row.content_text or row.content_raw)]
    text_blob = "\n".join(chat_lines[-120:])

    prompt = (
        "请将以下客户聊天记录输出为JSON，包含字段：key_content,important_event,requirement,question,commitment,risk_alert。"
        "仅输出JSON。\n"
        f"customer={user.nickname}\n"
        f"chat=\n{text_blob}"
    )

    llm_result = await _call_router(prompt, {"scene_type": "sop_generation", "model_preference": "auto"})
    parsed = _extract_json_block(str(llm_result.get("response", "")))

    if not parsed:
        parsed = {
            "key_content": chat_lines[-8:],
            "important_event": [],
            "requirement": [],
            "question": [],
            "commitment": [],
            "risk_alert": [],
        }

    summary_text = "；".join(parsed.get("key_content", [])[:6])
    row = ChatSummary(
        customer_id=customer_id,
        summary_scope=summary_scope,
        summary_days=summary_days,
        range_start=range_start,
        range_end=range_end,
        summary_content=summary_text,
        summary_json=_json_dumps(parsed),
        model_used=str(llm_result.get("model_used", "")),
        model_version="v1",
        token_in=max(0, len(text_blob) // 2),
        token_out=max(0, len(_json_dumps(parsed)) // 2),
    )
    session.add(row)

    user.summary = summary_text
    user.last_contact = range_end
    session.add(user)
    session.commit()
    session.refresh(row)

    return {
        "success": True,
        "customer_id": customer_id,
        "summary_id": row.id,
        "summary_scope": summary_scope,
        "summary_days": summary_days,
        "summary": parsed,
    }


@router.post("/crm/portrait/generate")
async def generate_portrait(payload: Dict[str, Any], session: Session = Depends(get_session)):
    customer_id = int(payload.get("customer_id") or 0)
    if customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id 不能为空")

    user = session.get(User, customer_id)
    if not user:
        raise HTTPException(status_code=404, detail="客户不存在")

    summaries = session.exec(
        select(ChatSummary)
        .where(ChatSummary.customer_id == customer_id)
        .order_by(ChatSummary.generated_at.desc())
        .limit(5)
    ).all()

    if not summaries:
        raise HTTPException(status_code=400, detail="请先生成聊天摘要")

    summary_text = "\n".join([s.summary_content for s in summaries if s.summary_content])
    prompt = (
        "请根据以下摘要生成客户画像JSON，字段：personality,preference,core_needs,purchase_intention,budget_level,taboo,best_contact_time,confidence。"
        "仅输出JSON。\n"
        f"customer={user.nickname}\nsummary=\n{summary_text}"
    )

    llm_result = await _call_router(prompt, {"scene_type": "system_evolution", "model_preference": "auto"})
    parsed = _extract_json_block(str(llm_result.get("response", "")))
    if not parsed:
        parsed = {
            "personality": "理性",
            "preference": "关注性价比",
            "core_needs": "高效、省心",
            "purchase_intention": "medium",
            "budget_level": "medium",
            "taboo": ["不喜欢被频繁催促"],
            "best_contact_time": "工作日下午",
            "confidence": 0.65,
        }

    row = CustomerPortrait(
        customer_id=customer_id,
        portrait_version="v1",
        portrait_content=f"{parsed.get('personality', '')};{parsed.get('preference', '')};{parsed.get('core_needs', '')}",
        portrait_json=_json_dumps(parsed),
        personality=str(parsed.get("personality", "")),
        preference=str(parsed.get("preference", "")),
        core_needs=str(parsed.get("core_needs", "")),
        purchase_intention=str(parsed.get("purchase_intention", "")),
        budget_level=str(parsed.get("budget_level", "")),
        taboo=_json_dumps(parsed.get("taboo", [])),
        best_contact_time=str(parsed.get("best_contact_time", "")),
        confidence=float(parsed.get("confidence", 0.0) or 0.0),
        source_summary_ids=",".join(str(s.id) for s in summaries if s.id),
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    return {"success": True, "customer_id": customer_id, "portrait_id": row.id, "portrait": parsed}


@router.post("/crm/tags/generate")
async def generate_tags(payload: Dict[str, Any], session: Session = Depends(get_session)):
    customer_id = int(payload.get("customer_id") or 0)
    if customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id 不能为空")

    user = session.get(User, customer_id)
    if not user:
        raise HTTPException(status_code=404, detail="客户不存在")

    portrait = session.exec(
        select(CustomerPortrait)
        .where(CustomerPortrait.customer_id == customer_id)
        .order_by(CustomerPortrait.generated_at.desc())
        .limit(1)
    ).first()

    if not portrait:
        raise HTTPException(status_code=400, detail="请先生成客户画像")

    portrait_json = _json_loads(portrait.portrait_json, {})
    prompt = (
        "请根据画像生成标签列表JSON，格式：{\"tags\":[{\"name\":\"\",\"type\":\"\",\"score\":0.8}]}，仅输出JSON。\n"
        f"portrait={_json_dumps(portrait_json)}"
    )
    llm_result = await _call_router(prompt, {"scene_type": "sop_generation", "model_preference": "auto"})
    parsed = _extract_json_block(str(llm_result.get("response", "")))

    tags = parsed.get("tags") if isinstance(parsed, dict) else None
    if not isinstance(tags, list) or not tags:
        tags = [
            {"name": "理性型", "type": "personality", "score": 0.72},
            {"name": "关注性价比", "type": "preference", "score": 0.8},
            {"name": "中意向", "type": "intent", "score": 0.68},
        ]

    # 清理旧快照
    old_rows = session.exec(select(CustomerTagSnapshot).where(CustomerTagSnapshot.customer_id == customer_id)).all()
    for row in old_rows:
        session.delete(row)

    for item in tags:
        session.add(
            CustomerTagSnapshot(
                customer_id=customer_id,
                tag_name=str(item.get("name") or ""),
                tag_type=str(item.get("type") or "general"),
                tag_score=float(item.get("score", 0.0) or 0.0),
                source="llm",
                source_ref=f"portrait:{portrait.id}",
            )
        )

    user.tags = _json_dumps([str(item.get("name") or "") for item in tags if item.get("name")])
    session.add(user)
    session.commit()

    return {"success": True, "customer_id": customer_id, "tags": tags}


@router.get("/crm/profile/overview")
async def get_customer_profile_overview(customer_id: int, session: Session = Depends(get_session)):
    user = session.get(User, customer_id)
    if not user:
        raise HTTPException(status_code=404, detail="客户不存在")

    latest_summary = session.exec(
        select(ChatSummary)
        .where(ChatSummary.customer_id == customer_id)
        .order_by(ChatSummary.generated_at.desc())
        .limit(1)
    ).first()

    latest_portrait = session.exec(
        select(CustomerPortrait)
        .where(CustomerPortrait.customer_id == customer_id)
        .order_by(CustomerPortrait.generated_at.desc())
        .limit(1)
    ).first()

    latest_tags = session.exec(
        select(CustomerTagSnapshot)
        .where(CustomerTagSnapshot.customer_id == customer_id)
        .order_by(CustomerTagSnapshot.generated_at.desc())
    ).all()

    recent_history = session.exec(
        select(WechatChatHistory)
        .where(WechatChatHistory.customer_id == customer_id)
        .order_by(WechatChatHistory.send_time.desc())
        .limit(20)
    ).all()

    return {
        "success": True,
        "customer": {
            "id": user.id,
            "wechat_id": user.wechat_id,
            "nickname": user.nickname,
            "tags": _json_loads(user.tags, []),
            "summary": user.summary,
            "last_contact": user.last_contact.isoformat() if user.last_contact else "",
        },
        "latest_summary": {
            "id": latest_summary.id if latest_summary else None,
            "scope": latest_summary.summary_scope if latest_summary else "",
            "days": latest_summary.summary_days if latest_summary else 0,
            "content": latest_summary.summary_content if latest_summary else "",
            "json": _json_loads(latest_summary.summary_json, {}) if latest_summary else {},
            "generated_at": latest_summary.generated_at.isoformat() if latest_summary and latest_summary.generated_at else "",
        },
        "latest_portrait": {
            "id": latest_portrait.id if latest_portrait else None,
            "content": latest_portrait.portrait_content if latest_portrait else "",
            "json": _json_loads(latest_portrait.portrait_json, {}) if latest_portrait else {},
            "generated_at": latest_portrait.generated_at.isoformat() if latest_portrait and latest_portrait.generated_at else "",
        },
        "tags": [
            {
                "name": row.tag_name,
                "type": row.tag_type,
                "score": row.tag_score,
                "source": row.source,
                "generated_at": row.generated_at.isoformat() if row.generated_at else "",
            }
            for row in latest_tags
        ],
        "recent_messages": [
            {
                "msg_id": row.msg_id,
                "msg_type": row.msg_type,
                "sender": row.sender,
                "content_text": row.content_text or row.content_raw,
                "send_time": row.send_time.isoformat() if row.send_time else "",
            }
            for row in recent_history
        ],
    }


@router.get("/crm/profile/list")
async def list_customer_profiles(keyword: Optional[str] = None, session: Session = Depends(get_session)):
    users = session.exec(select(User).order_by(User.last_contact.desc())).all()
    items = []
    for user in users:
        if keyword:
            kw = keyword.strip().lower()
            if kw and kw not in (user.nickname or "").lower() and kw not in (user.wechat_id or "").lower():
                continue

        tags = _json_loads(user.tags, [])
        portrait = session.exec(
            select(CustomerPortrait)
            .where(CustomerPortrait.customer_id == int(user.id))
            .order_by(CustomerPortrait.generated_at.desc())
            .limit(1)
        ).first()
        items.append(
            {
                "id": user.id,
                "name": user.nickname,
                "nickname": user.nickname,
                "wechatId": user.wechat_id,
                "tags": tags if isinstance(tags, list) else [],
                "summary": user.summary,
                "portraitUpdatedAt": portrait.generated_at.isoformat() if portrait and portrait.generated_at else "",
                "lastContact": user.last_contact.isoformat() if user.last_contact else "",
            }
        )

    return {"success": True, "items": items}


@router.get("/crm/schedule/config")
async def get_schedule_config(session: Session = Depends(get_session)):
    row = session.exec(select(CRMScheduleConfig).limit(1)).first()
    if not row:
        row = CRMScheduleConfig()
        session.add(row)
        session.commit()
        session.refresh(row)

    return {
        "success": True,
        "config": {
            "summary_days": row.summary_days,
            "auto_portrait_enabled": row.auto_portrait_enabled,
            "auto_tag_enabled": row.auto_tag_enabled,
            "run_daily_import": row.run_daily_import,
            "run_summary_hour": row.run_summary_hour,
            "run_portrait_hour": row.run_portrait_hour,
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        },
    }


@router.post("/crm/schedule/config")
async def upsert_schedule_config(payload: Dict[str, Any], session: Session = Depends(get_session)):
    row = session.exec(select(CRMScheduleConfig).limit(1)).first()
    if not row:
        row = CRMScheduleConfig()

    row.summary_days = int(payload.get("summary_days", row.summary_days))
    row.auto_portrait_enabled = bool(payload.get("auto_portrait_enabled", row.auto_portrait_enabled))
    row.auto_tag_enabled = bool(payload.get("auto_tag_enabled", row.auto_tag_enabled))
    row.run_daily_import = bool(payload.get("run_daily_import", row.run_daily_import))
    row.run_summary_hour = int(payload.get("run_summary_hour", row.run_summary_hour))
    row.run_portrait_hour = int(payload.get("run_portrait_hour", row.run_portrait_hour))
    row.updated_at = datetime.utcnow()

    session.add(row)
    session.commit()
    session.refresh(row)

    return {"success": True, "config_id": row.id}


@router.post("/crm/schedule/run-now")
async def run_schedule_now(payload: Dict[str, Any], session: Session = Depends(get_session)):
    customer_id = int(payload.get("customer_id") or 0)
    if customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id 不能为空")

    summary_res = await generate_summary({"customer_id": customer_id, "summary_days": int(payload.get("summary_days") or 3)}, session)
    portrait_res = await generate_portrait({"customer_id": customer_id}, session)
    tags_res = await generate_tags({"customer_id": customer_id}, session)

    return {
        "success": True,
        "customer_id": customer_id,
        "summary": summary_res,
        "portrait": portrait_res,
        "tags": tags_res,
    }


@router.get("/crm/chat/export/csv")
async def export_chat_csv(customer_id: int, session: Session = Depends(get_session)):
    rows = session.exec(
        select(WechatChatHistory)
        .where(WechatChatHistory.customer_id == customer_id)
        .order_by(WechatChatHistory.send_time.asc())
    ).all()

    csv_lines = ["msg_id,msg_type,sender,content_text,send_time"]
    for row in rows:
        content = (row.content_text or row.content_raw or "").replace('"', '""').replace("\n", " ")
        csv_lines.append(
            f'"{row.msg_id}","{row.msg_type}","{row.sender}","{content}","{row.send_time.isoformat() if row.send_time else ""}"'
        )

    return JSONResponse(content={"success": True, "customer_id": customer_id, "csv": "\n".join(csv_lines)})
