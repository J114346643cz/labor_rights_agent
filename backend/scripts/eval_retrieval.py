"""M9.3 检索质量评估：Recall@1 / Recall@5 / MRR 对比实验。

对比三版检索策略：
1. 基线：纯向量检索（retrieve）
2. 混合：向量 + BM25 → RRF 融合（hybrid_retrieve）
3. 混合+rerank：再经 bge-reranker 精排

标注集：eval_cases.json 的法条题（question → expected_sources 里的期望条文）。

用法（在 backend/ 目录下，需先入库）：
    uv run python scripts/eval_retrieval.py
    uv run python scripts/eval_retrieval.py --rerank   # 启用 rerank（需装 FlagEmbedding）
    uv run python scripts/eval_retrieval.py --top-k 5

输出：控制台对比表 + data/retrieval_eval_report.md（简历素材）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.rag.hybrid import BM25Index, hybrid_retrieve, load_corpus
from app.core.rag.retriever import retrieve

EVAL_CASES = Path(__file__).resolve().parent.parent / "data" / "eval_cases.json"
REPORT = Path(__file__).resolve().parent.parent / "data" / "retrieval_eval_report.md"


def parse_expected_sources(expected_list: list[str]) -> list[tuple[str, str]]:
    """解析期望条文（如"劳动合同法第47条"）→ [(法律关键词, 条款号)]。"""
    result = []
    for exp in expected_list:
        m = re.search(r"(.+?)第(\d+)条", exp)
        if m:
            result.append((m.group(1).strip(), m.group(2)))
        else:
            result.append((exp, ""))  # 文号等非条文格式
    return result


def hit_at(hits: list[dict], expected: list[tuple[str, str]], k: int) -> bool:
    """检查 top-k 内是否命中任意期望条文。"""
    for law_kw, article in expected:
        for h in hits[:k]:
            if article and str(h.get("article")) == article and law_kw in h.get("law", ""):
                return True
            if not article and (law_kw in h.get("law", "") or law_kw in h.get("title", "")):
                return True
    return False


def reciprocal_rank(hits: list[dict], expected: list[tuple[str, str]]) -> float:
    """第一个命中期望条文的 1/rank；未命中返回 0。"""
    for rank, h in enumerate(hits, 1):
        for law_kw, article in expected:
            if article and str(h.get("article")) == article and law_kw in h.get("law", ""):
                return 1.0 / rank
            if not article and (law_kw in h.get("law", "") or law_kw in h.get("title", "")):
                return 1.0 / rank
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="检索质量对比实验")
    parser.add_argument("--rerank", action="store_true", help="启用 rerank 精排")
    parser.add_argument("--top-k", type=int, default=5, help="评估 top-k（默认5）")
    args = parser.parse_args()
    top_k = args.top_k

    # 标注集：法条题
    data = json.loads(EVAL_CASES.read_text(encoding="utf-8"))
    law_cases = [c for c in data["cases"] if c["category"] == "法条"]
    print(f"标注集：{len(law_cases)} 条法条题（top-{top_k} 评估）\n")

    # 候选池（混合检索用）
    corpus = load_corpus()
    bm25 = BM25Index(corpus)
    print(f"候选池：{len(corpus)} 条文\n")

    # 三版策略结果
    strategies = {
        "基线(纯向量)": [],
        "混合(BM25+向量+RRF)": [],
        "混合+rerank": [],
    }

    for case in law_cases:
        q = case["question"]
        expected = parse_expected_sources(case.get("expected_sources", []))

        # 1. 基线
        hits_base = retrieve(q, top_k=top_k)
        strategies["基线(纯向量)"].append((hits_base, expected))

        # 2. 混合
        hits_mix = hybrid_retrieve(q, corpus, top_k=top_k, bm25=bm25, rerank=False)
        strategies["混合(BM25+向量+RRF)"].append((hits_mix, expected))

        # 3. 混合+rerank
        if args.rerank:
            hits_rr = hybrid_retrieve(q, corpus, top_k=top_k, bm25=bm25, rerank=True)
            strategies["混合+rerank"].append((hits_rr, expected))

    # 计算指标
    print(f"{'策略':<24}{'Recall@1':<10}{'Recall@{k}':<12}{'MRR':<10}")
    print("-" * 60)
    report_lines = ["# 检索质量对比实验报告", "",
                    f"- 标注集：{len(law_cases)} 条法条题",
                    f"- 评估：Recall@1 / Recall@{top_k} / MRR",
                    "", "| 策略 | Recall@1 | " + f"Recall@{top_k} | MRR |", "|---|---|---|---|"]

    for name, results in strategies.items():
        if not results:
            continue
        r1 = sum(1 for h, e in results if hit_at(h, e, 1)) / len(results)
        rk = sum(1 for h, e in results if hit_at(h, e, top_k)) / len(results)
        mrr = sum(reciprocal_rank(h, e) for h, e in results) / len(results)
        print(f"{name:<24}{r1:<10.2%}{rk:<12.2%}{mrr:<10.3f}")
        report_lines.append(f"| {name} | {r1:.1%} | {rk:.1%} | {mrr:.3f} |")

    report_lines.append("")
    REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n报告已写入: {REPORT}")


if __name__ == "__main__":
    main()
