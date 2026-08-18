"""手写 ReAct Agent 循环（M5a）——原理教学版，不参与正式服务。

ReAct = Reasoning + Acting（思考 + 行动）。
核心循环（三步）：
1. THOUGHT（思考）: 把对话历史发给 LLM，模型决定"直接回答"还是"需要调用工具"
2. ACTION（行动）: 若模型请求工具 → 执行工具（我们的计算器），拿到结果
3. OBSERVATION（观察）: 把工具结果作为"观察"回传给模型
   → 回到 1，直到模型不再请求工具，输出最终回答

为什么保留这个版本（面试点）：
- LangGraph 版是对本文件的"框架化"：本文件用 for 循环 + 手动 append 管理状态，
  LangGraph 用 StateGraph + 节点 + 边表达同样的逻辑。
- 看懂本文件 = 看懂 Agent 原理；看懂 graph.py = 看懂工程化。

与 M4 的关系：M4 的 _run_agent_loop 就是这个循环的内联版，
M5a 把它提炼成独立模块并明确"思考/行动/观察"三个概念。
"""
import json
from typing import Any

from sqlmodel import Session as DBSession

from app.core.llm import chat_with_tools
from app.core.tools.registry import TOOL_SCHEMAS, get_tool_name_from_call, execute_tool, tool_result_to_str
from app.schemas.CalcRecord import CalcRecord

# 循环最大轮数：防止"模型永远请求工具不回答"的死循环
MAX_TURNS = 5


def _call_llm(messages: list[dict]) -> Any:
    """ReAct 第 1 步（THOUGHT）：把状态发给 LLM，拿到它的决策。

    返回的 message 对象里：
    - 有 tool_calls → 模型决定"行动"（要调工具）
    - 无 tool_calls → 模型决定"直接回答"（content 即最终答案）
    """
    return chat_with_tools(messages, tools=TOOL_SCHEMAS)


def _execute(message: Any, messages: list[dict], session_id: str, db: DBSession, called_tools: list[str]) -> None:
    """ReAct 第 2+3 步（ACTION + OBSERVATION）：
    执行模型请求的工具，把"观察"（工具结果）追加进状态。
    """
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return

    # 2a. 把模型的工具请求追加进对话（OpenAI 协议要求）
    messages.append(
        {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": get_tool_name_from_call(tc),
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        }
    )

    # 2b. 逐个执行工具
    for tc in tool_calls:
        name = get_tool_name_from_call(tc)
        called_tools.append(name)
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}

        result = execute_tool(name, args)

        # 工具结果留痕（M6 评估用）
        db.add(
            CalcRecord(
                session_id=session_id,
                tool=name,
                params=json.dumps(args, ensure_ascii=False),
                result=json.dumps(result, ensure_ascii=False),
            )
        )

        # 3. 观察：把工具结果作为 role="tool" 消息回传（这就是"观察"）
        messages.append(
            {"role": "tool", "tool_call_id": tc.id, "content": tool_result_to_str(result)}
        )


def run_react_loop(
    messages: list[dict],
    session_id: str,
    db: DBSession,
    max_turns: int = MAX_TURNS,
) -> tuple[str, list[str]]:
    """ReAct 主循环：思考 → 行动 → 观察，直到模型给出最终回答。

    返回 (最终回答文本, 调用的工具名列表)。
    """
    called_tools: list[str] = []

    for _ in range(max_turns):
        # 第 1 步：思考（LLM 决策）
        message = _call_llm(messages)

        # 模型决定"直接回答" → 循环结束
        if not getattr(message, "tool_calls", None):
            return message.content or "", called_tools

        # 第 2、3 步：行动 + 观察
        _execute(message, messages, session_id, db, called_tools)

    db.commit()
    # 达到最大轮数仍没回答：返回提示，不让用户等死
    return "抱歉，我没有能完成这次计算，请换个方式描述你的问题。", called_tools
