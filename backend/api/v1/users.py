from fastapi import APIRouter, HTTPException
from db.session import get_session
from db.models import User
from sqlmodel import select
import json

router = APIRouter()

@router.get("/users")
async def get_users():
    """获取所有用户"""
    with next(get_session()) as session:
        users = session.exec(select(User)).all()
        return users

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """获取单个用户"""
    with next(get_session()) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

@router.put("/users/{user_id}")
async def update_user(user_id: int, data: dict):
    """更新用户信息"""
    with next(get_session()) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新字段
        if "nickname" in data:
            user.nickname = data["nickname"]
        if "tags" in data:
            user.tags = json.dumps(data["tags"])
        if "summary" in data:
            user.summary = data["summary"]
        
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """删除用户"""
    with next(get_session()) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        session.delete(user)
        session.commit()
        return {"message": "用户删除成功"}