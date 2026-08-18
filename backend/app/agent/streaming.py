"""流式 ReAct Agent 循环（SSE 版）——为前端打字机效果提供逐字输出。

与 react_loop.py 的区别：
- react_loop.py：每轮 LLM 调用都是非流式（stream=False），拿到完整回答才返回
- 本文件：LLM 调用用流式（stream=True），把"最终回答"的文本增量逐字 yield 给上层，
  由 chat_api 包装成 SSE event: delta 推给前端；工具轮则瞬时执行并 yield tool 事件。

循环结构（与 react_loop 相同的 思考→行动→观察 三步）：
1. THOUGHT（思考）：流式调用 LLM，边收边透传 content 增量；同时按 index 累加 tool_calls
2. ACTION（行动）：若本轮累加出 tool_calls → 逐个执行工具，写 CalcRecord 留痕
3. OBSERVATION（观察）：把工具结果作为 role="tool" 消息回传 → 回到 1
直到某轮没有 tool_calls（即模型给出了最终回答），返回 (回答全文, 工具名列表)。

为什么 content 增量边收边 yield 而 tool_calls 要等流结束再执行：
- OpenAI 协议里工具调用参数是"分片"到达的（arguments 按 index 分成多段），
  必须等整个流结束才能拼出完整参数 → 工具轮无法边收边执行
- 而最终回答的文本增量天然就是顺序的 → 可以边收边透传，实现打字机
"""
import json
from typing import Any, Iterator

from sqlmodel import Session as DBSession

from app.core.llm import stream_chat_with_tools
from app.core.tools.registry import (
    TOOL_SCHEMAS,
    execute_tool,
    tool_result_to_str,
)
from app.schemas.CalcRecord import CalcRecord
from app.utils.config import settings

# 循环最大轮数：防止"模型永远请求工具不回答"的死循环（与 react_loop.MAX_TURNS 同思路）
MAX_TURNS = settings.max_agent_turns


def _accumulate_tool_calls(
    tool_calls_acc: dict[int, dict[str, str]],
    delta_tool_calls: list[Any],
) -> None:
    """把一轮流式 chunk 里的 tool_calls 增量按 index 合并进累加器。

    OpenAI 协议：同一个工具调用的参数（arguments）会分成多个 chunk 依次到达，
    每个 chunk 携带相同的 index，必须逐段拼接才能得到完整 JSON 参数。

    参数：
    - tool_calls_acc: 累加器，形如 {0: {"id": "...", "name": "...", "arguments": "..."}}
    - delta_tool_calls: 当前 chunk 携带的工具调用增量列表
    """
    for tc in delta_tool_calls:
        # 用 index 定位累加槽位（每个工具调用一个槽位）
        acc = tool_calls_acc.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
        # 增量里只带"非空"的字段：id/name 出现一次，arguments 出现多次
        if tc.id:
            acc["id"] = tc.id
        if tc.function:
            # 函数名只出现在第一个增量 chunk 里
            if tc.function.name:
                acc["name"] = tc.function.name
            # 参数是分片的：逐段拼接成完整 JSON 字符串
            if tc.function.arguments:
                acc["arguments"] += tc.function.arguments


def _execute_tool_round(
    messages: list[dict],
    tool_calls_acc: dict[int, dict[str, str]],
    content: str,
    session_id: str,
    db: DBSession,
    called_tools: list[str],
) -> Iterator[dict]:
    """ReAct 第 2+3 步（ACTION + OBSERVATION）：执行工具，观察结果回传。

    生成器：每执行一个工具就 yield 一个 {"type": "tool", "name": ...} 事件，
    让前端能实时展示"正在调用 XX 工具"的徽标。

    参数：
    - messages: 对话状态（原地追加 assistant 工具请求 + tool 观察消息）
    - tool_calls_acc: 本轮 LLM 请求的工具调用（按 index 合并后的完整参数）
    - content: 本轮 assistant 消息的文本（工具轮通常为空串）
    - session_id: 会话 ID（工具结果留痕用）
    - db: 数据库会话（写 CalcRecord 留痕）
    - called_tools: 本次对话累计调用的工具名列表（最终返回给前端）
    """
    # 2a. 把模型的工具请求追加进对话（OpenAI 协议要求，格式与 react_loop 一致）
    messages.append(
        {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls_acc.values()
            ],
        }
    )

    # 2b. 按 index 顺序逐个执行工具
    for idx in sorted(tool_calls_acc.keys()):
        tc = tool_calls_acc[idx]
        name = tc["name"]
        # 记录本次调用的工具名（最终随 done 事件返回前端）
        called_tools.append(name)
        # 通知前端：正在调用该工具（SSE event: tool）
        yield {"type": "tool", "name": name}

        # 解析工具参数（LLM 给的 JSON 字符串；解析失败按空参数处理）
        try:
            args = json.loads(tc["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}

        # 执行工具（如加班费计算），拿到计算结果
        result = execute_tool(name, args)

        # 工具结果留痕（M6 评估用，与 react_loop._execute 一致）
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
            {"role": "tool", "tool_call_id": tc["id"], "content": tool_result_to_str(result)}
        )


def run_streaming_agent(
    messages: list[dict],
    session_id: str,
    db: DBSession,
    max_turns: int = MAX_TURNS,
) -> Iterator[dict]:
    """流式 ReAct 主循环：思考 → 行动 → 观察，直到模型给出最终回答。

    生成器 yield 的事件（由 chat_api 包装成 SSE 事件下发前端）：
    - {"type": "delta", "text": 文本增量}  最终回答逐字输出
    - {"type": "tool",  "name": 工具名}    正在调用某工具

    返回（生成器结束时，迭代返回值）：
    - (最终回答全文, 调用的工具名列表) —— 用 StopIteration.value 获取
    """
    # 本次对话累计调用的工具名（随最终回答一起返回前端）
    called_tools: list[str] = []

    for _ in range(max_turns):
        # ---------- 第 1 步：流式思考（THOUGHT） ----------
        # 逐 chunk 处理：content 增量立即透传，tool_calls 增量按 index 累加
        content_parts: list[str] = []  # 文本增量拼接成全文（最终回答用）
        tool_calls_acc: dict[int, dict[str, str]] = {}  # index → 完整工具调用

        stream = stream_chat_with_tools(messages, tools=TOOL_SCHEMAS)
        for chunk in stream:
            # 某些 chunk 只有 finish_reason 没有 choices，跳过
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # 文本增量：非空则透传给前端（打字机效果），并拼进全文
            if delta and delta.content:
                content_parts.append(delta.content)
                yield {"type": "delta", "text": delta.content}
            # 工具调用增量：按 index 合并（等流结束才能拼出完整参数）
            if delta and delta.tool_calls:
                _accumulate_tool_calls(tool_calls_acc, delta.tool_calls)

        # 模型决定"直接回答"（本轮没有工具调用）→ 循环结束，返回全文
        if not tool_calls_acc:
            return "".join(content_parts), called_tools

        # ---------- 第 2、3 步：行动 + 观察（ACTION + OBSERVATION） ----------
        # 执行工具并 yield tool 事件；把 assistant 工具请求 + tool 观察追加进状态
        yield from _execute_tool_round(
            messages, tool_calls_acc, "".join(content_parts), session_id, db, called_tools
        )

    # 提交 CalcRecord 留痕（与 react_loop 一致：留痕在循环结束后统一提交）
    db.commit()
    # 达到最大轮数仍没回答：把兜底文案作为 delta 事件下发，不让用户等死
    fallback = "抱歉，我没有能完成这次计算，请换个方式描述你的问题。"
    yield {"type": "delta", "text": fallback}
    return fallback, called_tools
