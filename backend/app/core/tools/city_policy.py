import csv

from anyio.functools import lru_cache

from app.utils.config import settings

POLICY_CSV = settings.policies_dir / "city_policies.csv"

@lru_cache(maxsize=1) # 函数装饰器，开启 LRU 缓存，最多保存 1 个返回结果
def load_policies() -> list[dict]:
    """加载全部城市政策（缓存，CSV 更新后需重启或清缓存）。"""
    if not POLICY_CSV.exists():
        return []
    with open(POLICY_CSV,encoding="utf-8",newline="") as f:
        # 读取 csv 文件，把第一行作为字典 key（表头），每一行返回一个字典{"law_name":"劳动合同法","article":"19","content":"试用期相关规定"}
        return list(csv.DictReader(f))


def query_city_policy(city: str) -> dict:
    """查询指定城市的政策（function calling 工具）。

    参数：
        city: 城市名（如"北京""广州"）
    返回：
        {city, min_wage, avg_salary_3x, data_as_of, source, found} 或 {error}
    """
    city = (city or "").strip().replace("市", "").replace("省", "")
    if not city:
        return {"error": "城市名不能为空"}

    for row in load_policies():
        if row["city"] == city:
            avg_salary = float(row["avg_salary_month"])
            return {
                "city": row["city"],
                "province": row["province"],
                "min_wage": int(row["min_wage"]),
                "avg_salary_3x": round(avg_salary * 3, 2),  # 经济补偿封顶线 = 社平 × 3
                "data_as_of": row["data_as_of"],
                "source": row["source"],
                "found": True,
            }

    return {"error": f"暂未收录 {city} 的政策数据，请确认城市名或上传当地政策文件"}

def list_cities() -> list[str]:
    """已收录城市列表（工具描述/前端展示用）。"""
    return [row["city"] for row in load_policies()]