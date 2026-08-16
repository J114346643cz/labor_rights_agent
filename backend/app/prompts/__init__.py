from pathlib import Path

# prompts文件夹路径
PROMPT_DIR = Path(__file__).parent

def load_prompt(filename: str) -> str:
    """读取prompts目录下md提示词文件"""
    file_path = PROMPT_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"提示词文件不存在：{file_path}")
    return file_path.read_text(encoding="utf-8")

# 预加载系统提示词
system_prompt = load_prompt("SystemPrompt.md")