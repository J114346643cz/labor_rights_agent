from app.core.rag.embedding import embed_query
from app.core.rag.knowledge_base import get_collection


def retrieve(query:str ,top_k :int = 5)->list[dict]:
    collection = get_collection()
    query_vec = embed_query(query)
    result = collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
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