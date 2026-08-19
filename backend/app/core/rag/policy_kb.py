import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.contract.parser import extract_text
from app.core.rag.embedding import embed_texts
from app.utils.config import settings

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap

POLICY_COLLECTION = settings.policy_collection

def _split_chunks(text:str,chunk_size:int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """按固定长度+重叠切 chunk（与 user_kb 相同的通用切分）。"""
    import re

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size ,len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def get_policy_collection():
    client = chromadb.PersistentClient(
        path=settings.chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    return client.get_or_create_collection(name=POLICY_COLLECTION)

def ingest_policy(
    filename: str,
    content: bytes,
    city: str,
    policy_type: str,
    effective_date: str,
    source: str,
) -> dict:
    """上传政策文件入库。

    参数：城市 / 政策类型（最低工资|高温津贴|工伤赔偿|其他）/ 生效日期 / 来源
    """
    text = extract_text(filename,content)
    chunks = _split_chunks(text)

    if not chunks:
        raise ValueError("文档内容为空，无法入库")

    vectors = embed_texts(chunks)
    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "doc_name": filename,
            "city": city,
            "policy_type": policy_type,
            "effective_date": effective_date,
            "source": source,
            "source_type": "policy",  # 与法条(无此字段)/规则("rule")区分
            "chunk_index": str(i),
        }
        for i in range(len(chunks))
    ]

    col = get_policy_collection()

    col.add(
        ids=ids, documents=chunks, metadatas=metadatas, embeddings=vectors
    )
    return {
        "doc_id": doc_id,
        "doc_name": filename,
        "city": city,
        "policy_type": policy_type,
        "chunks": len(chunks),
        "ingested": len(chunks),
    }



def list_policies() ->list[dict]:
    col = get_policy_collection()
    all_data = col.get(include=["metadatas"])
    docs:dict[str,dict] = {}
    for meta in all_data.get("metadatas",[]):
        doc_id = meta.get("doc_id","")
        if doc_id and doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "doc_name": meta.get("doc_name", ""),
                "city": meta.get("city", ""),
                "policy_type": meta.get("policy_type", ""),
                "effective_date": meta.get("effective_date", ""),
                "source": meta.get("source", ""),
                "chunks": 0,
            }
        if doc_id:
            docs[doc_id]["chunks"] += 1
    return list(docs.values())

def delete_policy(doc_id:str) ->bool:
    col = get_policy_collection()
    col.delete(where={"doc_id":doc_id})
    return True
























