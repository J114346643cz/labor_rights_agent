import json
from typing import Any

from app.core.llm import chat

REMEDY_PROMPT = """你是劳动维权指引助手。基于以下【风险条款】给出维权指引。

风险条款：
{findings_text}

要求输出 JSON（严格）：
{{
  "remedies": [
    {{
      "issue": "问题简述",
      "path": "维权路径：第一步做什么 → 第二步做什么（如：先与公司协商 → 向劳动监察部门投诉 → 申请劳动仲裁），含各阶段大致时限",
      "evidence": ["证据1", "证据2", "证据3"],
      "note": "特别提醒"
    }}
  ],
  "complex_advice": "若案情复杂（多争议点/事实不清/金额大），建议前往当地劳动仲裁委员会线下咨询或寻求法律援助，本指引仅供参考"
}}

安全边界（必须遵守）：
1. 【禁止】生成起诉状、仲裁申请书等完整法律文书——用户可能直接提交，后果严重
2. path 只给"步骤指引"，不代写文书内容；复杂案情明确建议线下咨询律师/法律援助
3. 证据清单列举应准备的证明材料类型（劳动合同、工资流水、考勤记录等），不虚构
4. 输出末尾隐含"仅供参考，不构成法律意见"
"""

def _parse_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "remedies": [],
            "complex_advice": "维权建议生成失败，请咨询专业律师或当地法律援助。",
        }

def generate_remedies(findings:list[dict[str,Any]])->dict[str,Any]:
    """生成维权路径 + 证据清单（只针对 🔴/🟡 风险项）。"""
    risky = [
        f for f in findings
        if f.get("verdict") in ("违法", "模糊") and f.get("present")
    ]
    if not risky:
        return {"remedies": [], "complex_advice": "未发现明显违规条款。"}

    findings_text = "\n".join(
        f"- {f['field']}：{f.get('text', '')[:100]}（判定：{f.get('verdict')}，依据：{f.get('basis', '')}）"
        for f in risky
    )
    prompt = REMEDY_PROMPT.format(findings_text=findings_text)
    raw = chat([{"role": "user", "content": prompt}], temperature=0.3)
    return _parse_json(raw)
