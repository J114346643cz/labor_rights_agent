from app.utils.path_tool import get_abs_path
import yaml

# 系统提示词
def load_prompts_config(config_path: str=get_abs_path("config/prompts.yml"), encoding: str="utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

prompts_conf = load_prompts_config()