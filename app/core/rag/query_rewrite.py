# ---- 第一层：词典规则（口语 → 法律术语） ----
# 按"口语表达"查"法律关键词"，命中即替换/追加
from app.core.llm import chat

QUERY_DICT: dict[str, str] = {
    "被开了": "劳动合同解除 经济补偿",
    "被裁了": "裁员 经济补偿",
    "被裁员": "裁员 经济补偿",
    "被辞退": "劳动合同解除 经济补偿",
    "被开除": "劳动合同解除 经济补偿",
    "辞退": "劳动合同解除 经济补偿",
    "炒鱿鱼": "劳动合同解除 经济补偿",
    "n+1": "经济补偿 代通知金",
    "n 1": "经济补偿 代通知金",
    "加班费": "加班费 延长工作时间 工资报酬",
    "加班工资": "加班费 延长工作时间 工资报酬",
    "双休加班": "休息日加班 200%",
    "周末加班": "休息日加班 200%",
    "节假日加班": "法定节假日加班 300%",
    "试用期": "试用期 劳动合同法",
    "年假": "年休假",
    "五险一金": "五险一金 社保",
    "个税": "个人所得税",
    "扣税": "个人所得税",
    "社保": "社会保险",
    "工资怎么算": "工资 计算 标准",
    "赔偿": "经济补偿 赔偿金",
    "赔偿金": "经济补偿 赔偿金",
    "离职": "劳动合同解除 离职",
    "辞职": "劳动合同解除 辞职",
    "裁员": "裁员 经济补偿",
    "解雇": "劳动合同解除 经济补偿",
}

_QUERY_KEYS = sorted(QUERY_DICT.keys(),key=len,reverse=True)

def rewrite_by_dict(query):
    """词典改写：命中任意口语词 → 返回改写后的检索词。"""
    hit_terms = []
    for key in _QUERY_KEYS:
        if key.lower() in query.lower():
            hit_terms.append(QUERY_DICT[key])
    if not hit_terms:
        return None
    merged = query +" "+" ".join(dict.fromkeys(hit_terms))
    return merged

# ---- 第二层：LLM 改写 ----
REWRITE_PROMPT = (
    "你是一个法律检索助手。用户会用口语提问劳动权益问题，"
    "请把用户问题改写为一组【法律检索关键词】，用于检索法律法规。\n"
    "要求：\n"
    "1. 只输出关键词，用空格分隔，不要输出任何解释或标点\n"
    "2. 关键词要用法律术语（如：劳动合同解除、经济补偿、加班费、代通知金）\n"
    "3. 保留原问题中的关键数字和主体信息（如月薪、工作年限）\n"
    "4. 如果问题与劳动法无关，直接输出原问题\n\n"
    "用户问题：{query}\n\n"
    "改写结果："
)
def rewrite_by_llm(query):
    """LLM 改写：把口语改写成法律检索关键词。失败时回退原问题。"""
    try:
        prompt = REWRITE_PROMPT.format(query=query)
        result = chat([{"role": "user", "content": prompt}], temperature=0.0)
        result = (result or "").strip().strip('"')
        # 防御：LLM 可能返回整句而非关键词，截断到合理长度
        if not result or len(result) > 200:
            return query
        return result
    except Exception:
        return query  # 任何异常都回退原问题，保证检索不中断



def rewrite_query(query:str,use_llm:bool=True)->str:
    """主入口：先词典，后 LLM；返回改写后的检索词。"""
    # 第一层：词典命中直接返回（快、稳、可解释）
    dict_result = rewrite_by_dict(query)
    if dict_result:
        return dict_result
    # 第二层：LLM 改写（未命中词典时）
    if use_llm:
        return rewrite_by_llm(query)
    return query