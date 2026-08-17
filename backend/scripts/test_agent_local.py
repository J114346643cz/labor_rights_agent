"""M4 本地验证：工具执行器 + Agent 循环逻辑（不调用真实 LLM）。

用 mock 的 chat_with_tools 模拟"模型请求工具 → 收到结果 → 给出最终回答"，
验证 _run_agent_loop 的循环、参数传递、CalcRecord 留痕是否正确。
"""
import json
import sys
from pathlib import Path

from app.api.chat_api import _run_agent_loop
from app.core.db import init_db, engine
from app.core.tools.registry import execute_tool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session as DBSession


init_db()  # 测试前确保表已创建


class FakeToolCall:
    """模拟 OpenAI 的 tool_call 对象。"""

    def __init__(self, tc_id, name, args):
        self.id = tc_id
        self.function = type("F", (), {"name": name, "arguments": json.dumps(args, ensure_ascii=False)})()


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


def test_execute_tool():
    """工具执行器：正确参数 → 正确结果；错误参数 → error 而非崩溃。"""
    # 加班费（eval_cases calc-001）
    r = execute_tool("calculate_overtime_pay", {"monthly_salary": 10000, "overtime_type": "weekday", "hours": 2})
    assert r["amount"] == 172.41, r

    # 经济补偿封顶（eval_cases calc-009）
    r = execute_tool("calculate_severance", {"monthly_salary": 40000, "years": 11, "months": 0, "scenario": "negotiated", "avg_salary_3x": 36000})
    assert r["amount"] == 396000, r

    # 个税（eval_cases calc-011）
    r = execute_tool("calculate_tax", {"monthly_income": 15000, "insurance": 2000})
    assert r["tax"] == 590, r

    # 年假（eval_cases calc-013）
    r = execute_tool("calculate_annual_leave", {"years_of_service": 5})
    assert r["days"] == 5, r

    # 未知工具
    r = execute_tool("unknown_tool", {})
    assert "error" in r

    # 参数缺失
    r = execute_tool("calculate_tax", {})
    assert "error" in r
    print("EXECUTE_TOOL OK")


def test_agent_loop():
    """Agent 循环：模型请求工具 → 执行 → 回传 → 最终回答；CalcRecord 留痕。"""
    from unittest.mock import patch


    calls = {"n": 0}

    def fake_chat_with_tools(messages, tools, temperature=0.7):
        """模拟：第一轮请求加班费工具，第二轮给出最终回答。"""
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeMessage(
                content=None,
                tool_calls=[FakeToolCall("call-1", "calculate_overtime_pay",
                                         {"monthly_salary": 10000, "overtime_type": "weekday", "hours": 2})],
            )
        return FakeMessage(content="加班费为172.41元（依据劳动法第44条）", tool_calls=None)

    with DBSession(engine) as db:
        with patch("app.api.chat.chat_with_tools", side_effect=fake_chat_with_tools):
            reply, called_tools = _run_agent_loop(
                [{"role": "user", "content": "月薪10000工作日加班2小时"}],
                session_id="test-session",
                db=db,
            )

    assert reply == "加班费为172.41元（依据劳动法第44条）", reply
    assert called_tools == ["calculate_overtime_pay"], called_tools
    print("AGENT_LOOP OK, reply:", reply)
    print("AGENT_LOOP OK, tools:", called_tools)


def test_agent_loop_max_turns():
    """防死循环：模型一直请求工具 → 最大轮数后返回提示。"""
    from unittest.mock import patch


    def endless_tool(messages, tools, temperature=0.7):
        return FakeMessage(
            content=None,
            tool_calls=[FakeToolCall("call-x", "calculate_tax", {"monthly_income": 10000})],
        )

    with DBSession(engine) as db:
        with patch("app.api.chat.chat_with_tools", side_effect=endless_tool):
            reply, called_tools = _run_agent_loop(
                [{"role": "user", "content": "算个税"}],
                session_id="test-session",
                db=db,
            )
    assert "抱歉" in reply, reply
    print("MAX_TURNS OK")


if __name__ == "__main__":
    test_execute_tool()
    test_agent_loop()
    test_agent_loop_max_turns()
    print("ALL M4 LOCAL TESTS PASSED")
