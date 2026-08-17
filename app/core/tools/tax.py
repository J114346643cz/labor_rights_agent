"""个人所得税计算器（综合所得，单月简化版）。

应纳税所得额 = 月收入 − 5000（起征点）− 五险一金 − 专项附加扣除
应纳税额 = 应纳税所得额 × 税率 − 速算扣除数

注意：正式个税为"累计预扣法"，本工具为单月简化版（技术方案 M4 说明）。
"""
from typing import Optional, Union

# (应纳税所得额上限, 税率, 速算扣除数) —— 上限为 None 表示无上限
BRACKETS = [
    (3000, 0.03, 0),
    (12000, 0.10, 210),
    (25000, 0.20, 1410),
    (35000, 0.25, 2660),
    (55000, 0.30, 4410),
    (80000, 0.35, 7160),
    (None, 0.45, 15160),
]

STANDARD_DEDUCTION = 5000  # 每月起征点


def calculate_tax(
    monthly_income: Union[int, float],
    insurance: Optional[Union[int, float]] = 0,
    special_deduction: Optional[Union[int, float]] = 0,
) -> dict:
    """计算单月个税。

    参数：
        monthly_income: 月收入
        insurance: 五险一金个人缴纳部分（默认0）
        special_deduction: 专项附加扣除（默认0，如房贷/子女教育）
    返回：
        {taxable_income, rate, quick_deduction, tax, detail} 或 {error}
    """
    if monthly_income is None:
        return {"error": "参数缺失：monthly_income 必填"}
    if monthly_income <= 0:
        return {"error": "月收入必须大于 0"}

    taxable = monthly_income - STANDARD_DEDUCTION - (insurance or 0) - (special_deduction or 0)
    if taxable <= 0:
        return {
            "taxable_income": 0,
            "rate": 0,
            "quick_deduction": 0,
            "tax": 0.0,
            "detail": f"应纳税所得额 {taxable} ≤ 0，无需缴纳个税",
            "basis": "个人所得税法（综合所得，单月简化版）",
        }

    rate, quick = 0.0, 0
    for limit, r, q in BRACKETS:
        if limit is None or taxable <= limit:
            rate, quick = r, q
            break

    tax = round(taxable * rate - quick, 2)
    return {
        "taxable_income": round(taxable, 2),
        "rate": rate,
        "quick_deduction": quick,
        "tax": tax,
        "detail": f"应纳税所得额 {round(taxable,2)} × {rate:.0%} − {quick} = {tax} 元",
        "basis": "个人所得税法（综合所得，单月简化版）",
    }
