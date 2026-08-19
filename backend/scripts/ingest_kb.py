"""法条+规则库入库脚本（M3/M7）：解析 data/laws/ 与 data/contract_rules/ → 向量化 → 存入 Chroma。

用法（在 backend/ 目录下）：
    uv run python scripts/ingest_kb.py          # 增量入库（法条 + 规则）
    uv run python scripts/ingest_kb.py --force  # 清空重建（法条 + 规则）

首次运行会自动下载 embedding 模型（约 100MB，缓存到 data/embedding_cache/）。
"""
import argparse
import sys
from pathlib import Path



# 保证能 import app 包（脚本在 scripts/ 下运行时，把上级目录加入路径）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.rag.knowledge_base import ingest, ingest_rules


def main() -> None:
    #Python 命令行参数解析库，作用：你在终端运行脚本的时候，可以传参数给程序，不用改代码。
    parser = argparse.ArgumentParser(description="法条+规则入库（Chroma）")
    #不带 --force → force=False，增量入库，不会清空旧向量，只新增文档
    parser.add_argument("--force", action="store_true", help="清空重建")
    # 解析终端输入的命令，把参数结果放到 args 对象。 args.force 获取布尔值。
    # 执行命令带uv run python scripts/ingest_kb.py --force带了--force 则args为true
    args = parser.parse_args()

    print("开始入库（首次运行会下载 embedding 模型，请稍候）...")
    result = ingest(force=args.force)
    print(f"法条入库完成：共 {result.get('ingested', 0)} 条")
    for law in result.get("laws", []):
        print(f"  - {law}")
    rule_result = ingest_rules()
    print(f"规则库入库完成：共 {rule_result.get('ingested', 0)} 条")
    for rule in rule_result.get("rules", []):
        print(f"  - {rule}")


if __name__ == "__main__":
    main()
