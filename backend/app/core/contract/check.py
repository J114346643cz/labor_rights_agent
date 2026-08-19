import json
from typing import Any

from app.core.llm import chat
from app.core.rag.query_rewrite import rewrite_query
from app.core.rag.retriever import retrieve, retrieve_rules

RISK_LEVELS = {
    "违法": "🔴 严重违规",
    "模糊": "🟡 需注意",
    "合法": "🟢 正常",
    "未约定": "⚪ 未约定",
}

VERDICT_PROMPT = """你是劳动法合规审查助手。基于提供的【判定规则】和【合同条款原文】及【合同全文上下文】，判断该条款是否合规。

判定规则：
{rules}

合同条款：
字段：{field}
原文引用：{text}
{present_hint}
{context_hint}

要求：
1. 只输出 JSON，格式：{{"verdict": "合法|违法|模糊", "basis": "依据的法律条款", "reason": "一句话理由"}}
2. verdict 判定标准：
   - 条款违反强制规定（如低于法定标准、排除法定权利）→ 违法
   - 条款符合法定标准 → 合法
   - 表述不清、无法确定是否合规 → 模糊
3. **必须结合【合同全文上下文】综合判断**：如试用期期限需结合合同期限档位判断（劳动合同法第19条），不要因看不到联动信息而误判模糊
4. basis 必须来自【判定规则】中的法律依据（如"劳动合同法第20条"），不得编造
5. 若判定规则中没有覆盖该字段，输出 {{"verdict": "未约定", "basis": "", "reason": "规则库未覆盖此条款"}}
6. 你只做合规性参考判断，不构成法律意见；复杂争议提示线下咨询

安全边界（必须遵守）：
- 不得生成起诉状、仲裁申请书等法律文书
- 判定结果仅作参考，应提示"建议咨询专业律师"
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
        return {"verdict": "模糊", "basis": "", "reason": "判定解析失败"}



def check_clause(field: str, text: str, present: bool, contract_context: str = "") -> dict[str, Any]:
    """对单个条款做合规判定。

    返回：{field, text, verdict, basis, reason, risk, present}
    """
    if not present or not text.strip():
        return {
            "field": field, "text": text, "verdict": "未约定", "basis": "",
            "reason": "合同中未约定该条款", "risk": "⚪ 未约定", "present": False,
        }

    # RAG 检索判定规则：优先规则库（含明确的违规判定逻辑），不足时退回法条库
    search_query = rewrite_query(f"{field} {text[:100]}", use_llm=False)
    rule_hits = retrieve_rules(search_query, top_k=3)

    if rule_hits:
        hits = rule_hits  # 规则库命中 → 用规则（判定逻辑更精确）
        hit_kind = "合规规则"
    else:
        hits = retrieve(search_query, top_k=3)  # 规则库无命中 → 法条库兜底
        hit_kind = "法律法规"

    rules_text = "\n".join(
        f"[{i}]（{hit_kind}）《{h['law']}》{h['title']}：{h['content'][:300]}" for i, h in enumerate(hits, 1)
    ) or "（规则库无相关条目）"

    prompt = VERDICT_PROMPT.format(
        rules=rules_text,
        field=field,
        text=text[:500],
        present_hint="",
        context_hint=(
            f"\n合同全文上下文（用于联动判断，如试用期与合同期限）：\n{contract_context[:1500]}"
            if contract_context else ""
        ),
    )
    raw = chat([{"role": "user", "content": prompt}], temperature=0.0)
    result = _parse_json(raw)

    verdict = result.get("verdict", "模糊")
    if verdict not in ("合法", "违法", "模糊", "未约定"):
        verdict = "模糊"

    return {
        "field": field,
        "text": text,
        "verdict": verdict,
        "basis": result.get("basis", ""),
        "reason": result.get("reason", ""),
        "risk": RISK_LEVELS.get(verdict, "⚪ 未约定"),
        "present": True,
    }




def check_all(clauses:dict[str,Any],contract_context:str = "")->list[dict[str,Any]]:
    """对抽取的全部条款做合规判定，返回体检项列表。"""
    findings = []
    # clauses
    # {
    # "试用期期限": {{"text": "原文引用，没有则为空字符串", "present": true / false}},
    # ......
    # }
    for field,info in clauses.items():
        # field = "试用期期限"
        # info = {"text": "原文引用，没有则为空字符串", "present": true / false}
        item = check_clause(field,info.get("text",""),info.get("present", False), contract_context)
        findings.append(item)
    return findings

