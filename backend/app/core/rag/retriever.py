from app.core.rag.embedding import embed_query
from app.core.rag.knowledge_base import get_collection
from app.core.rag.policy_kb import get_policy_collection


def retrieve(query: str, top_k: int = 5, city: str | None = None) -> list[dict]:
    """检索与 query 最相关的 top_k 条法条+规则。

    city 不为空时，融合检索公共政策库（按城市过滤），结果合并按距离排序。
    返回：[{"law", "article", "title", "content", "distance", "source_type"}]
    """
    law_hits = _query(query, top_k, where_filter=None)

    if city:
        policy_hits = _query_policy(query, top_k, city=city)
        merged = law_hits + policy_hits
        merged.sort(key=lambda h: h["distance"])
        return merged[:top_k]

    return law_hits

def _query_policy(query: str, top_k: int, city: str) -> list[dict]:
    """从公共政策库检索（按城市过滤）。"""
    query_vec = embed_query(query)
    result = get_policy_collection().query(
        query_embeddings=[query_vec],
        n_results=top_k,
        where={"city": city},
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        hits.append(
            {
                "law": meta.get("doc_name", ""),
                "article": "",
                "title": f"{meta.get('city', '')} {meta.get('policy_type', '')}政策",
                "content": doc,
                "distance": round(float(dist), 4),
                "source_type": "policy",
                "policy_type": meta.get("policy_type", ""),
                "effective_date": meta.get("effective_date", ""),
                "source": meta.get("source", ""),
            }
        )
    return hits

def retrieve_rules(query: str, top_k: int = 3) -> list[dict]:
    """只检索合规规则库（M7：metadata.source_type == "rule"）。

    合同体检判定时优先用规则库（规则含明确的违规判定逻辑），
    命中不足时再退回法条库（见 checker.py）。
    """
    return _query(query, top_k, where_filter={"source_type": "rule"})

def _query(query: str, top_k: int, where_filter: dict | None)->list[dict]:
    """通用检索：支持 where 过滤（法条/规则同集合）。"""
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
                "source_type": meta.get("source_type", "law"),
            }
        )
    return hits

def format_context(hits:list[dict]) -> str:
    """把检索结果拼成 prompt 中的参考资料段落。

        法条/规则：《法律名》条款；政策：[城市政策] 文档名。
        """
    if not hits:
        return ""
    lines = ["以下是相关的参考资料（回答时请优先引用，并标注来源）："]
    for i,hit in enumerate(hits,1):
        if hit.get("source_type") == "policy":
            # 政策来源（安全边界：可追溯）——含来源与生效日期
            title = f"[{hit.get('title', '')}] {hit['law']}"
            meta_parts = []
            if hit.get("effective_date"):
                meta_parts.append(f"生效日期 {hit['effective_date']}")
            if hit.get("source"):
                meta_parts.append(f"来源 {hit['source']}")
            if meta_parts:
                title += "（" + "；".join(meta_parts) + "）"
        else:
            title = f"《{hit['law']}》{hit['title']}"
        lines.append(f"[{i}] {title}：{hit['content']}")
    return "\n\n".join(lines)