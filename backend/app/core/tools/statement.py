from typing import Any

from app.core.contract.service import DISCLAIMER
from app.core.tools.city_policy import query_city_policy
from app.core.tools.overtime import calculate_overtime_pay
from app.core.tools.severance import calculate_severance

# 核算情形 → 对应计算函数 + 所需参数说明
SCENARIOS = ["severance", "overtime"]


def build_severance_statement(
    city: str,
    monthly_salary: float,
    years: int,
    months: int,
    scenario: str,
) -> dict[str, Any]:
    """经济补偿核算单。"""
    # 1. 查城市政策（社平 3 倍 = 封顶线） 得到就是根据城市找到city_policies.csv定义的{}数据
    policy = query_city_policy(city)
    if policy.get("error"):
        return {"error": policy["error"]}

    # 2. 确定性计算（复用 M4 工具）
    result = calculate_severance(
        monthly_salary=monthly_salary,
        years=years,
        months=months,
        scenario=scenario,
        avg_salary_3x=policy["avg_salary_3x"],
    )
    if result.get("error"):
        return {"error": result["error"]}

    return {
        "type": "经济补偿核算单",
        "city": city,
        "input": {
            "monthly_salary": monthly_salary,
            "years": years,
            "months": months,
            "scenario": scenario,
            "avg_salary_3x": policy["avg_salary_3x"],
        },
        "result": result,
        "policy": {
            "min_wage": policy["min_wage"],
            "data_as_of": policy["data_as_of"],
            "source": policy["source"],
        },
        "disclaimer": DISCLAIMER,
    }


def build_overtime_statement(
    city: str,
    monthly_salary: float,
    overtime_type: str,
    hours: float,
) -> dict[str, Any]:
    """加班费核算单。"""
    policy = query_city_policy(city)
    if policy.get("error"):
        return {"error": policy["error"]}

    result = calculate_overtime_pay(
        monthly_salary=monthly_salary,
        overtime_type=overtime_type,
        hours=hours,
    )
    if result.get("error"):
        return {"error": result["error"]}

    return {
        "type": "加班费核算单",
        "city": city,
        "input": {
            "monthly_salary": monthly_salary,
            "overtime_type": overtime_type,
            "hours": hours,
        },
        "result": result,
        "policy": {
            "min_wage": policy["min_wage"],
            "data_as_of": policy["data_as_of"],
            "source": policy["source"],
        },
        "disclaimer": DISCLAIMER,
    }


def build_statement(kind:str,params:dict) -> dict[str,Any]:
    """核算单统一入口。kind: severance / overtime。"""
    if kind == "severance":
        return build_severance_statement(
            city=params.get("city", ""),
            monthly_salary=params.get("monthly_salary", 0),
            years=params.get("years", 0),
            months=params.get("months", 0),
            scenario=params.get("scenario", "negotiated"),
        )
    if kind == "overtime":
        return build_overtime_statement(
            city=params.get("city", ""),
            monthly_salary=params.get("monthly_salary", 0),
            overtime_type=params.get("overtime_type", "weekday"),
            hours=params.get("hours", 0),
        )
    return {"error": f"不支持的核算类型: {kind}，支持 {SCENARIOS}"}