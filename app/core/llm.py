# app/services/llm_service.py
from typing import Any

from openai import OpenAI

from app.utils.config import settings
# from app.prompts import system_prompt  # 直接导入读取好的提示词用的是prompts下的__init__.py
from app.utils.prompt_loader import load_system_prompts


_client: OpenAI | None = None

def chat(message: list[dict[str,Any]]) -> str:
    global _client
    if _client is None:
        if not settings.deepseek_api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY 未配置：请复制 .env.example 为 .env 并填入真实 Key"
            )
        _client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=message,
        temperature=0.2  # RAG场景改成0.2，不要0.7，减少幻觉
    )
    return resp.choices[0].message.content

