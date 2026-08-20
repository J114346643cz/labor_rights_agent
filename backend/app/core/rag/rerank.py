from app.utils import hf_env # noqa: F401
from app.utils.config import settings

# 模型 ID：优先用本地缓存；别人首次运行会按 HF_HOME 自动下载
RERANK_MODEL = settings.rerank_model

_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANK_MODEL,max_length=512)
    return _reranker

def rerank_hits(query:str,hits:list[dict],top_k:int = 5)->list[dict]:
    if not hits:
        return []
    try:
        model = _get_reranker()
        pairs = [[query,h["content"][:500]] for h in hits]
        scores = model.predict(pairs)
        import numpy as np

        scores = np.asarray(scores,dtype=float).flatten().tolist()
        if len(scores) == 1 and len(hits) >1:
            scores = scores * len(hits)
        ranked = sorted(zip(hits,scores),key=lambda x:-float(x[1]))
        result = []
        for h,s in ranked[:top_k]:
            h = dict(h)
            h["rerank_score"] = round(float(s), 4)
            result.append(h)
        return result
    except Exception as e:
        # 依赖未装 / 模型加载失败 → 回退原序，不中断检索
        print(f"[rerank] 不可用，回退原序: {e}")
        return hits[:top_k]
