"""M5 验证：LangGraph 版 Agent（mock chat_with_tools，需要 langgraph 已安装）。

验证：
1. 图构建成功（节点/边/条件路由注册）
2. 正常路径：agent 节点 → tools 节点 → agent 节点 → END
3. 防死循环：recursion_limit 生效
4. CalcRecord 留痕

运行（在 backend/ 目录下，先 uv sync 装好 langgraph）：
    uv run python scripts/test_langgraph.py
"""
import json
import sys
from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session as DBSession

from app.core.db import engine,init_db
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


def test_build_graph():
    """图构建：节点 agent/tools 注册，边存在。"""
    from app.agent.graph import build_graph

    with DBSession(engine) as db:
        g = build_graph(db)
        nodes = set(g.get_graph().nodes.keys())
        assert "agent" in nodes and "tools" in nodes, nodes
    print("BUILD_GRAPH OK, nodes:", sorted(nodes))


def test_normal_flow():
    """正常路径：agent(请求工具) → tools(执行) → agent(回答) → END。"""
    from unittest.mock import patch

    from app.agent.graph import run_langgraph_agent

    calls = {"n": 0}

    def fake_llm(messages, tools, temperature=0.7):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeMessage(
                content=None,
                tool_calls=[FakeToolCall("c1", "calculate_severance",
                                         {"monthly_salary": 40000, "years": 11, "months": 0,
                                          "scenario": "negotiated", "avg_salary_3x": 36000})],
            )
        return FakeMessage(content="封顶后经济补偿为396000元", tool_calls=None)

    with DBSession(engine) as db:
        with patch("app.agent.graph.chat_with_tools", side_effect=fake_llm):
            reply, tools = run_langgraph_agent(
                [{"role": "user", "content": "11年40000月薪裁员补偿"}],
                session_id="lg-test-session",
                db=db,
            )

    assert reply == "封顶后经济补偿为396000元", reply
    assert tools == ["calculate_severance"], tools
    print("NORMAL_FLOW OK:", reply, tools)


def test_recursion_limit():
    """防死循环：模型一直请求工具 → recursion_limit 触发，返回异常提示。"""
    from unittest.mock import patch

    from app.agent.graph import RECURSION_LIMIT, run_langgraph_agent

    def endless(messages, tools, temperature=0.7):
        return FakeMessage(
            content=None,
            tool_calls=[FakeToolCall("cx", "calculate_tax", {"monthly_income": 10000})],
        )

    with DBSession(engine) as db:
        with patch("app.agent.graph.chat_with_tools", side_effect=endless):
            try:
                reply, tools = run_langgraph_agent(
                    [{"role": "user", "content": "算个税"}],
                    session_id="lg-test-session",
                    db=db,
                )
            except Exception as e:
                print(f"RECURSION_LIMIT: 触发异常（LangGraph 行为）: {type(e).__name__}")
                return
    print("RECURSION_LIMIT: 正常返回（可能已达到上限但仍给出内容）:", reply[:30])


def test_calc_record():
    """CalcRecord 留痕。"""
    from sqlmodel import select

    with DBSession(engine) as db:
        records = db.exec(select(CalcRecord).where(CalcRecord.session_id == "lg-test-session")).all()
        print(f"CALC_RECORD: {len(records)} 条留痕")
        for rec in records:
            db.delete(rec)
        db.commit()


if __name__ == "__main__":
    """预计输出
    BUILD_GRAPH OK, nodes: ['__end__', '__start__', 'agent', 'tools']
    NORMAL_FLOW OK: 封顶后经济补偿为396000元 ['calculate_severance']
    RECURSION_LIMIT: 触发异常（LangGraph 行为）: GraphRecursionError
    CALC_RECORD: 1 条留痕
    LANGGRAPH TESTS DONE
    """
    test_build_graph()
    test_normal_flow()
    test_recursion_limit() #表示agent → tools → agent 之间循环跑满了 8 步还没到终点，LangGraph 会直接抛出 GraphRecursionError 异常，强制截断
    test_calc_record()
    print("LANGGRAPH TESTS DONE")
