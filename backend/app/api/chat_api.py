from fastapi import APIRouter ,Depends

from app.core import llm
from app.schemas.Chat import ChatRequest , ChatResponse
from sqlmodel import Session as DBSession

router = APIRouter(prefix="/api/agent",tags=['agent'])

@router.post("/chat",response_model=ChatResponse)
def chat(req:ChatRequest)->ChatResponse:
    result = llm.chat_one(req.message)
    return ChatResponse(reply=result)

