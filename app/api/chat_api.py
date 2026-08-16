from fastapi import APIRouter, Depends, HTTPException

from app.core import llm
from app.core.db import get_db
from app.schemas.Chat import ChatRequest , ChatResponse
from sqlmodel import Session as DBSession
from app.core import memory

from app.utils.config import settings

router = APIRouter(prefix="/api/agent",tags=['agent'])

def _make_title(message:str) ->str:
    title = message.strip().replace("\n"," ")
    return title[:settings.title_max_len] if title else "新对话"

@router.post("/chat",response_model=ChatResponse)
def chat_endpoint(req:ChatRequest,db:DBSession = Depends(get_db))->ChatResponse:
    if req.session_id is None:
        session = memory.create_session(db , title=_make_title(req.message))
    else:
        session = memory.get_session(db,req.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")

    memory.add_message(db ,session.id,role="user",content=req.message)

    messages = memory.build_messages(db,session.id)
    result = llm.chat(messages)

    memory.add_message(db,session.id,role="assistant",content=result)
    return ChatResponse(session_id=session.id,reply=result)

