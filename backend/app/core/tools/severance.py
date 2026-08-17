"""经济补偿计算器（《劳动合同法》第 46/47 条、第 40 条、第 87 条）。

规则：
- N：每满 1 年 1 个月工资；满 6 个月不满 1 年按 1 年；不满 6 个月按 0.5 个月
- N+1：+1 为代通知金（医疗期满/不胜任/客观情况变化，未提前 30 天通知，第 40 条）
- 2N：违法解除赔偿金（第 87 条）
- 封顶：月薪高于当地社平 3 倍时按 3 倍计，年限最高 12 年（第 47 条）

工具只做计算，不做判断（用 N 还是 2N 由 Agent 检索法条后决定）。
"""
from typing import Optional, Union


def calculate_severance(
    monthly_salary: Union[int, float],
    years: int,
    months: int,
    scenario: str,
    avg_salary_3x: Optional[Union[int, float]] = None,
) -> dict:
    """计算经济补偿。

    参数：
        monthly_salary: 解除前 12 个月平均月薪
        years: 工作整年数
        months: 剩余月数（0-11）
        scenario: negotiated(协商解除/N) / N+1 / illegal(违法解除/2N)
        avg_salary_3x: 当地上年度职工月平均工资的 3 倍（触发封顶时传入）
    返回：
        {n_months, base_salary, amount, detail, basis} 或 {error}
    """
    if monthly_salary is None or years is None or months is None:
        return {"error": "参数缺失：monthly_salary、years、months 必填"}
    if monthly_salary <= 0:
        return {"error": "月薪必须大于 0"}
    if years < 0 or not (0 <= months < 12):
        return {"error": "years >= 0 且 0 <= months < 12"}
    if scenario not in ("negotiated", "N+1", "illegal"):
        return {"error": "scenario 必须是 negotiated / N+1 / illegal 之一"}

    # 1. 计算 N（工作年限折算）
    n = years
    if months >= 6:
        n += 1
    elif months > 0:
        n += 0.5

    # 2. 封顶处理（第47条：月薪 > 社平3倍 → 按3倍计 + 年限上限12年）
    base_salary = monthly_salary
    capped = False
    if avg_salary_3x and monthly_salary > avg_salary_3x:
        base_salary = avg_salary_3x
        capped = True
        if n > 12:
            n = 12

    # 3. 场景倍数
    scenario_name = {"negotiated": "协商解除/裁员", "N+1": "N+1（代通知金）", "illegal": "违法解除"}[scenario]
    if scenario == "N+1":
        n += 1
    elif scenario == "illegal":
        n *= 2

    amount = round(n * base_salary, 2)

    basis = "劳动合同法第46条、第47条"
    if scenario == "N+1":
        basis += "、第40条"
    elif scenario == "illegal":
        basis += "、第87条"

    detail_parts = [f"N = {n} 个月工资"]
    if capped:
        detail_parts.append(f"（月薪 {monthly_salary} 超过社平3倍 {avg_salary_3x}，按 {base_salary} 计）")
    detail_parts.append(f"{n} × {base_salary} = {amount} 元")

    return {
        "n_months": n,
        "base_salary": base_salary,
        "amount": amount,
        "detail": "；".join(detail_parts),
        "basis": basis,
        "note": f"{scenario_name}，应得经济补偿为 {amount} 元",
    }
