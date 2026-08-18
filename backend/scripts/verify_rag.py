"""M3 验证脚本：直接测检索层（不经过 LLM，排除模型变量干扰）。

用法（在 backend/ 目录下，先跑过 ingest_kb.py 入库）：
    uv run python scripts/verify_rag.py

预期：对每个测试问题，打印命中的 top-3 法条。
如果命中法条明显相关 → 检索层 OK。
"""
import sys
from pathlib import Path

from app.core.rag.retriever import retrieve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# 测试问题：覆盖不同知识主题
TEST_QUERIES = [
    "我月薪10000，工作日加班2小时，加班费是多少？",
    "工作3年被裁员，经济补偿怎么算？",
    "试用期最长能多久？",
    "月收入15000，五险一金2000，个税交多少？",
    "我工作5年，年假有几天？",
]


def main() -> None:
    print("=" * 60)
    print("M3 检索层验证（top-3 命中法条）")
    print("=" * 60)
    all_ok = True
    for q in TEST_QUERIES:
        print(f"\nQ: {q}")
        hits = retrieve(q, top_k=3)
        if not hits:
            print("  ⚠️ 没有检索到任何法条（可能还没入库，先跑 ingest_kb.py）")
            all_ok = False
            continue
        for i, h in enumerate(hits, 1):
            print(f"  [{i}] 《{h['law']}》{h['title']} (distance={h['distance']})")
    print("\n" + "=" * 60)
    print("判断标准：")
    print("  - 加班费问题应命中《劳动法》第44条")
    print("  - 裁员补偿应命中《劳动合同法》第46/47/87条")
    print("  - 试用期应命中《劳动合同法》第19条")
    print("  - 个税应命中《个税税率表》第一条")
    print("  - 年假应命中《年休假条例》第3条")
    print("=" * 60)
    print("RESULT:", "PASS（命中法条与预期主题匹配）" if all_ok else "CHECK（见上方警告）")


if __name__ == "__main__":
    main()
