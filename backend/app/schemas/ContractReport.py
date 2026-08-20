import uuid
from datetime import datetime, timezone

from openai import BaseModel
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """UTC 当前时间（无时区信息，SQLite 友好）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ContractReport(SQLModel, table=True):
    """合同体检报告（M7）：按会话关联，前端展示 + 对话上下文复用。"""

    __tablename__ = "contract_reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    file_name: str
    summary: str = "{}"          # JSON：违规统计
    report: str = "{}"           # JSON：完整报告
    created_at: datetime = Field(default_factory=utcnow)


class ReportDocxRequest(BaseModel):
    """Word 报告下载请求:前端把体检报告 JSON 原样发回,后端渲染成 docx。"""
    report: dict


class ReportBindRequest(BaseModel):
    """把已生成的体检报告绑定到指定会话(写摘要消息,供后续聊天追问)。"""
    session_id: str
    report: dict

