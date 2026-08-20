import math
import re
from collections import Counter
from typing import Optional


from app.core.rag.knowledge_base import get_collection



def load_corpus() ->list[dict]:
    col = get_collection()
    all_data = col.get(include=["documents","metadatas"])
    docs = []
    for doc ,meta in zip(all_data.get("documents",[]),all_data.get("metadatas",[])):
        docs.append(
            {
                "law": meta.get("law", ""),
                "article": meta.get("article", ""),
                "title": meta.get("title", ""),
                "content": doc,
                "source_type": meta.get("source_type", "law"),
            }
        )
    return docs

class BM25Index:
    """轻量 BM25（纯 Python 可讲原理）。

    公式：score(q,d) = Σ idf(t) * f(t,d)*(k1+1) / (f(t,d) + k1*(1-b+b*|d|/avgdl))
    """
    def __init__(self,docs:list[dict],k1:float=1.5,b:float=0.75):
        self.docs = docs
        self.k1=k1 #控制词频 tf 的饱和程度。k1 越大，词频越高分数提升越明显；经典取值 1.2~2.0
        self.b = b #控制文档长度惩罚。b=1 完全使用长度惩罚；b=0 完全关闭长度惩罚；标准取值 0.75
        self._tokenize_docs()

    def _tokenize(self,text:str) ->list[str]:
        """中文切词：单字 + 双字组合（法条术语多为双字词）。"""
        # 取出文本里面每一个单独汉字，返回列表 "你好世界" → ['你','好','世','界']
        han = re.findall(r"[\u4e00-\u9fa5]", text or "")
        # 连续的英文 / 数字，按连续片段提取，不是按单个字符 "RAG123测试Agent" → ["rag123", "agent"]
        alnum = [c.lower() for c in re.findall(r"[a-zA-Z0-9]+", text or "")]
        # 相邻两个汉字拼接 输入：['你','好','世','界'] 输出：["你好","好世","世界"]
        bigrams = ["".join(han[i: i + 2]) for i in range(len(han) - 1)]
        # ['检', '索', '测', '试'] + ['rag'] + ["检索", "索测", "测试"]
        return han + alnum + bigrams

    def _tokenize_docs(self):
        """构建索引，预计算全部文档统计量，只在建库时跑一次"""
        self.doc_tokens = [self._tokenize(d["content"]) for d in self.docs]
        self.doc_lens = [len(t) for t in self.doc_tokens]
        self.avgdl = sum(self.doc_lens) / max(len(self.docs),1) #全部文档的平均 token 长度
        # 词频，某词在单篇文档内部出现多少次
        #df = document‑frequency，文档频率：一个 token 出现在多少篇文档里
        self.df:Counter = Counter()
        for tokens in self.doc_tokens:
            self.df.update(set(tokens)) #把每篇文档的不重复 token 更新进 Counter
        self.N = len(self.docs) #总文档数量 N

    def _idf(self,term:str) ->float:
        """计算逆文档频率，衡量词的重要程度 BM25 idf(t)公式"""
        # 拿该词的文档频率，没见过就是 0
        df = self.df.get(term,0)
        if df == 0:
            return 0.0
        return max(0.1 , math.log((self.N-df+0.5) / (df+0.5) + 1))

    def score(self,query:str) -> list[float]:
        """输入查询语句，返回每一篇文档对应的 BM25 分数列表，分数越高越相关。"""
        q_tokens = set(self._tokenize(query))
        if not q_tokens:
            return [0.0] * self.N
        scores = []
        for i in range(self.N):
            tf = Counter(self.doc_tokens[i])
            s = 0.0
            for t in q_tokens:
                if t in tf:
                    idf = self._idf(t)
                    f = tf[t]
                    denom = f + self.k1 * (1 - self.b + self.b * self.doc_lens[i] / max(self.avgdl, 1))
                    s += idf * (f * (self.k1 + 1)) /denom
            scores.append(s)
        return scores


def _rrf(ranked_list:list[list[int]],k:int = 60) ->list[int]:
    scores:dict[int,float]={}
    for ranked in ranked_list:
        for rank,doc_idx in enumerate(ranked):
            scores[doc_idx] = scores.get(doc_idx,0.0) +1.0/(k+rank+1)
    return [idx for idx,_ in sorted(scores.items(),key=lambda x:-x[1])]

def hybrid_retrieve(
        query:str,
        docs:list[dict],
        top_k:int = 5,
        bm25:Optional[BM25Index] = None,
        rerank:bool = False,
)->list[dict]:
    """混合检索：向量路(复用 retrieve) + BM25 路 → RRF 融合 → (可选) rerank。

        docs：候选池（全部法条+规则，从知识库加载）。
        返回：融合排序后的 top_k，含 distance 与 bm25_score。
        """
    if not docs:
        return []
    # 1. 向量路：对候选池全量算余弦相似度（与 retrieve 同源 embedding）
    from app.core.rag.embedding import embed_query,embed_texts
    doc_vecs = embed_texts(d["content"][:500] for d in docs)
    query_vec = embed_query(query)
    sims = []
    for dv in doc_vecs:
        dot = sum(a * b for a,b in zip(query_vec,dv))
        nq = math.sqrt(sum(a * a for a in query_vec)) + 1e-9
        nd = math.sqrt(sum(b * b for b in dv)) + 1e-9
        sims.append(dot / (nq * nd))
    vec_rank = sorted(range(len(docs)), key=lambda i: -sims[i])

    # 2. BM25 路（关键词精确匹配）
    if bm25 is None:
        bm25 = BM25Index(docs)
    bm_scores = bm25.score(query)
    bm_rank = sorted(range(len(docs)),key=lambda i: -bm_scores[i])

    # 3. RRF 融合
    fused_idx = _rrf([vec_rank, bm_rank])

    fused = [dict(docs[i]) for i in fused_idx[:top_k]]
    for i, orig_i in enumerate(fused_idx[:top_k]):
        fused[i]["distance"] = round(float(1 - sims[orig_i]), 4)
        fused[i]["bm25_score"] = round(float(bm_scores[orig_i]), 4)

    # 4. 可选 rerank（cross-encoder 精排）
    if rerank:
        from app.core.rag.rerank import rerank_hits
        fused = rerank_hits(query, fused, top_k=top_k)

    return fused



























































