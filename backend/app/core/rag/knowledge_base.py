import re
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.rag.embedding import embed_texts
from app.utils.config import settings

COLLECTION_NAME = settings.collection_name
LAW_DIR = settings.laws_dir

# 匹配 "## 第十九条 试用期期限" 中的条号
ARTICLE_RE = re.compile(r"第([一二三四五六七八九十百零]+)条")

CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "百": 100, "零": 0,
}


# get_client()相当于打开数据库软件，拿到数据库连接。每次操作集合之前，先拿到这个连接对象。
def get_client():
    """获取持久化客户端。"""
    return chromadb.PersistentClient(
        path=settings.chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False),  # 关闭 chroma 的匿名数据上报，不把你的使用数据上传给官方，项目上线最佳实践，避免隐私泄露。
    )


def reset_collection()->None:
    """删除并重建集合（force 入库时用；比 delete(where={}) 更干净、兼容新版 chromadb）。"""
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    client.get_or_create_collection(name=COLLECTION_NAME)

def get_collection():
    return get_client().get_or_create_collection(name=COLLECTION_NAME)


def cn_to_int(s: str) -> int:
    """中文数字转阿拉伯数字（支持 1-99，够用）。"""
    if "十" not in s:
        return sum(CN_NUM.get(c, 0) for c in s)
    parts = s.split("十")
    tens = CN_NUM.get(parts[0], 1) if parts[0] else 1
    ones = CN_NUM.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
    return tens * 10 + ones

def parse_law_file(path:Path)->list[dict]:
    """解析单个法条 md 文件 → 条文列表。

    格式约定：`## 第X条 标题` 开头的段落为一条条文。
    """
    text = path.read_text(encoding="utf-8")
    # 法律名取文件第一行 "# xxx" 去掉井号
    law = "未命名法律"
    for line in text.splitlines():  # 按换行符切成一行一行的列表，不丢弃换行内容
        if line.startswith("# "):
            law = line.lstrip("# ").strip()  # lstrip("# ")把开头的# 符号删掉；.strip()去掉前后空格
            break

    articles = []
    current_title = None
    current_body = []

    def flush():
        # flush是内部函数，想要修改外层函数的current_title、current_body变量，必须写nonlocal，否则只能读不能改。
        nonlocal current_title, current_body
        if current_title and current_body:
            content = f"{current_title}\n" + "\n".join(current_body).strip()
            m = ARTICLE_RE.search(current_title)
            article_num = cn_to_int(m.group(1)) if m else 0
            articles.append(
                {
                    "law": law,
                    "article": article_num,
                    "title": current_title,
                    "content": content,
                }
            )
        current_title, current_body = None, []

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_title = line.lstrip("## ").strip()
            current_body = []
        elif current_title is not None and line.strip():
            current_body.append(line.strip())

    flush()
    return articles



#把 data/laws/ 下所有法条文件入库。force=True 时清空重建。
def ingest(force : bool=False) ->dict :
    if force:
        reset_collection()
    collection = get_collection()

    all_articles = []
    # glob路径匹配方法，用来遍历文件夹，找出符合匹配规则的文件
    for md_file in sorted(LAW_DIR.glob("*.md")):
        #md_file 是完整路径D:\AIStudyCode\labor_rights_agent\backend\data\laws\个税税率表.md
        all_articles.extend(parse_law_file(md_file))

    if not all_articles:
        return {"ingested": 0, "error": "data/laws/ 下没有可入库的法条文件"}

    # 文本内容已经获取到了而且切分好了
    # 向量化（首次会下载模型）
    contents = [a["content"] for a in all_articles]
    vectors = embed_texts(contents)

    ids = []
    documents = []
    metadatas = []
    for a,vec in zip(all_articles,vectors):
        doc_id = f"{a['law']}-{a['article']}"
        ids.append(doc_id)
        documents.append(a['content'])
        metadatas.append({"law": a["law"], "article": str(a["article"]), "title": a["title"]})

    # 存入向量数据库
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=vectors)
    return {"ingested": len(all_articles), "laws": sorted({a["law"] for a in all_articles})}


def ingest_rules() -> dict:
    """合同合规规则库入库（M7）：与法条同 collection，metadata 标记 source_type=rule。

    规则文件格式与法条一致（## 第X条 标题），复用 parse_law_file。
    """
    collection = get_collection()
    rules_dir = settings.contract_rules_dir

    all_rules = []
    for md_file in sorted(rules_dir.glob("*.md")):
        all_rules.extend(parse_law_file(md_file))

    if not all_rules:
        return {"ingested": 0, "error": f"{rules_dir} 下没有规则文件"}

    contents = [r["content"] for r in all_rules]
    vectors = embed_texts(contents)

    ids = []
    documents = []
    metadatas = []
    for r, vec in zip(all_rules, vectors):
        doc_id = f"rule-{r['law']}-{r['article']}"
        ids.append(doc_id)
        documents.append(r["content"])
        metadatas.append(
            {
                "law": r["law"],
                "article": str(r["article"]),
                "title": r["title"],
                "source_type": "rule",  # 与法条区分（法条无此字段）
            }
        )

    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=vectors)
    return {"ingested": len(all_rules), "rules": sorted({r["law"] for r in all_rules})}

if __name__ == '__main__':
    import json
    res = ingest(force=True)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    # {
    #     "ingested": 18,
    #     "laws": [
    #         "个人所得税税率表（综合所得，按月换算）",
    #         "中华人民共和国劳动合同法（核心条款节选）",
    #         "中华人民共和国劳动法（核心条款节选）",
    #         "关于职工全年月平均工作时间和工资折算问题的通知",
    #         "职工带薪年休假条例"
    #     ]
    # }