import json
from typing import Any,Callable

from app.core.tools.annual_leave import calculate_annual_leave
from app.core.tools.city_policy import query_city_policy
from app.core.tools.overtime import calculate_overtime_pay
from app.core.tools.severance import calculate_severance
from app.core.tools.statement import build_statement
from app.core.tools.tax import calculate_tax

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "query_city_policy",
            "description": "查询指定城市的最新政策：最低工资标准、上年度职工月平均工资（3倍为经济补偿封顶线）。用户提到所在城市（如'我在广州'）时应调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京、上海、广州"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_overtime_pay",
            "description": "计算加班费。依据劳动法第44条：工作日延时1.5倍、休息日2倍（可调休）、法定节假日3倍。时薪=月薪÷21.75÷8。",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_salary": {"type": "number", "description": "月薪（基本工资，不含绩效补贴）"},
                    "overtime_type": {"type": "string", "enum": ["weekday", "weekend", "holiday"],
                                      "description": "weekday=工作日延时 / weekend=休息日 / holiday=法定节假日"},
                    "hours": {"type": "number", "description": "加班小时数"},
                },
                "required": ["monthly_salary", "overtime_type", "hours"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_severance",
            "description": "计算经济补偿金（N/N+1/2N）。依据劳动合同法第46/47条（N）、第40条（N+1代通知金）、第87条（违法解除2N）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_salary": {"type": "number", "description": "解除前12个月平均月薪"},
                    "years": {"type": "integer", "description": "工作整年数"},
                    "months": {"type": "integer", "description": "剩余月数（0-11）"},
                    "scenario": {"type": "string", "enum": ["negotiated", "N+1", "illegal"],
                                 "description": "negotiated=协商解除/裁员(N) / N+1 / illegal=违法解除(2N)"},
                    "avg_salary_3x": {"type": "number",
                                      "description": "当地上年度职工月平均工资的3倍（可选，月薪超过它时触发封顶）"},
                },
                "required": ["monthly_salary", "years", "months", "scenario"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_tax",
            "description": "计算单月个人所得税（综合所得简化版）。应纳税所得额=月收入-5000起征点-五险一金-专项附加扣除。",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_income": {"type": "number", "description": "月收入"},
                    "insurance": {"type": "number", "description": "五险一金个人缴纳部分（可选，默认0）"},
                    "special_deduction": {"type": "number", "description": "专项附加扣除（可选，默认0，如房贷/子女教育）"},
                },
                "required": ["monthly_income"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_annual_leave",
            "description": "计算带薪年休假天数。依据职工带薪年休假条例第3条：满1年不满10年5天、满10年不满20年10天、满20年15天。",
            "parameters": {
                "type": "object",
                "properties": {
                    "years_of_service": {"type": "number", "description": "累计工作年限（年）"},
                },
                "required": ["years_of_service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_statement",
            "description": "生成核算单（结合城市政策的确定性计算结果）。kind=severance 经济补偿 / overtime 加班费。需要城市名（用户提到的所在城市）、月薪等参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["severance", "overtime"], "description": "核算类型"},
                    "city": {"type": "string", "description": "城市名（来自用户对话，如 广州）"},
                    "monthly_salary": {"type": "number", "description": "月薪"},
                    "years": {"type": "integer", "description": "工作整年数（severance 用）"},
                    "months": {"type": "integer", "description": "剩余月数 0-11（severance 用）"},
                    "scenario": {"type": "string", "enum": ["negotiated", "N+1", "illegal"],
                                 "description": "解除情形（severance 用）"},
                    "overtime_type": {"type": "string", "enum": ["weekday", "weekend", "holiday"],
                                      "description": "加班类型（overtime 用）"},
                    "hours": {"type": "number", "description": "加班小时数（overtime 用）"},
                },
                "required": ["kind", "city", "monthly_salary"],
            },
        },
    },
]

# 工具名 → 执行函数
_TOOL_FUNCTIONS: dict[str, Callable[..., dict]] = {
    "query_city_policy": query_city_policy,
    "calculate_overtime_pay": calculate_overtime_pay,
    "calculate_severance": calculate_severance,
    "calculate_tax": calculate_tax,
    "calculate_annual_leave": calculate_annual_leave,
    "build_statement": build_statement,
}

def get_tool_name_from_call(tool_call:Any)->str:
    """从 OpenAI tool_call 对象取工具名（兼容不同 SDK 版本字段）。"""
    fn = getattr(tool_call,"function",None)
    return getattr(fn,"name","") if fn else ""

def execute_tool(name:str,arguments:dict)->dict:
    func = _TOOL_FUNCTIONS.get(name)
    if func is None:
        return {"error": f"未知工具: {name}"}
    try:
        return func(**arguments)
    except TypeError as e:
        return {"error": f"工具参数错误: {e}"}
    except Exception as e:  # 防御：任何异常都转为可读错误
        return {"error": f"工具执行异常: {e}"}

def tool_result_to_str(result: dict) -> str:
    """工具结果 → JSON 字符串（作为 tool 消息回传给 LLM）。"""
    return json.dumps(result, ensure_ascii=False)