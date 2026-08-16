# app/services/llm_service.py
from openai import OpenAI

from app.config import settings
# from app.prompts import system_prompt  # 直接导入读取好的提示词用的是prompts下的__init__.py
from utils.prompt_loader import load_system_prompts

def chat_one(use_msg: str) -> str:
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url
    )
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": load_system_prompts()},
            {"role": "user", "content": use_msg},
        ],
        temperature=0.2  # RAG场景改成0.2，不要0.7，减少幻觉
    )
    return resp.choices[0].message.content