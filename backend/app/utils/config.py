

from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # deepseek大模型配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # SQLite 数据库文件路径（M2）
    database_path: str = str(BASE_DIR / "data" / "labor_rights_test.db")
    database_url: str = ""

    # 历史会话（每个id一个标题）标题最大字数限制
    title_max_len:int = 20

    # 截断策略：最多保留最近 10 轮（1 轮 = 1 条 user + 1 条 assistant）
    max_history_turns:int = 10

    # Chroma 向量库持久化目录
    chroma_dir: str = str(BASE_DIR / "data" / "chroma")
    # 法条原始文档目录（M0 数据）
    laws_dir: Path = BASE_DIR / "data" / "laws"
    # Chroma 向量库的集合名
    collection_name:str = "law_kb"
    # embedding 模型名（fastembed 的 BGE 中文模型，维度 512）
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    # embedding 模型缓存目录（固定在工作区内，避免写 C 盘系统目录）
    embedding_cache_dir: str = str(BASE_DIR / "data" / "embedding_cache")

    # 默认检索条数
    rag_top_k: int = 5

    # M3.5：query 改写是否启用 LLM 兜底层（词典层始终启用；False 时只走词典）
    rag_use_llm_rewrite: bool = True

    # Agent 循环最大轮数（防死循环：模型一直请求工具不回答）
    max_agent_turns:int = 5

    # -----------计算加班费------------------
    # 国家法定的月平均计薪天数。
    month_days : float = 21.75
    # 国家法定的标准工作日小时数
    hours_per_day :int = 8

    # 告诉BaseSettings去哪里读环境变量、用什么编码读取文件
    model_config = {
        "env_file" : ".env", #指定要加载的环境变量文件，就是项目根目录下的 .env 文件
        "env_file_encoding" : "utf-8" #指定读取 .env 文件时使用 utf‑8 编码。
    }

    # 历史会话记录保存的数据库地址
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if not self.database_url:
            self.database_url = f"sqlite:///{self.database_path}"


settings = Settings()

if __name__ == '__main__':
    print(BASE_DIR) #D:\AIStudyCode\labor_rights_agent\backend
    for md_file in settings.laws_dir.glob("*.md"):
        print(md_file) #D:\AIStudyCode\labor_rights_agent\backend\data\laws\个税税率表.md
