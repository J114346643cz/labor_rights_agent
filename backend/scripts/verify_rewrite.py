"""M3.5 验证脚本：对比 query 改写前后的检索命中率（词典层）。

用法（在 backend/ 目录下，需先入库）：
    uv run python scripts/verify_rewrite.py

判定逻辑：对每个测试问题，给出【期望命中的条款集合】（如 {46, 47}），
检查 top-3 命中里是否包含期望条款 → 命中（比 top-1 子串匹配更合理）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.query_rewrite import rewrite_query
from app.rag.retriever import retrieve

# 口语测试问题 → 期望命中的条款号集合（来自 eval_cases 的知识）
TEST_CASES = [
    ("我被开了能拿多少钱", {46, 47, 87}, "经济补偿"),
    ("被裁了有补偿吗", {46, 47}, "经济补偿"),
    ("公司把我辞退了怎么赔", {46, 47, 87}, "经济补偿"),
    ("加班费怎么算", {44}, "加班费"),
    ("周六上班算加班吗", {44}, "加班费"),
    ("试用期工资有规定吗", {19, 20}, "试用期"),
    ("我干了5年有年假吗", {3}, "年休假"),
    ("工资扣个税怎么算", {1}, "个税"),
]


def top3_articles(query: str) -> list[tuple[str, str]]:
    """返回 top-3 命中的 (法律名, 条款号)。"""
    hits = retrieve(query, top_k=3)
    return [(h["law"], h["article"]) for h in hits]


def main() -> None:
    print("=" * 70)
    print("M3.5 query 改写验证（词典层，top-3 命中判定）")
    print("=" * 70)

    hit_before = 0
    hit_after = 0
    total = len(TEST_CASES)

    for q, expect_articles, label in TEST_CASES:
        rewritten = rewrite_query(q, use_llm=False)

        arts_before = {int(a) for _, a in top3_articles(q) if a.isdigit()}
        arts_after = {int(a) for _, a in top3_articles(rewritten) if a.isdigit()}

        ok_before = bool(arts_before & expect_articles)
        ok_after = bool(arts_after & expect_articles)
        hit_before += ok_before
        hit_after += ok_after

        print(f"\nQ: {q}  (期望条款 {sorted(expect_articles)})")
        print(f"  改写: {rewritten}")
        print(f"  改写前 top3 条款: {sorted(arts_before) or ['无']}  {'✓' if ok_before else '✗'}")
        print(f"  改写后 top3 条款: {sorted(arts_after) or ['无']}  {'✓' if ok_after else '✗'}")

    print("\n" + "=" * 70)
    print(f"命中率对比：改写前 {hit_before}/{total} ({hit_before / total:.0%})"
          f"  →  改写后 {hit_after}/{total} ({hit_after / total:.0%})")
    print("=" * 70)


if __name__ == "__main__":
    main()
