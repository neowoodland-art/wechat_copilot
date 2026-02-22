from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "sqlite:///../data/wechat.db"
    
    # LLM 配置
    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    llm_model: str = "qwen-max"
    
    # 微信配置
    wechat_version: str = "3.0.0"
    
    class Config:
        env_file = ".env"

settings = Settings()