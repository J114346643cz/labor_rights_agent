import os
from pathlib import Path


def _load_env_file() ->dict:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return {}
    result ={}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key,_,value = line.partition("=")
        result[key.strip()] = value.strip()
    return result

# ---- 立即执行（模块 import 时）----
_env = _load_env_file()

# HF_HOME：模型缓存目录（默认 D:/huggingface_cache，可被 .env / 环境变量覆盖）
hf_home = _env.get("HF_HOME") or "D:/huggingface_cache"
os.environ["HF_HOME"] = hf_home
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# 离线模式：.env 里 HF_HUB_OFFLINE=true 或环境变量已设
offline = _env.get("HF_HUB_OFFLINE", "").lower() in ("1", "true", "yes") or \
    os.environ.get("HF_HUB_OFFLINE", "").lower() in ("1", "true", "yes")
if offline:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    # 关键：离线时删除 HF_ENDPOINT（镜像 URL 与缓存元数据不匹配，
    # 会导致 huggingface_hub 判定"缓存不存在"）。镜像只对在线下载有用。
    os.environ.pop("HF_ENDPOINT", None)
elif _env.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = _env["HF_ENDPOINT"]



