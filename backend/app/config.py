from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 告诉BaseSettings去哪里读环境变量、用什么编码读取文件
    model_config = {
        "env_file" : ".env", #指定要加载的环境变量文件，就是项目根目录下的 .env 文件
        "env_file_encoding" : "utf-8" #指定读取 .env 文件时使用 utf‑8 编码。
    }

settings = Settings()