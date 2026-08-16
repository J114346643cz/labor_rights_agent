import json

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlmodel import Session as DBSession
from sqlmodel import select

from app.core.db import get_db
from app.core.memory import create_session, get_session, get_history_messages
from app.schemas.Chat import Source
from app.schemas.Message import MessageOut
from app.schemas.Session import SessionOut, SessionCreate, Session

router = APIRouter(prefix="/api/agent",tags=["sessions"])

@router.post("/sessions",response_model=SessionOut)
def create_session_endpoint(
        req:SessionCreate | None = None,
        db: DBSession = Depends(get_db)
)-> SessionOut:
    """新建一个会话，标题可选，不选为新对话"""
    title = req.title if req and req.title else "新对话"
    session = create_session(db,title=title)
    return SessionOut(id=session.id,title=session.title,created_at=session.created_at)

@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: DBSession = Depends(get_db)) -> list[SessionOut]:
    """获取所有会话列表（侧栏用），按创建时间倒序。"""
    stmt = select(Session).order_by(Session.created_at.desc())
    sessions = db.exec(stmt).all()
    return [
        SessionOut(id=s.id, title=s.title, created_at=s.created_at)
        for s in sessions
    ]

@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: str, db: DBSession = Depends(get_db)) -> list[MessageOut]:
    """某会话的全部历史消息（刷新页面恢复对话用）。"""
    if get_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    result = []
    for msg in get_history_messages(db, session_id, limit_turns=100000):
        result.append(
            MessageOut(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                sources=[Source(**s) for s in json.loads(msg.sources or "[]")],
                calc_result=json.loads(msg.calc_result or "{}"),
                created_at=msg.created_at,
            )
        )
    return result

