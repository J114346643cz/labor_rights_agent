from pydantic.v1 import BaseSettings

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    database_path: str = str(BASE_DIR / "data" / "labor_rights_test.db")
    database_url: str = ""

    # 历史会话标题最大字数限制
    title_max_len = 20

    # 截断策略：最多保留最近 10 轮（1 轮 = 1 条 user + 1 条 assistant）
    max_history_turns = 10

    # 告诉BaseSettings去哪里读环境变量、用什么编码读取文件
    model_config = {
        "env_file" : ".env", #指定要加载的环境变量文件，就是项目根目录下的 .env 文件
        "env_file_encoding" : "utf-8" #指定读取 .env 文件时使用 utf‑8 编码。
    }
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if not self.database_url:
            self.database_url = f"sqlite:///{self.database_path}"


settings = Settings()

if __name__ == '__main__':
    print(BASE_DIR)