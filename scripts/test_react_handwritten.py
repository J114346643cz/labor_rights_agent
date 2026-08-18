"""M5 测试：手写 ReAct 版 Agent 循环（mock LLM，不需要 langgraph）。

验证：
1. 正常路径：模型请求工具 → 执行 → 回传 → 最终回答
2. 防死循环：模型一直请求工具 → max_turns 后返回提示
3. CalcRecord 留痕写入
"""
import json
import sys
from pathlib import Path

from app.agent.react_loop import run_react_loop

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session as DBSession
from app.core.db import init_db,engine
from app.schemas.CalcRecord import CalcRecord

init_db()


class FakeToolCall:
    def __init__(self, tc_id, name, args):
        self.id = tc_id
        self.function = type("F", (), {"name": name, "arguments": json.dumps(args, ensure_ascii=False)})()


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


def test_react_normal():
    """正常路径：第一轮请求加班费工具，第二轮给出最终回答。"""
    from unittest.mock import patch



    calls = {"n": 0}

    def fake_llm(messages, tools, temperature=0.7):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeMessage(
                content=None,
                tool_calls=[FakeToolCall("c1", "calculate_overtime_pay",
                                         {"monthly_salary": 10000, "overtime_type": "weekday", "hours": 2})],
            )
        return FakeMessage(content="加班费为172.41元（劳动法第44条）", tool_calls=None)

    with DBSession(engine) as db:
        with patch("app.agent.react_loop.chat_with_tools", side_effect=fake_llm):
            reply, tools = run_react_loop(
                [{"role": "user", "content": "月薪10000加班2小时"}],
                session_id="m5-test-session",
                db=db,
            )

    assert reply == "加班费为172.41元（劳动法第44条）", reply
    assert tools == ["calculate_overtime_pay"], tools
    print("REACT NORMAL OK:", reply, tools)


def test_react_max_turns():
    """防死循环：一直请求工具 → 最大轮数后返回提示。"""
    from unittest.mock import patch


    def endless(messages, tools, temperature=0.7):
        return FakeMessage(
            content=None,
            tool_calls=[FakeToolCall("cx", "calculate_tax", {"monthly_income": 10000})],
        )

    with DBSession(engine) as db:
        with patch("app.agent.react_loop.chat_with_tools", side_effect=endless):
            reply, tools = run_react_loop(
                [{"role": "user", "content": "算个税"}],
                session_id="m5-test-session",
                db=db,
                max_turns=3,
            )
    assert "抱歉" in reply, reply
    assert len(tools) == 3, tools
    print("REACT MAX_TURNS OK")


def test_calc_record_written():
    """CalcRecord 留痕写入验证。"""
    from sqlmodel import select

    with DBSession(engine) as db:
        records = db.exec(select(CalcRecord).where(CalcRecord.session_id == "m5-test-session")).all()
        assert len(records) > 0, "应有 CalcRecord 记录"
        r = records[0]
        assert r.tool in ("calculate_overtime_pay", "calculate_tax")
        print(f"CALC_RECORD OK: {r.tool} params={r.params[:60]}")
        # 清理测试数据
        for rec in records:
            db.delete(rec)
        db.commit()


if __name__ == "__main__":
    """预计输出
    REACT NORMAL OK: 加班费为172.41元（劳动法第44条） ['calculate_overtime_pay']
    REACT MAX_TURNS OK
    CALC_RECORD OK: calculate_tax params={"monthly_income": 10000}
    ALL M5 (handwritten) TESTS PASSED
    """
    test_react_normal()
    test_react_max_turns()
    test_calc_record_written()
    print("ALL M5 (handwritten) TESTS PASSED")
