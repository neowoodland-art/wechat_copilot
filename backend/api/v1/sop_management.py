# /home/neogh/wechat_copilot/backend/api/v1/sop_management.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/sop", tags=["sop"])

# 数据模型定义
class Position(BaseModel):
    x: int
    y: int

class NodeProperties(BaseModel):
    name: str
    duration: Optional[int] = None
    messageType: Optional[str] = None
    content: Optional[str] = None
    delayBeforeSend: Optional[int] = None
    randomVariations: Optional[List[str]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    tagsToAdd: Optional[List[str]] = None
    tagsToRemove: Optional[List[str]] = None
    targetElement: Optional[str] = None
    expectedText: Optional[str] = None
    timeout: Optional[int] = None

class Node(BaseModel):
    id: str
    type: str
    name: str
    position: Position
    properties: NodeProperties
    next: List[str]

class Edge(BaseModel):
    id: str
    source: str
    target: str
    type: str

class Variable(BaseModel):
    name: str
    type: str
    source: str

class ErrorHandling(BaseModel):
    retryAttempts: int = 3
    retryDelay: int = 5000
    fallbackSop: Optional[str] = None
    notificationOnFailure: bool = True

class Analytics(BaseModel):
    trackMetrics: List[str]
    reportingSchedule: str = "daily"

class TriggerCondition(BaseModel):
    type: str
    params: Dict[str, Any]

class SOPDefinition(BaseModel):
    id: str
    name: str
    description: str
    version: str
    createdBy: str = "system"
    createdAt: str = datetime.now().isoformat()
    updatedAt: str = datetime.now().isoformat()
    isActive: bool = True
    triggerConditions: Optional[List[TriggerCondition]] = []
    nodes: List[Node]
    edges: List[Edge]
    variables: Optional[List[Variable]] = []
    errorHandling: ErrorHandling = ErrorHandling()
    analytics: Analytics = Analytics()

class SOPRequest(BaseModel):
    sopDefinition: SOPDefinition

class SOPResponse(BaseModel):
    success: bool
    data: Optional[SOPDefinition] = None
    message: Optional[str] = None

class SOPListResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    pagination: Dict[str, int]

class ExecuteSOPRequest(BaseModel):
    targetCustomerId: str
    context: Dict[str, Any]

class ExecuteSOPResponse(BaseModel):
    success: bool
    executionId: str
    status: str
    estimatedCompletion: str

# 模拟数据库存储
sops_db = {}

@router.post("/", response_model=SOPResponse)
async def create_sop(request: SOPRequest):
    """创建新SOP"""
    try:
        sop_definition = request.sopDefinition
        sop_id = sop_definition.id
        
        # 生成唯一ID（如果未提供）
        if not sop_id or sop_id == "":
            sop_id = f"sop_{uuid.uuid4().hex[:8]}"
            sop_definition.id = sop_id
        
        # 存储SOP定义
        sops_db[sop_id] = sop_definition.dict()
        
        return SOPResponse(
            success=True,
            data=sop_definition,
            message="SOP创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SOP创建失败: {str(e)}")

@router.get("/", response_model=SOPListResponse)
async def get_sops(page: int = 1, size: int = 10):
    """获取SOP列表"""
    try:
        all_sops = list(sops_db.values())
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        page_sops = all_sops[start_idx:end_idx]
        
        # 转换为简化格式
        simplified_sops = []
        for sop in page_sops:
            simplified_sops.append({
                "id": sop["id"],
                "name": sop["name"],
                "status": "active" if sop["isActive"] else "inactive",
                "stepsCount": len(sop["nodes"]),
                "lastExecuted": "2026-02-16T09:30:00Z",  # 示例值
                "successRate": 85.5  # 示例值
            })
        
        return SOPListResponse(
            success=True,
            data=simplified_sops,
            pagination={
                "page": page,
                "size": size,
                "total": len(all_sops)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取SOP列表失败: {str(e)}")

@router.get("/{sop_id}", response_model=SOPResponse)
async def get_sop(sop_id: str):
    """获取特定SOP详情"""
    try:
        if sop_id not in sops_db:
            raise HTTPException(status_code=404, detail="SOP不存在")
        
        sop_data = sops_db[sop_id]
        sop_definition = SOPDefinition(**sop_data)
        
        return SOPResponse(
            success=True,
            data=sop_definition
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取SOP详情失败: {str(e)}")

@router.put("/{sop_id}", response_model=SOPResponse)
async def update_sop(sop_id: str, request: SOPRequest):
    """更新SOP"""
    try:
        if sop_id not in sops_db:
            raise HTTPException(status_code=404, detail="SOP不存在")
        
        sop_definition = request.sopDefinition
        sop_definition.id = sop_id  # 确保ID不变
        sop_definition.updatedAt = datetime.now().isoformat()  # 更新时间
        
        # 更新SOP定义
        sops_db[sop_id] = sop_definition.dict()
        
        return SOPResponse(
            success=True,
            data=sop_definition,
            message="SOP更新成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SOP更新失败: {str(e)}")

@router.delete("/{sop_id}", response_model=SOPResponse)
async def delete_sop(sop_id: str):
    """删除SOP"""
    try:
        if sop_id not in sops_db:
            raise HTTPException(status_code=404, detail="SOP不存在")
        
        del sops_db[sop_id]
        
        return SOPResponse(
            success=True,
            message="SOP删除成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SOP删除失败: {str(e)}")

@router.post("/{sop_id}/execute", response_model=ExecuteSOPResponse)
async def execute_sop(sop_id: str, request: ExecuteSOPRequest):
    """执行SOP"""
    try:
        if sop_id not in sops_db:
            raise HTTPException(status_code=404, detail="SOP不存在")
        
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # 这里应该调用实际的SOP执行逻辑
        # 为了示例，我们只是返回一个执行ID
        
        return ExecuteSOPResponse(
            success=True,
            executionId=execution_id,
            status="started",
            estimatedCompletion=(datetime.now().timestamp() + 300).isoformat()  # 5分钟后
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SOP执行失败: {str(e)}")

@router.get("/{sop_id}/execution/{execution_id}")
async def get_execution_status(sop_id: str, execution_id: str):
    """获取SOP执行状态"""
    try:
        if sop_id not in sops_db:
            raise HTTPException(status_code=404, detail="SOP不存在")
        
        # 返回示例执行状态
        return {
            "success": True,
            "data": {
                "executionId": execution_id,
                "sopId": sop_id,
                "status": "completed",
                "progress": 100,
                "startTime": datetime.now().isoformat(),
                "endTime": datetime.now().isoformat(),
                "results": [
                    {
                        "nodeId": "node_001",
                        "status": "completed",
                        "output": "等待完成"
                    },
                    {
                        "nodeId": "node_002",
                        "status": "completed",
                        "output": "消息已发送"
                    }
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取执行状态失败: {str(e)}")
