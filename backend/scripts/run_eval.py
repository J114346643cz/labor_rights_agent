"""M6 评估脚本：跑 eval_cases.json 测试集，输出评估报告。

三类测试：
1. 计算题（纯本地，不需要 LLM）：从问题解析参数 → 调计算器 → 比对标准金额
2. 法条题（调 chat 接口，需要 LLM + RAG 已入库）：检查回答是否正确、引用是否命中
3. 多轮题（调 chat 接口）：连续对话，检查第二轮是否用到第一轮信息

用法（在 backend/ 目录下，需先入库 + 配置 .env）：
    uv run python scripts/run_eval.py                  # 全部
    uv run python scripts/run_eval.py --category 计算   # 只跑计算题（离线可用）
    uv run python scripts/run_eval.py --only-local      # 只跑本地可跑的计算题

输出：控制台报告 + data/eval_report.md（可写进 README/简历）
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.tools.overtime import calculate_overtime_pay
from app.core.tools.severance import calculate_severance
from app.core.tools.tax import calculate_tax
from app.core.tools.annual_leave import calculate_annual_leave

EVAL_CASES = Path(__file__).resolve().parent.parent / "data" / "eval_cases.json"
REPORT = Path(__file__).resolve().parent.parent / "data" / "eval_report.md"

BASE_URL = "http://127.0.0.1:8000"

# ---- 计算题参数解析（从自然语言提取） ----

def _find_num(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def parse_overtime(q: str) -> dict | None:
    salary = _find_num(q, r"月薪(\d+)")
    hours = _find_num(q, r"加班(\d+)小时")
    if salary is None or hours is None:
        return None
    if "国庆" in q or "法定节假" in q or "节假日" in q:
        otype = "holiday"
    elif "周六" in q or "周日" in q or "休息日" in q or "周末" in q:
        otype = "weekend"
    else:
        otype = "weekday"
    return {"monthly_salary": salary, "overtime_type": otype, "hours": hours}


def parse_severance(q: str) -> dict | None:
    salary = _find_num(q, r"月薪(\d+)")
    years = _find_num(q, r"工作(\d+)年")
    months = _find_num(q, r"年(\d+)个月")
    if salary is None:
        return None
    # 支持"工作刚好6个月"这种没有"年"的表述
    if years is None:
        months = _find_num(q, r"工作(\d+)个月") or _find_num(q, r"(\d+)个月")
        years = 0
    months = int(months) if months else 0
    if "违法" in q:
        scenario = "illegal"
    elif "医疗期满" in q or "未提前" in q or "N+1" in q or "代通知" in q:
        scenario = "N+1"
    else:
        scenario = "negotiated"
    # 封顶：兼容"社平12000"和"职工月平均工资12000"两种表述
    avg = _find_num(q, r"社平(\d+)") or _find_num(q, r"月平均工资(\d+)")
    result = {"monthly_salary": salary, "years": int(years), "months": months, "scenario": scenario}
    if avg:
        result["avg_salary_3x"] = avg * 3  # 问题里给的是社平工资，需乘 3 才是封顶线
    return result


def parse_tax(q: str) -> dict | None:
    income = _find_num(q, r"月收入(\d+)")
    if income is None:
        return None
    insurance = _find_num(q, r"五险一金(\d+)")
    special = _find_num(q, r"专项附加扣除(\d+)") or _find_num(q, r"专项(\d+)")
    result = {"monthly_income": income}
    if insurance:
        result["insurance"] = insurance
    if special:
        result["special_deduction"] = special
    return result


def parse_annual_leave(q: str) -> dict | None:
    years = _find_num(q, r"工作(\d+)年")
    if years is None:
        return None
    return {"years_of_service": years}


TOOL_PARSERS = {
    "overtime": parse_overtime,
    "severance": parse_severance,
    "tax": parse_tax,
    "annual_leave": parse_annual_leave,
}

TOOL_FUNCS = {
    "overtime": calculate_overtime_pay,
    "severance": calculate_severance,
    "tax": calculate_tax,
    "annual_leave": calculate_annual_leave,
}


def eval_calc_case(case: dict) -> tuple[bool, str]:
    """跑单个计算题：解析参数 → 调计算器 → 比对金额。返回 (通过?, 详情)。"""
    tool = case["tool"]
    parser = TOOL_PARSERS.get(tool)
    func = TOOL_FUNCS.get(tool)
    if not parser or not func:
        return False, "未知工具类型"
    params = parser(case["question"])
    if not params:
        return False, "参数解析失败"
    result = func(**params)
    if "error" in result:
        return False, f"计算器报错: {result['error']}"
    got = result.get("amount", result.get("tax", result.get("days")))
    expected = case.get("expected_amount")
    if got is None or expected is None:
        return False, f"金额字段缺失: got={got}, expected={expected}"
    ok = abs(float(got) - float(expected)) < 0.01
    detail = f"解析参数={params} → 结果={got}，期望={expected}"
    return ok, detail


def eval_chat_case(case: dict, client) -> tuple[bool, str]:
    """跑单个法条/多轮题：调 chat 接口，检查引用是否命中。"""
    import urllib.request

    def ask(session_id: str | None, message: str) -> dict:
        body = json.dumps({"session_id": session_id, "message": message}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/agent/chat", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    expected = case.get("expected_sources", [])
    if case["category"] == "多轮":
        conv = case.get("conversation", [])
        if not conv:
            return False, "多轮题缺少 conversation"
        session_id = None
        for msg in conv:
            resp = ask(session_id, msg)
            session_id = resp.get("session_id")
        # 检查最后回答是否涉及第一轮的关键信息（用 expected_amount 校验）
        expected_amt = case.get("expected_amount")
        if expected_amt is not None:
            # 从回答中找金额（粗匹配：数字出现在回答中）
            nums = re.findall(r"[\d,]+\.?\d*", resp.get("reply", ""))
            hit = any(abs(float(n.replace(",", "")) - expected_amt) < 1 for n in nums if n.replace(",", "").replace(".", "").isdigit())
            return hit, f"多轮回答: {resp.get('reply', '')[:80]}... 期望金额 {expected_amt}"
        return True, f"多轮对话完成，回答: {resp.get('reply', '')[:60]}"
    else:  # 法条题
        resp = ask(None, case["question"])
        sources = [s["law"] + "第" + str(s["article"]) for s in resp.get("sources", [])]
        # 引用命中：期望的条文（如"劳动合同法第47条"）是否出现在 sources 或回答中
        reply = resp.get("reply", "")
        hit = any(exp in reply or any(exp in s for s in sources) for exp in expected)
        return hit, f"sources={sources}，期望={expected}"


def main() -> None:
    parser = argparse.ArgumentParser(description="评估测试集")
    parser.add_argument("--category", choices=["计算", "法条", "多轮"], help="只跑指定类别")
    parser.add_argument("--only-local", action="store_true", help="只跑本地可跑的（计算题）")
    args = parser.parse_args()

    data = json.loads(EVAL_CASES.read_text(encoding="utf-8"))
    cases = data["cases"]
    if args.category:
        cases = [c for c in cases if c["category"] == args.category]

    local_cases = [c for c in cases if c["category"] == "计算"]
    remote_cases = [c for c in cases if c["category"] != "计算"]
    if args.only_local:
        remote_cases = []

    results: list[dict] = []

    # 1. 计算题（本地）
    calc_pass = 0
    for c in local_cases:
        ok, detail = eval_calc_case(c)
        calc_pass += ok
        results.append({"id": c["id"], "category": "计算", "ok": ok, "detail": detail})
        print(f"{'✅' if ok else '❌'} {c['id']}: {detail}")

    # 2. 法条/多轮题（调接口）
    remote_pass = 0
    for c in remote_cases:
        try:
            ok, detail = eval_chat_case(c, None)
        except Exception as e:
            ok, detail = False, f"接口调用失败: {e}"
        remote_pass += ok
        results.append({"id": c["id"], "category": c["category"], "ok": ok, "detail": detail})
        print(f"{'✅' if ok else '❌'} {c['id']} ({c['category']}): {detail}")

    # 3. 汇总报告
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    lines = [
        "# 评估报告",
        "",
        f"- 测试时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 测试集总数：{total} 条（计算 {len(local_cases)} / 法条+多轮 {len(remote_cases)}）",
        f"- 通过：{passed}/{total}（{passed / total:.1%}）",
        "",
        "## 分项统计",
        "",
    ]
    for cat in ["计算", "法条", "多轮"]:
        cat_results = [r for r in results if r["category"] == cat]
        if cat_results:
            cat_pass = sum(1 for r in cat_results if r["ok"])
            lines.append(f"- {cat}：{cat_pass}/{len(cat_results)}（{cat_pass / len(cat_results):.1%}）")
    lines.append("")
    lines.append("## 明细")
    lines.append("")
    lines.append("| ID | 类别 | 结果 | 详情 |")
    lines.append("|---|---|---|---|")
    for r in results:
        lines.append(f"| {r['id']} | {r['category']} | {'✅' if r['ok'] else '❌'} | {r['detail']} |")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"评估完成：{passed}/{total} 通过（{passed/total:.1%}）")
    print(f"报告已写入: {REPORT}")


if __name__ == "__main__":
    main()
