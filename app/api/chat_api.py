import json

from fastapi import APIRouter, Depends, HTTPException

from app.core import llm
from app.core.db import get_db
from app.core.rag.retriever import retrieve, format_context
from app.schemas.Chat import ChatRequest, ChatResponse, Source
from sqlmodel import Session as DBSession
from app.core import memory

from app.utils.config import settings

router = APIRouter(prefix="/api/agent",tags=['agent'])

RAG_SYSTEM_HINT = (
    "\n\n你有权查阅以下法律法规资料。回答劳动权益问题时，"
    "优先依据这些资料作答，并在回答中标注引用的条款号（如「劳动合同法第47条」）。"
    "如果资料中没有相关信息，请如实说明，不要编造法条。"
)

def _make_title(message:str) ->str:
    """会话标题：取第一条消息前 20 字。"""
    title = message.strip().replace("\n"," ")
    return title[:settings.title_max_len] if title else "新对话"


def _retrieve_and_build_context(user_message:str)->tuple[str,list[Source]]:
    hits = retrieve(user_message,top_k=settings.rag_top_k)
    context = format_context(hits)
    sources = [
        # law法条名（劳动合同法）  article第几条法条 text法条具体内容
        # content 入库时已含标题（"第X条 标题\n正文"），直接截取即可，避免标题重复
        Source(law=h["law"],article=h["article"],text=h["content"][:200])
        for h in hits
    ]
    return context,sources

@router.post("/chat",response_model=ChatResponse)
def chat_endpoint(req:ChatRequest,db:DBSession = Depends(get_db))->ChatResponse:
    # 1. 确定会话（新建或复用）
    if req.session_id is None:
        session = memory.create_session(db , title=_make_title(req.message))
    else:
        session = memory.get_session(db,req.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")
    # 2. 用户消息入库 返回Message对象
    memory.add_message(db ,session.id,role="user",content=req.message)

    # 3. RAG 检索：把相关法条context拼进 system prompt
    context , sources=_retrieve_and_build_context(req.message)
    print(context)
    print(sources)
    # 4. 拼历史（system 带 RAG 上下文）→ 调 LLM
    #根据用户session_id获取当前用户对答的历史会话列表 list[{"role":msg.role,"content":msg.content},...]
    messages : list[dict]= memory.build_messages(db,session.id)
    if context:
        #messages[0]["content"] 就是[{"role": "system", "content": 系统提示词}]
        messages[0]["content"] = messages[0]["content"] + RAG_SYSTEM_HINT +"\n\n" + context
    result = llm.chat(messages)

    memory.add_message(
        db,
        session.id,
        role="assistant",
        content=result,
        #model_dump()把 Pydantic 模型对象 → 转换成普通 Python 字典 dict
        # s=Source(law="劳动合同法", article=47, text="第47条 经济补偿......")
        # d = {"law":"劳动合同法","article":47,"text":"第47条 经济补偿......"} 普通字典
        sources=json.dumps([s.model_dump() for s in sources],ensure_ascii=False),
    )
    return ChatResponse(session_id=session.id,reply=result, sources=sources)

