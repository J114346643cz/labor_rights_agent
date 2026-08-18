import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

def utcnow() -> datetime:
    """UTC 英国伦敦的当前时间（无时区信息，SQLite 友好）。
    存裸 UTC：无论你的服务器在东京、伦敦还是北京，2026-08-17 12:23:06
    这个绝对值永远是唯一的、不会引起歧义的。
    前端展示时，只需要用 JavaScript 的 new Date('2026-08-17T12:23:06Z').toLocaleString('zh-CN')，
    瞬间就能自动变成 2026-08-17 20:23:06 显示给用户看。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

class CalcRecord(SQLModel, table=True):
    """工具计算结果留痕（M4 启用，先建表结构）。"""

    __tablename__ = "calc_records"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    tool: str
    params: str = "{}"           # JSON 字符串：入参
    result: str = "{}"           # JSON 字符串：金额与过程
    created_at: datetime = Field(default_factory=utcnow)