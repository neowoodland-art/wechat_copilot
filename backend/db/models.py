from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional, List
from datetime import datetime
import json
from sqlalchemy import Column, Integer

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    wechat_id: str = Field(unique=True)  # 微信内部ID
    nickname: str
    tags: str = Field(default="[]")      # JSON 字符串：["价格敏感", "技术咨询"]
    summary: str = Field(default="")     # LLM 生成的最新总结
    last_contact: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def tag_list(self) -> List[str]:
        return json.loads(self.tags) if self.tags else []
    
    @tag_list.setter
    def tag_list(self, value: List[str]):
        self.tags = json.dumps(value, ensure_ascii=False)

class Message(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str  # 同一会话ID
    confidence: float = Field(default=1.0)  # OCR 可信度

class SopRule(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    trigger_keyword: str
    reply_template: str
    delay_seconds: int = 0
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WechatATSPINode(SQLModel, table=True):
    __tablename__ = "wechat_atspi_nodes"

    id: Optional[int] = Field(default=None, primary_key=True)
    window_title: str = Field(default="")
    window_class: str = Field(default="")
    access_path: str = Field(default="")
    path_numeric_code: str = Field(default="")
    depth: int = Field(default=0)
    depth_code: str = Field(default="00")
    parent_id: Optional[int] = Field(default=None)
    index: int = Field(default=0, sa_column=Column("index", Integer, nullable=False, default=0))
    name: str = Field(default="")
    role: str = Field(default="")
    text: str = Field(default="")
    ocr_text: str = Field(default="")
    ocr_number: int = Field(default=0)
    x: int = Field(default=0)
    y: int = Field(default=0)
    width: int = Field(default=0)
    height: int = Field(default=0)
    client_x: int = Field(default=0)
    client_y: int = Field(default=0)
    screenshot_path: str = Field(default="")
    full_image_path: str = Field(default="")
    page_type: str = Field(default="")
    function_type: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LLMToolRegistry(SQLModel, table=True):
    __tablename__ = "llm_tool_registry"

    id: Optional[int] = Field(default=None, primary_key=True)
    tool_name: str = Field(index=True, unique=True)
    description: str = Field(default="")
    input_schema: str = Field(default="{}")
    output_schema: str = Field(default="{}")
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMSceneConfig(SQLModel, table=True):
    __tablename__ = "llm_scene_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    scene_type: str = Field(index=True, unique=True)
    config_json: str = Field(default="{}")
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMRequestLog(SQLModel, table=True):
    __tablename__ = "llm_request_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True, unique=True)
    scene_type: str = Field(index=True)
    user_id: str = Field(default="")
    model_used: str = Field(default="")
    status_code: int = Field(default=0)
    success: bool = Field(default=True)
    execution_time_ms: int = Field(default=0)
    request_json: str = Field(default="{}")
    response_json: str = Field(default="{}")
    error_message: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WechatChatHistory(SQLModel, table=True):
    __tablename__ = "wechat_chat_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(index=True)
    session_id: str = Field(default="")
    msg_id: str = Field(index=True)
    msg_type: str = Field(default="text")  # text/image/audio/file/system
    sender: str = Field(default="other")  # me/other/system
    content_raw: str = Field(default="")
    content_text: str = Field(default="")
    content_json: str = Field(default="{}")
    file_path: str = Field(default="")
    file_hash: str = Field(default="")
    ocr_status: str = Field(default="none")
    asr_status: str = Field(default="none")
    parse_status: str = Field(default="none")
    send_time: datetime = Field(default_factory=datetime.utcnow, index=True)
    imported_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSummary(SQLModel, table=True):
    __tablename__ = "chat_summary"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(index=True)
    summary_scope: str = Field(default="3day")
    summary_days: int = Field(default=3)
    range_start: datetime = Field(default_factory=datetime.utcnow)
    range_end: datetime = Field(default_factory=datetime.utcnow)
    summary_content: str = Field(default="")
    summary_json: str = Field(default="{}")
    model_used: str = Field(default="")
    model_version: str = Field(default="")
    token_in: int = Field(default=0)
    token_out: int = Field(default=0)
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CustomerPortrait(SQLModel, table=True):
    __tablename__ = "customer_portrait"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(index=True)
    portrait_version: str = Field(default="v1")
    portrait_content: str = Field(default="")
    portrait_json: str = Field(default="{}")
    personality: str = Field(default="")
    preference: str = Field(default="")
    core_needs: str = Field(default="")
    purchase_intention: str = Field(default="")
    budget_level: str = Field(default="")
    taboo: str = Field(default="")
    best_contact_time: str = Field(default="")
    confidence: float = Field(default=0.0)
    source_summary_ids: str = Field(default="")
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CustomerTagSnapshot(SQLModel, table=True):
    __tablename__ = "customer_tag_snapshot"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(index=True)
    tag_name: str = Field(default="", index=True)
    tag_type: str = Field(default="")
    tag_score: float = Field(default=0.0)
    source: str = Field(default="llm")
    source_ref: str = Field(default="")
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CRMScheduleConfig(SQLModel, table=True):
    __tablename__ = "crm_schedule_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    summary_days: int = Field(default=3)
    auto_portrait_enabled: bool = Field(default=True)
    auto_tag_enabled: bool = Field(default=True)
    run_daily_import: bool = Field(default=True)
    run_summary_hour: int = Field(default=1)
    run_portrait_hour: int = Field(default=2)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
