# M1实现单次对话P145 -> M2实现多轮对话（10轮）P146 -> M3rag P139 -> M3.5query改写 P37
# M4tools工具调用 P147 -> M5 手写ReAct+LangGraph P148
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.graph import run_langgraph_agent
from app.agent.react_loop import run_react_loop
from app.agent.streaming import run_streaming_agent
from app.core import llm
from app.core.db import get_db
from app.core.rag.query_rewrite import rewrite_query
from app.core.rag.retriever import retrieve, format_context
from app.core.tools.city_policy import list_cities
from app.schemas.Chat import ChatRequest, ChatResponse, Source
from sqlmodel import Session as DBSession
from app.core import memory

from app.utils.config import settings

# 日志记录器（与 main.py 共用同一个名字）
logger = logging.getLogger("labor_agent")

router = APIRouter(prefix="/api/agent",tags=['chat'])

MAX_AGENT_TURNS = settings.max_agent_turns

RAG_SYSTEM_HINT = (
    "\n\n你有权查阅以下法律法规资料。回答劳动权益问题时，"
    "优先依据这些资料作答，并在回答中标注引用的条款号（如「劳动合同法第47条」）。"
    "如果资料中没有相关信息，请如实说明，不要编造法条。"
)

def _make_title(message:str) ->str:
    """会话标题：取第一条消息前 20 字。"""
    title = message.strip().replace("\n"," ")
    return title[:settings.title_max_len] if title else "新对话"

def _detect_city(message: str) -> str | None:
    """从用户消息中识别城市（M8：带 city 检索公共政策库）。

    用已收录城市名列表做包含匹配（"我在杭州上班"→"杭州"）。
    命中返回城市名，未命中返回 None（不检索政策库）。
    """
    for city in list_cities():
        if city in message:
            return city
    return None

def _retrieve_and_build_context(user_message:str)->tuple[str,list[Source],str]:
    # M3.5：query改写 口语 → 法律术语（词典优先，LLM 兜底），提升口语问题命中率
    """query 改写 → 检索相关法条+政策 → 返回 (拼好的上下文段落, 引用来源列表)。

        改写只影响检索词，用户原话仍原样进对话历史与回答。
        M8：从消息识别城市后带 city 检索（政策库按城市过滤），命中政策标注来源。
        """
    search_query = rewrite_query(user_message,use_llm=settings.rag_use_llm_rewrite)
    city = _detect_city(user_message)
    hits = retrieve(search_query,top_k=settings.rag_top_k,city=city)
    context = format_context(hits)
    sources = [
        # law法条名（劳动合同法）  article第几条法条 text法条具体内容
        # content 入库时已含标题（"第X条 标题\n正文"），直接截取即可，避免标题重复
        Source(law=h["law"],article=h["article"],text=h["content"][:200])
        for h in hits
    ]
    return context,sources,search_query




def _run_agent(messages:list[dict], session_id:str, db: DBSession)-> tuple[str,list[str]]:
    if settings.agent_use_langgraph:
        return run_langgraph_agent(messages,session_id,db)
    return run_react_loop(messages,session_id,db)



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
    context , sources ,rewrite_message=_retrieve_and_build_context(req.message)

    # 4. 拼历史（system 带 RAG 上下文）→ Agent 循环（工具调用）
    # 4.1拼接历史会话 根据用户session_id获取当前用户对答的历史会话列表 list[{"role":msg.role,"content":msg.content},...]
    messages : list[dict]= memory.build_messages(db,session.id)
    # 4.2 M3 rag添加知识库内容到系统提示词
    if context:
        #messages[0]["content"] 就是[{"role": "system", "content": 系统提示词}]
        messages[0]["content"] = messages[0]["content"] + RAG_SYSTEM_HINT +"\n\n" + context

    # 4.3 循环工具调用 最多5轮 防止死循环
    # M1 实现单次对话 reply = llm.chat_one(messages)
    # M2 实现多轮对话（10轮) reply = llm.chat(messages)
    # M4tools工具调用 reply , called_tools = _run_agent_loop(messages,session.id,db)
    reply , called_tools = _run_agent(messages,session.id,db)

    # 5. 回答入库并返回（带引用来源 + 工具调用记录）
    memory.add_message(
        db,
        session.id,
        role="assistant",
        content=reply,
        #model_dump()把 Pydantic 模型对象 → 转换成普通 Python 字典 dict
        # s=Source(law="劳动合同法", article=47, text="第47条 经济补偿......")
        # d = {"law":"劳动合同法","article":47,"text":"第47条 经济补偿......"} 普通字典
        sources=json.dumps([s.model_dump() for s in sources],ensure_ascii=False),
        calc_result=json.dumps({"tools": called_tools}, ensure_ascii=False),
    )
    return ChatResponse(session_id=session.id,query=req.message,rewrite_query=rewrite_message,reply=reply, sources=sources,tool_calls=called_tools)


def _sse_event(event: str, data: dict) -> str:
    """把一个 SSE 事件序列化成文本（event + data 两行，空行结尾）。

    参数：
    - event: 事件类型（session / tool / delta / done / error）
    - data: 事件负载（会被 json.dumps 序列化，ensure_ascii=False 保留中文）
    返回：形如 "event: delta\ndata: {"text": "你"}\n\n" 的 SSE 文本块
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_events(
    messages: list[dict],
    session_id: str,
    db: DBSession,
    sources: list[Source],
    rewrite_query: str,
):
    """SSE 事件生成器：跑流式 Agent，把中间产物逐事件推给前端。

    事件顺序：
    1. session 事件：会话 ID + 改写后的检索词（前端据此创建/定位会话）
    2. tool 事件（若有工具调用）：正在调用 XX 工具（前端显示徽标）
    3. delta 事件（最终回答阶段）：回答文本增量（前端实现打字机效果）
    4. done 事件：法条引用 sources + 工具名列表（回答已入库）
    5. error 事件（异常时）：错误提示，避免流断了用户还不知道

    参数：
    - messages: 拼好历史的对话列表（含 system + RAG 上下文）
    - session_id: 会话 ID
    - db: 数据库会话（写用户/助手消息与 CalcRecord 留痕）
    - sources: RAG 检索到的法条引用列表
    - rewrite_query: query 改写结果（session 事件里带给前端）
    """
    # 1. 会话事件（放在最前，前端一拿到就能创建会话、立即切换侧栏）
    yield _sse_event("session", {"session_id": session_id, "rewrite_query": rewrite_query})

    # 流式累积回答全文与工具名（done 事件 + 入库时使用）
    reply_parts: list[str] = []
    called_tools: list[str] = []

    try:
        # 2-3. 跑流式 Agent 主循环，把 delta/tool 事件透传给前端
        for ev in run_streaming_agent(messages, session_id, db):
            if ev["type"] == "delta":
                # 文本增量：累加进全文，同时透传
                reply_parts.append(ev["text"])
                yield _sse_event("delta", {"text": ev["text"]})
            elif ev["type"] == "tool":
                # 工具调用：记录工具名，同时透传
                called_tools.append(ev["name"])
                yield _sse_event("tool", {"name": ev["name"]})

        # 4. 回答入库（sources / calc_result 存 JSON 字符串，与 /chat 一致）
        memory.add_message(
            db,
            session_id,
            role="assistant",
            content="".join(reply_parts),
            sources=json.dumps([s.model_dump() for s in sources], ensure_ascii=False),
            calc_result=json.dumps({"tools": called_tools}, ensure_ascii=False),
        )

        # 5. 结束事件：法条引用 + 工具名列表
        yield _sse_event(
            "done",
            {
                "sources": [s.model_dump() for s in sources],
                "tool_calls": called_tools,
            },
        )
    except Exception:
        # 流式中途出错：记录日志并下发 error 事件，不让前端以为还在生成
        logger.exception("流式聊天异常 session_id=%s", session_id)
        yield _sse_event("error", {"message": "服务内部错误，请稍后重试或换个说法。"})


@router.post("/chat/stream")
def chat_stream_endpoint(req: ChatRequest, db: DBSession = Depends(get_db)) -> StreamingResponse:
    """SSE 流式聊天（前端打字机效果用）。

    与 /chat 的区别：回答不是一次性返回，而是通过 SSE 逐字推送，
    且工具调用（tool 事件）与结束信息（done 事件）也是事件流的一部分。
    前端用 fetch + ReadableStream 消费（EventSource 不支持 POST body）。

    请求体：ChatRequest（session_id 可选，message 必填）——与 /chat 完全一致
    """
    # 1. 确定会话（新建或复用）——与 /chat 相同的逻辑
    if req.session_id is None:
        session = memory.create_session(db, title=_make_title(req.message))
    else:
        session = memory.get_session(db, req.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")
    # 2. 用户消息入库
    memory.add_message(db, session.id, role="user", content=req.message)

    # 3. RAG 检索：把相关法条 context 拼进 system prompt
    context, sources, rewrite_message = _retrieve_and_build_context(req.message)

    # 4. 拼历史（system 带 RAG 上下文）→ 交给事件生成器跑流式 Agent
    messages: list[dict] = memory.build_messages(db, session.id)
    if context:
        messages[0]["content"] = messages[0]["content"] + RAG_SYSTEM_HINT + "\n\n" + context

    # 5. 返回 SSE 流式响应（事件生成器在响应发送时才真正执行）
    return StreamingResponse(
        _stream_events(messages, session.id, db, sources, rewrite_message),
        media_type="text/event-stream",
        headers={
            # 禁止中间代理缓冲：保证增量能实时到达前端
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

