"""合同体检主流程（M7.5）：上传合同 → 报告。

串联：解析(parser) → 抽取(extractor) → 合规比对(checker) → 处置建议(remedy)
→ 体检报告 JSON。

报告结构：
{
  "report_id": "...",
  "file_name": "...",
  "summary": {"total": N, "violations": n, "warnings": n, "ok": n, "not_specified": n},
  "findings": [{field, text, verdict, basis, reason, risk}],
  "remedies": {remedies: [...], complex_advice: "..."},
  "disclaimer": "本报告仅供参考，不构成法律意见……"
}
"""
from typing import Any

from app.core.contract.check import check_all
from app.core.contract.extractor import extract_clauses
from app.core.contract.remedy import generate_remedies

DISCLAIMER = (
    "本体检报告由 AI 自动生成，仅供参考，不构成法律意见。"
    "涉及具体权益纠纷，请咨询专业律师或当地法律援助机构。"
    "如需法律文书，请由专业律师起草。"
)

def run_contract_check(contract_text: str, file_name: str = "合同") -> dict[str, Any]:
    """完整体检流程，返回报告 JSON。"""
    # 1. 条款抽取
    clauses = extract_clauses(contract_text)

    # 2. 合规比对 + 风险分级
    findings = check_all(clauses, contract_context=contract_text)

    # 3. 处置建议（维权路径 + 证据清单）
    remedies = generate_remedies(findings)

    # 4. 汇总
    summary = {
        "total": len(findings),
        "violations": sum(1 for f in findings if f["verdict"] == "违法"),
        "warnings": sum(1 for f in findings if f["verdict"] == "模糊"),
        "ok": sum(1 for f in findings if f["verdict"] == "合法"),
        "not_specified": sum(1 for f in findings if f["verdict"] == "未约定"),
    }

    return {
        "report_id": file_name,
        "file_name": file_name,
        "summary": summary,
        "findings": findings,
        "remedies": remedies,
        "disclaimer": DISCLAIMER,
    }