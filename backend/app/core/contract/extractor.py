import json
from typing import Any

from app.core.llm import chat

# 抽取的条款字段（M7.0 规则库覆盖的领域）
EXTRACT_FIELDS = [
    "试用期期限", "试用期工资", "工资构成", "工时制度", "加班规定",
    "竞业限制", "违约金", "服务期", "社会保险", "住房公积金",
    "工资支付方式", "押金保证金", "解除条款", "必备条款完整性",
]

EXTRACT_PROMPT = """你是劳动合同条款抽取器。从用户提供的劳动合同文本中，抽取以下条款字段，输出 JSON。

需要抽取的字段：{fields}

输出格式（严格 JSON，不要输出其他内容）：
{{
  "试用期期限": {{"text": "原文引用，没有则为空字符串", "present": true/false}},
  "试用期工资": {{"text": "原文引用，没有则为空字符串", "present": true/false}},
  ...
}}

规则：
1. text 必须是合同原文的**逐字引用**（截取相关句子），不能改写
2. present=true 表示合同中明确约定了该事项；false 表示未约定
3. 若条款表述含糊不清（约定了但无法确定具体内容），present 仍为 true，text 引用原文
4. 只做条款识别，不判断合法/违法，不输出任何法律意见

合同文本：
---
{contract_text}
---
"""
def _parse_json(raw:str)->dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start: end + 1]
    return json.loads(text)

def extract_clauses(contract_text:str)->dict[str,Any]:
    prompt = EXTRACT_PROMPT.format(
        fields="、".join(EXTRACT_FIELDS),
        contract_text=contract_text[:8000],
    )
    try:
        raw = chat([{"role": "user", "content": prompt}],temperature=0.0)
        result = _parse_json(raw)
    except Exception:
        result = {}

    # 确保所有字段存在（LLM 可能漏字段）
    normalized = {}
    for f in EXTRACT_FIELDS:
        val = result.get(f,{})
        normalized[f] = {
            "text":val.get("text","") if isinstance(val,dict) else "",
            "present":bool(val.get("present",False)) if isinstance(val, dict) else False,
        }

    return normalized






















