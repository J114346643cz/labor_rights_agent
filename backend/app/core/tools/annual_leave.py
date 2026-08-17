"""年假计算器（《职工带薪年休假条例》第 3 条）。

累计工作年限 → 年假天数：
- 满 1 年不满 10 年：5 天
- 满 10 年不满 20 年：10 天
- 满 20 年：15 天

注意：享受年假的前提是"连续工作 1 年以上"（第 2 条）。
"""
from typing import Union


def calculate_annual_leave(years_of_service: Union[int, float]) -> dict:
    """计算年假天数。

    参数：
        years_of_service: 累计工作年限（年）
    返回：
        {days, detail, basis} 或 {error}
    """
    if years_of_service is None:
        return {"error": "参数缺失：years_of_service 必填"}
    if years_of_service < 0:
        return {"error": "工作年限不能为负数"}

    if years_of_service < 1:
        return {
            "days": 0,
            "detail": f"累计工作 {years_of_service} 年，不满 1 年，不享受带薪年休假（条例第2条）",
            "basis": "职工带薪年休假条例第2条、第3条",
        }
    if years_of_service < 10:
        days = 5
        rule = "满1年不满10年"
    elif years_of_service < 20:
        days = 10
        rule = "满10年不满20年"
    else:
        days = 15
        rule = "满20年"

    return {
        "days": days,
        "detail": f"累计工作 {years_of_service} 年（{rule}），年休假 {days} 天",
        "basis": "职工带薪年休假条例第3条",
    }
