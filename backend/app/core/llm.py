from typing import Any

from openai import OpenAI

from app.utils.config import settings
# from app.prompts import system_prompt  # 直接导入读取好的提示词用的是prompts下的__init__.py
from app.utils.prompt_loader import load_system_prompts


_client: OpenAI | None = None

def get_client() -> OpenAI:
    """懒加载 OpenAI client；未配置 Key 时给出明确提示。"""
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
    return _client

def chat(message: list[dict[str,Any]]) -> str:
    """多轮对话：传入完整 messages 列表（含 system），返回模型回答文本。"""
    resp = get_client().chat.completions.create(
        model=settings.deepseek_model,
        messages=message,
        temperature=0.2  # RAG场景改成0.2，不要0.7，减少幻觉
    )
    return resp.choices[0].message.content

# def chat_once(user_message: str, system_prompt: str = SYSTEM_PROMPT) -> str:
#     """单轮对话：发一条用户消息，返回模型回答文本。"""
#     return chat(
#         [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_message},
#         ]
#     )

def chat_with_tools(
        messages:list[dict[str,Any]],
        tools:list[dict],
):
    resp = get_client().chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        tools=tools,
        temperature=0.2  # RAG场景改成0.2，不要0.7，减少幻觉
    )
    return resp.choices[0].message


