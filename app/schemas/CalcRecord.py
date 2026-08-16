from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

def utcnow() -> datetime:
    """UTC 当前时间（无时区信息，SQLite 友好）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class CalcRecord(SQLModel, table=True):
    """工具计算结果留痕（M4 启用，先建表结构）。"""

    __tablename__ = "calc_records"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    tool: str
    params: str = "{}"           # JSON 字符串：入参
    result: str = "{}"           # JSON 字符串：金额与过程
    created_at: datetime = Field(default_factory=utcnow)