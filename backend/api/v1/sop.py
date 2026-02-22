from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from db.session import get_session
from db.models import SopRule
from datetime import datetime
import json

router = APIRouter()

@router.get("/sop-rules")
async def get_sop_rules(session: Session = Depends(get_session)):
    """获取 SOP 规则列表"""
    rules = session.exec(select(SopRule)).all()
    
    result = []
    for rule in rules:
        result.append({
            "id": rule.id,
            "name": rule.name,
            "trigger_keyword": rule.trigger_keyword,
            "reply_template": rule.reply_template,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat()
        })
    
    return result

@router.get("/sop-rules/{rule_id}")
async def get_sop_rule(rule_id: int, session: Session = Depends(get_session)):
    """获取单个 SOP 规则"""
    rule = session.exec(select(SopRule).where(SopRule.id == rule_id)).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "trigger_keyword": rule.trigger_keyword,
        "reply_template": rule.reply_template,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat()
    }

@router.post("/sop-rules")
async def create_sop_rule(rule_data: dict, session: Session = Depends(get_session)):
    """创建 SOP 规则"""
    rule = SopRule(
        name=rule_data.get("name"),
        trigger_keyword=rule_data.get("trigger_keyword"),
        reply_template=rule_data.get("reply_template"),
        enabled=rule_data.get("enabled", True),
        priority=rule_data.get("priority", 1)
    )
    
    session.add(rule)
    session.commit()
    session.refresh(rule)
    
    return {
        "id": rule.id,
        "name": rule.name,
        "trigger_keyword": rule.trigger_keyword,
        "reply_template": rule.reply_template,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat()
    }

@router.put("/sop-rules/{rule_id}")
async def update_sop_rule(rule_id: int, rule_data: dict, session: Session = Depends(get_session)):
    """更新 SOP 规则"""
    rule = session.exec(select(SopRule).where(SopRule.id == rule_id)).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 更新字段
    if "name" in rule_data:
        rule.name = rule_data["name"]
    if "trigger_keyword" in rule_data:
        rule.trigger_keyword = rule_data["trigger_keyword"]
    if "reply_template" in rule_data:
        rule.reply_template = rule_data["reply_template"]
    if "enabled" in rule_data:
        rule.enabled = rule_data["enabled"]
    if "priority" in rule_data:
        rule.priority = rule_data["priority"]
    
    rule.updated_at = datetime.now()
    
    session.add(rule)
    session.commit()
    session.refresh(rule)
    
    return {
        "id": rule.id,
        "name": rule.name,
        "trigger_keyword": rule.trigger_keyword,
        "reply_template": rule.reply_template,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat()
    }

@router.delete("/sop-rules/{rule_id}")
async def delete_sop_rule(rule_id: int, session: Session = Depends(get_session)):
    """删除 SOP 规则"""
    rule = session.exec(select(SopRule).where(SopRule.id == rule_id)).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    session.delete(rule)
    session.commit()
    return {"message": "规则删除成功"}
