from datetime import datetime, timezone
from typing import List

from openai import BaseModel
from sqlmodel import Field, SQLModel

from app.schemas.Chat import Source


def utcnow() -> datetime:
    """UTC 当前时间（无时区信息，SQLite 友好）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Message(SQLModel, table=True):
    """会话内的一条消息。"""

    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True, foreign_key="sessions.id")
    role: str  # "user" / "assistant"
    content: str
    sources: str = "[]"          # JSON 字符串：引用来源（M3 填充）
    calc_result: str = ""        # JSON 字符串：工具计算结果（M4 填充）
    created_at: datetime = Field(default_factory=utcnow)

class MessageOut(BaseModel):
    """单条消息（历史消息返回）。"""

    id: str
    session_id: str
    role: str
    content: str
    sources: List[Source] = []
    calc_result: dict = {}
    created_at: datetime