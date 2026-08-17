"""加班费计算器（依据《劳动法》第 44 条）。

时薪 = 月薪 ÷ 21.75 ÷ 8（月计薪天数 21.75，劳社部发〔2008〕3号）
- 工作日延时：时薪 × 1.5 × 小时
- 休息日：时薪 × 2.0 × 小时（可调休）
- 法定节假日：时薪 × 3.0 × 小时

工具只做计算，不做判断（判断用哪个倍率由 Agent 检索法条后决定）。
"""
from typing import Union

from app.utils.config import settings

# 加班类型 → 倍率（对应劳动法第44条第1/2/3项）
MULTIPLIERS = {
    "weekday": 1.5,   # 工作日延时
    "weekend": 2.0,   # 休息日
    "holiday": 3.0,   # 法定节假日
}

MONTH_DAYS = settings.month_days  # 月计薪天数
HOURS_PER_DAY = settings.hours_per_day

def calculate_overtime_pay(
        monthly_salary:Union[int,float],
        overtime_type:str,
        hours:Union[int,float],
)->dict:
    """计算加班费。

    参数：
        monthly_salary: 月薪（应为基本工资，不含绩效补贴）
        overtime_type: weekday / weekend / holiday
        hours: 加班小时数
    返回：
        {hourly_rate, multiplier, amount, basis} 或 {error}
    """
    if monthly_salary is None or hours is None:
        return {"error": "参数缺失：monthly_salary 和 hours 必填"}
    if monthly_salary <= 0:
        return {"error": "月薪必须大于 0"}
    if hours <= 0:
        return {"error": "加班小时数必须大于 0"}
    if overtime_type not in MULTIPLIERS:
        return {"error": f"overtime_type 必须是 {list(MULTIPLIERS.keys())} 之一"}

    # 全程用完整精度计算，只在最终结果舍入（避免中间舍入误差）
    hourly_rate_full = monthly_salary / MONTH_DAYS / HOURS_PER_DAY #时薪
    multiplier = MULTIPLIERS[overtime_type]
    # 计算最终的加班费总额，并保留两位小数
    amount = round(hourly_rate_full * multiplier * hours, 2)
    hourly_rate = round(hourly_rate_full, 2)

    type_name = {
        "weekday": "工作日延时",
        "weekend": "休息日",
        "holiday": "法定节假日",
    }[overtime_type]

    return {
        "hourly_rate": hourly_rate,
        "multiplier": multiplier,
        "hours": hours,
        "amount": amount,
        "detail": f"时薪 {hourly_rate} × {multiplier}倍 × {hours}小时 = {amount} 元",
        "basis": "劳动法第44条",
        "note": f"{type_name}加班，加班费为 {amount} 元",
    }








