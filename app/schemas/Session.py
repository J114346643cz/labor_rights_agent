from datetime import datetime, timezone
from typing import Optional

from openai import BaseModel
from sqlmodel import Field, SQLModel

def utcnow() -> datetime:
    """UTC 当前时间（无时区信息，SQLite 友好）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Session(SQLModel,table=True):
    """数据库表sessions信息"""
    __tablename__ = "sessions"
    id: str = Field(primary_key=True)
    title: str = "新对话"
    created_at: datetime = Field(default_factory=utcnow)

class SessionOut(BaseModel):
    """实体类 会话信息（列表/详情返回）。"""
    id: str
    title: str
    created_at: datetime

class SessionCreate(BaseModel):
    """POST /api/agent/sessions 请求体（可选，不传则默认标题）。"""

    title: Optional[str] = None