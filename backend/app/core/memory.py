import uuid

from sqlmodel import Session as DBSession, select
from app.schemas.Session import Session
from app.schemas.Message import Message
from app.utils.config import settings
from app.utils.prompt_loader import load_system_prompts
def create_session(db:DBSession, title:str="新对话") -> Session:
    session = Session(id=str(uuid.uuid4()),title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_session(db, session_id):
    return db.get(Session,session_id)


def add_message(
    db: DBSession,
    session_id: str,
    role: str,
    content: str,
    sources: str = "[]",
    calc_result: str = "",
) -> Message:
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        sources=sources,
        calc_result=calc_result,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_history_messages(db: DBSession, session_id: str, limit_turns: int = settings.max_history_turns):
    get_all_msg_by_session_id = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit_turns *2 ) #每轮 2 条：user + assistant
    )
    rows = db.exec(get_all_msg_by_session_id).all()
    return list(reversed(rows)) # 恢复时间正序


def build_messages(db: DBSession, session_id: str) -> list[dict]:
    messages = [{"role":"system","content":load_system_prompts()}]
    for msg in get_history_messages(db,session_id):
        messages.append({"role":msg.role,"content":msg.content})
    return messages