from app.core.rag.embedding import embed_query
from app.core.rag.knowledge_base import get_collection

def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """检索与 query 最相关的 top_k 条法条。

    返回：[{"law": ..., "article": ..., "title": ..., "content": ..., "distance": ...}]
    """
    return _query(query, top_k, where_filter=None)


def retrieve_rules(query: str, top_k: int = 3) -> list[dict]:
    """只检索合规规则库（M7：metadata.source_type == "rule"）。

    合同体检判定时优先用规则库（规则含明确的违规判定逻辑），
    命中不足时再退回法条库（见 checker.py）。
    """
    return _query(query, top_k, where_filter={"source_type": "rule"})

def _query(query: str, top_k: int, where_filter: dict | None)->list[dict]:
    collection = get_collection()
    query_vec = embed_query(query)
    result = collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]

    for doc,meta,dist in zip(docs,metas,dists):
        hits.append(
            {
                "law": meta.get("law", ""),
                "article": meta.get("article", ""),
                "title": meta.get("title", ""),
                "content": doc,
                "distance": round(float(dist), 4),
            }
        )
    return hits

def format_context(hits:list[dict]) -> str:
    if not hits:
        return ""
    lines = ["以下是相关的法律法规条文（回答时请优先引用这些条文，并标注条款号）："]
    for i,hit in enumerate(hits,1):
        lines.append(f"[{i}]《{hit['law']}》{hit['title']}：{hit['content']}")
    return "\n\n".join(lines)