import json

from io import BytesIO
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select

from app.core.contract.parser import extract_text
from app.core.contract.service import run_contract_check, DISCLAIMER, _build_report_docx
from app.core.db import get_db
from app.core.memory import get_session, add_message
from app.schemas.ContractReport import ContractReport, ReportBindRequest, ReportDocxRequest
from app.utils.config import settings

MAX_FILE_SIZE = settings.max_file_size

router = APIRouter(prefix="/api/agent",tags=["contract"])


def _maybe_save_report(db:DBSession, session_id:Optional[str], report:dict):
    """带 session_id 时：报告入库 + 写 assistant 摘要消息。"""
    if not session_id:
        return
    if get_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 1. 报告入库（前端展示用）
    db.add(
        ContractReport(
            session_id=session_id,
            file_name=report["file_name"],
            summary=json.dumps(report["summary"], ensure_ascii=False),
            report=json.dumps(report, ensure_ascii=False),
        )
    )

    # 2. 写 assistant 摘要消息（对话上下文：Agent 后续追问能记得体检结论）
    summary = report.get("summary", {})
    risky = [
        f for f in report.get("findings", [])
        if f.get("verdict") in ("违法", "模糊") and f.get("present", True)
    ]
    risky_desc = "；".join(f"{f.get('field')}（{f.get('verdict')}）" for f in risky) or "无"
    msg = (
        f"已对《{report['file_name']}》完成体检：共检查 {summary['total']} 项条款，"
        f"发现 {summary['violations']} 项违法、{summary['warnings']} 项需注意。"
        f"风险条款：{risky_desc}。\n{DISCLAIMER}"
    )
    add_message(db, session_id, role="assistant", content=msg)
    db.commit()

@router.post("/contract/check")
def check_contract(
        file:UploadFile = File(...),
        session_id : Optional[str] = None,
        db : DBSession = Depends(get_db)
)->dict:
    if file.filename is None or not file.filename.strip():
        raise HTTPException(status_code=400, detail="文件名不能为空")

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件超过 {MAX_FILE_SIZE/1024/1024:.0f}MB")

    try:
        # 解析用户上传的合同文件 获取文件内容str
        text = extract_text(file.filename, content)
    except ValueError as e :
        raise HTTPException(status_code=400, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 主线 完成 合同体检（后端）——上传劳动合同 → 风险分级报告
    report = run_contract_check(text,file_name=file.filename)
    # 带 session_id 时：报告入库 + 写 assistant 摘要消息。
    _maybe_save_report(db,session_id,report)
    return report


@router.get("/contract/reports/{session_id}")
def get_session_reports(session_id:str,db:DBSession=Depends(get_db))->list[dict]:
    stmt = (
        select(ContractReport)
        .where(ContractReport.session_id==session_id)
        .order_by(ContractReport.created_at.desc())
    )
    reports = db.exec(stmt).all()
    return [json.loads(r.report) for r in reports]


@router.post("/contract/report-bind")
def bind_report_to_session(req: ReportBindRequest, db: DBSession = Depends(get_db)) -> dict:
    """把已生成的体检报告绑定到指定会话(报告入库 + 写 assistant 摘要消息)。

    用于"去聊天继续提问":体检时可能没有会话,报告生成后才新建体检专用会话,
    前端把报告 JSON 发来,复用 _maybe_save_report 的入库逻辑。
    """
    if get_session(db, req.session_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    _maybe_save_report(db, req.session_id, req.report)
    return {"ok": True, "session_id": req.session_id}


@router.post("/contract/report-docx")
def download_report_docx(req: ReportDocxRequest) -> StreamingResponse:
    """把体检报告渲染成 Word 文档返回(前端用 Blob 下载)。"""
    content = _build_report_docx(req.report)
    # RFC 5987 编码文件名,避免中文在 Content-Disposition 里乱码
    file_name = f"{req.report.get('file_name', '合同体检报告')}.docx"
    encoded = file_name.encode("utf-8").decode("latin-1")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename*=UTF-8\'\'{encoded}'},
    )


class ContractTextRequest(BaseModel):
    text: str
    session_id: Optional[str] = None

@router.post("/contract/check-text",description="这个接口这是用于在fastapi用于合同体检的")
def check_contract_text(
    req: ContractTextRequest,
    db: DBSession = Depends(get_db),
) -> dict:
    """直接提交合同文本体检。"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="合同文本不能为空")
    report = run_contract_check(req.text, file_name="text-input")
    _maybe_save_report(db, req.session_id, report)
    return report





























