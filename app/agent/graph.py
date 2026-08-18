import json
import operator
from typing import Any, TypedDict, Annotated, Literal

from langgraph.graph import StateGraph,START,END
from sqlmodel import Session as DBSession

from app.core.llm import chat_with_tools
from app.core.tools.registry import TOOL_SCHEMAS, get_tool_name_from_call, execute_tool, tool_result_to_str
from app.schemas.CalcRecord import CalcRecord
from app.utils.config import settings

# LangGraph 内置步数上限（对应手写版的 MAX_TURNS）
RECURSION_LIMIT = settings.max_agent_turns_langgraph

class AgentState(TypedDict):
    """图的状态：所有节点共享、可被节点读写。

    关键：messages 和 called_tools 用 Annotated + operator.add 声明【追加 reducer】。
    LangGraph 默认对状态字段是"后写覆盖先写"，若不声明 reducer，
    节点返回的消息会覆盖历史，导致 tool 消息丢失前文（OpenAI 会报 400 错误）。
    声明 reducer 后，节点返回的是"增量"，LangGraph 负责追加合并。
    """
    # 默认行为（大坑）：如果不加这个注解，LangGraph 默认是“覆盖”逻辑。
    # 即 _agent_node 返回 {"messages": [新消息]} 后，
    # 全局的 messages 会被替换成只有这条新消息，历史记录全丢，LLM 会报错
    #加上 operator.add 后LangGraph 执行的是 全局messages = 旧的全局messages + [新消息]
    messages: Annotated[list[dict], operator.add]      # 对话历史 + 工具调用记录
    session_id: str                                     # 用于工具结果留痕
    called_tools: Annotated[list[str], operator.add]    # 本次调用过的工具名


def _agent_node(state:AgentState) ->dict:
    """节点1：思考（LLM 决策）。把当前 messages 发给模型。"""
    # state["messages"]，这里面装着到目前为止的所有对话
    # 整个历史对话发给 DeepSeek，并附带上所有工具（加班费、个税等）的说明书（TOOL_SCHEMAS）
    message = chat_with_tools(state["messages"],tools=TOOL_SCHEMAS)

    # 把模型的回复（可能含 tool_calls）追加进状态
    new_message:dict[str,Any] = {"role":"assistant","content":message.content or ""}
    # chat_with_tools已经把message里的工具挑选好了 由大模型（LLM）完成的。
    tool_calls = getattr(message,"tool_calls",None)
    if tool_calls:
        new_message["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": get_tool_name_from_call(tc),
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    #加上你在 AgentState 中定义的 messages: Annotated[list, operator.add]，
    # LangGraph 会自动把这一条新消息追加（Append） 到全局消息列表的末尾，而不是覆盖历史
    return {"messages": [new_message]}


def _tools_node(state:AgentState,db:DBSession)->dict:
    """节点2：行动 + 观察（执行工具，结果回传）。

    db 通过闭包注入（见 build_graph），不放进状态——
    状态只保存可序列化数据，避免 LangGraph 状态序列化/恢复时出问题。
    """
    messages = state["messages"]
    last = messages[-1]  # 上一条一定是 assistant 带 tool_calls 的消息

    new_messages: list[dict] = []
    called_tools: list[str] = []  # reducer 模式下返回增量，不直接改 state
    for tc in last.get("tool_calls", []):
        name = tc["function"]["name"]
        called_tools.append(name)
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}

        # 根据工具名调用工具 获取计算后结果
        result = execute_tool(name, args)

        # 留痕（M6 评估用）
        db.add(
            CalcRecord(
                session_id=state["session_id"],
                tool=name,
                params=json.dumps(args, ensure_ascii=False),
                result=json.dumps(result, ensure_ascii=False),
            )
        )

        # 观察：工具结果回传给模型
        new_messages.append(
            {"role": "tool", "tool_call_id": tc["id"], "content": tool_result_to_str(result)}
        )

    return {"messages": new_messages, "called_tools": called_tools}

# Literal限定变量的取值范围 这个函数的返回值，必须且只能是 "tools" 或 "END" 这两个字符串中的一个，不能是其他任何值
def _should_continue(state:AgentState) ->Literal["tools","END"]:
    last = state["messages"][-1]
    return "tools" if last.get("tool_calls") else END


def build_graph(db: DBSession) -> Any:
    """构建 LangGraph 状态图。

    db 通过闭包注入 _tools_node（不放进状态，见 _tools_node 注释）。
    """
    #StateGraph 是 LangGraph 提供的一个图构建器类
    graph = StateGraph(AgentState)#实例化这个构建器，并告诉它：“你要管理的状态蓝图是 AgentState 这个格式

    graph.add_node("agent",_agent_node)
    graph.add_node("tools",lambda state:_tools_node(state,db))

    graph.add_edge(START,"agent")
    # _should_continue是agent节点走向下一节点(tools,END)的规则，_should_continue返回的是键值对比如{END:END}
    graph.add_conditional_edges("agent",_should_continue,{"tools":"tools",END:END})
    graph.add_edge("tools","agent") # 工具执行完回到 agent 再思考

    return graph.compile() #编译成可执行的 Python 应用

def run_langgraph_agent(
        messages:list[dict],
        session_id:str,
        db: DBSession
)-> tuple[str,list[str]]:
    """入口：把 messages 放进状态，跑图，返回 (最终回答, 工具名列表)。

    每次请求构建新图实例（简单、无共享状态泄漏；生产可缓存编译图）。
    状态只放可序列化数据（messages / session_id / called_tools）。
    """
    app = build_graph(db)

    state : dict = {
        "messages":messages,
        "session_id":session_id,
        "called_tools":[],
    }
    # invoke意思是“启动列车，运行到终点站（END）或触发熔断，再把车上的所有数据(state)报给我
    # recursion_limit表示agent → tools → agent 之间循环跑满了 8 步还没到终点，LangGraph 会直接抛出 GraphRecursionError 异常，强制截断
    result = app.invoke(state,config={"recursion_limit": RECURSION_LIMIT})
    
    final_messages = result["messages"]
    # 最后一条 assistant 消息即最终回答
    reply = ""
    for m in reversed(final_messages):
        if m.get("role") == "assistant":
            reply = m.get("content") or ""
            break

    db.commit()  # 提交 CalcRecord 留痕
    return reply,result["called_tools"]
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    