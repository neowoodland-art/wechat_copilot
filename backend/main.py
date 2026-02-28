import sys
import os

# 获取项目根目录并添加到Python路径，确保能找到rpa模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db.session import create_tables
from api.v1 import users, messages, sop, rpa, rpa_control, wechat_ops, layout_control, atspi_analysis, llm_core, crm_profile, wechat_api_framework, rpa_definition
from api.v1.rpa_compatibility import router as rpa_compat_router

# 从backend.core导入配置
from backend.core.config import settings

# 条件导入API模块
try:
    from api.v1 import ui_analysis, message_ops
    UI_ANALYSIS_ENABLED = True
except ImportError as e:
    print(f"警告: UI分析模块加载失败: {e}")
    ui_analysis = None
    message_ops = None
    UI_ANALYSIS_ENABLED = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    create_tables()
    yield
    # 关闭时
    pass

app = FastAPI(title="WeChat Copilot Backend", lifespan=lifespan)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(messages.router, prefix="/api/v1", tags=["messages"])
app.include_router(sop.router, prefix="/api/v1", tags=["sop"])
app.include_router(rpa.router, prefix="/api/v1/rpa", tags=["rpa"])
app.include_router(rpa_control.router, prefix="/api/v1", tags=["rpa_control"])
app.include_router(rpa_compat_router, prefix="/api/v1", tags=["rpa_compatibility"])
app.include_router(wechat_ops.router, prefix="/api/v1", tags=["wechat_ops"])
app.include_router(sop.router, prefix="/api/v1", tags=["sop_management"])
app.include_router(layout_control.router, prefix="/api/v1", tags=["layout"])
app.include_router(atspi_analysis.router, prefix="/api/v1", tags=["atspi_analysis"])
app.include_router(atspi_analysis.router, prefix="/api", tags=["atspi_analysis_compat"])
app.include_router(llm_core.router, prefix="/api/v1", tags=["llm_core"])
app.include_router(crm_profile.router, prefix="/api/v1", tags=["crm_profile"])
app.include_router(wechat_api_framework.router, prefix="/api/v1", tags=["wechat_api_framework"])
app.include_router(rpa_definition.router, prefix="/api/v1", tags=["rpa_definition"])


# 条件性包含UI分析和消息操作路由
if UI_ANALYSIS_ENABLED:
    app.include_router(ui_analysis.router, prefix="/api/v1", tags=["ui_analysis"])
    app.include_router(message_ops.router, prefix="/api/v1", tags=["message_ops"])
    print("✅ UI分析和消息操作API已启用")
else:
    print("⚠️ UI分析和消息操作API已被禁用")

@app.get("/")
async def root():
    return {"message": "WeChat Copilot Backend API"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "backend"}