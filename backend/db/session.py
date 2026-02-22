from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from pathlib import Path

# 数据库文件路径（固定到 backend/data，避免因启动目录不同读写到不同DB）
backend_root = Path(__file__).resolve().parents[1]
db_path = backend_root / "data" / "wechat.db"
db_path.parent.mkdir(parents=True, exist_ok=True)

# 创建数据库引擎
engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})

def create_tables():
    """创建所有表"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session
