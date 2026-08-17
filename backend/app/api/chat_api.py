import json

from fastapi import APIRouter, Depends, HTTPException

from app.core import llm
from app.core.db import get_db
from app.core.llm import chat_with_tools
from app.core.rag.query_rewrite import rewrite_query
from app.core.rag.retriever import retrieve, format_context
from app.core.tools.registry import TOOL_SCHEMAS, get_tool_name_from_call, execute_tool, tool_result_to_str
from app.schemas.CalcRecord import CalcRecord
from app.schemas.Chat import ChatRequest, ChatResponse, Source
from sqlmodel import Session as DBSession
from app.core import memory

from app.utils.config import settings

router = APIRouter(prefix="/api/agent",tags=['agent'])

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


def _retrieve_and_build_context(user_message:str)->tuple[str,list[Source],str]:
    # M3.5：口语 → 法律术语（词典优先，LLM 兜底），提升口语问题命中率
    search_query = rewrite_query(user_message,use_llm=settings.rag_use_llm_rewrite)

    hits = retrieve(search_query,top_k=settings.rag_top_k)
    context = format_context(hits)
    sources = [
        # law法条名（劳动合同法）  article第几条法条 text法条具体内容
        # content 入库时已含标题（"第X条 标题\n正文"），直接截取即可，避免标题重复
        Source(law=h["law"],article=h["article"],text=h["content"][:200])
        for h in hits
    ]
    return context,sources,search_query


def _run_agent_loop(messages:list[dict], session_id:str, db: DBSession)-> tuple[str,list[str]]:
    """Agent 工具调用循环：模型请求工具 → 执行 → 回传 → 直到最终回答。

    返回 (最终回答文本, 调用的工具名列表)。
    工具执行结果同时写入 CalcRecord 表（留痕，M6 评估用）。
    实现了一个标准的 ReAct 风格（Reasoning + Acting）Agent 循环。
    它的核心逻辑是：“模型思考 → 决定调工具 → 后端执行 → 结果喂回模型 → 再思考，直到模型觉得够了”。
    """
    called_tools:list[str] =[]
    for _ in range(MAX_AGENT_TURNS):
        message = chat_with_tools(messages,tools=TOOL_SCHEMAS)
        # 从 message 对象里取出 tool_calls 这个属性，如果这个对象压根没有这个属性，不要报错崩溃，而是返回 None
        tool_calls = getattr(message,"tool_calls",None)
        if not tool_calls:
            # 模型不再请求工具 → 这就是最终回答
            return message.content or "", called_tools

        # 把模型的工具请求追加进对话（OpenAI 要求）
        messages.append(
            {
                "role":"assistant",
                "content":message.content or "",
                "tool_calls":[
                    {
                        "id":tc.id,
                        "type":"function",
                        "function":{
                            "name":get_tool_name_from_call(tc),
                            "arguments":tc.function.arguments,
                        }
                    }
                    for tc in tool_calls
                ]
            }
        )
        # 逐个执行工具，结果回传
        for tc in tool_calls:
            name = get_tool_name_from_call(tc) # 获取工具名称
            called_tools.append(name)
            try:
                args = json.loads(tc.function.arguments or "{}")  # 解析成 dict
            except json.JSONDecodeError:
                args = {}
            result = execute_tool(name,args) # 这里的 args 才是真正传给函数的实参

            # 工具结果留痕（M6 评估可回溯）
            db.add(
                CalcRecord(
                    session_id=session_id,
                    tool=name,
                    params=json.dumps(args, ensure_ascii=False),
                    result=json.dumps(result, ensure_ascii=False),
                )
            )
            messages.append(
                {
                    "role":"tool",
                    "tool_call_id":tc.id,
                    "content":tool_result_to_str(result)
                }
            )
    db.commit()
    return "抱歉，我没有能完成这次计算，请换个方式描述你的问题。", called_tools







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
    # 4.2 rag添加知识库内容到系统提示词
    if context:
        #messages[0]["content"] 就是[{"role": "system", "content": 系统提示词}]
        messages[0]["content"] = messages[0]["content"] + RAG_SYSTEM_HINT +"\n\n" + context
    # reply = llm.chat(messages)
    # 4.3 循环工具调用 最多5轮 防止死循环
    reply , called_tools = _run_agent_loop(messages,session.id,db)

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
    )
    return ChatResponse(session_id=session.id,query=req.message,rewrite_query=rewrite_message,reply=reply, sources=sources,tool_calls=called_tools)

