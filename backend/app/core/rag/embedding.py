from fastembed import TextEmbedding

from app.utils.config import settings

_model :TextEmbedding | None = None

def get_embedding_model() ->TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=settings.embedding_model)
        return _model


def embed_texts(texts :list[str]) ->list[list[float]]:
    """把文本列表转成向量列表。"""
    model = get_embedding_model()
    # fastembed 返回生成器，list() 转成实际向量
    return [list(map(float, vec)) for vec in model.embed(texts)]

def embed_query(query:str)-> list[float]:
    return embed_texts([query])[0]