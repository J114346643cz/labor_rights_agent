from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.rag.policy_kb import ingest_policy, list_policies, delete_policy
from app.core.tools.city_policy import list_cities
from app.utils.config import settings

router = APIRouter(prefix="/api/agent",tags=["policies"])


MAX_FILE_SIZE = settings.max_file_size  # 5MB

POLICY_TYPES = ["最低工资", "高温津贴", "工伤赔偿", "社保基 数", "其他"]

@router.post("/policies")
def upload_policy(
        file:UploadFile = File(...),
        city:str = Form(...), #... 代表必填，等价于 Form(...) = 不能为空
        policy_type: str = Form(...),
        effective_date: str = Form(...),
        source: str = Form(...),
)->dict:
    """上传官方政策文件入库（用户众包维护公共政策库）。"""
    if file.filename is None or not file.filename.strip():
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if not city.strip():
        raise HTTPException(status_code=400, detail="城市不能为空")
    if policy_type not in POLICY_TYPES:
        raise HTTPException(status_code=400, detail=f"政策类型必须是 {POLICY_TYPES} 之一")
    if not effective_date.strip():
        raise HTTPException(status_code=400, detail="生效日期不能为空")

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件超过{MAX_FILE_SIZE/1024/1024} MB 限制")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        result = ingest_policy(
            file.filename,
            content,
            city=city.strip(),
            policy_type=policy_type,
            effective_date=effective_date.strip(),
            source=source.strip() or "用户上传",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 安全边界：标注参考性质
    result["note"] = "由用户上传，仅供参考，请以官方发布为准"
    return result


@router.get("/policies")
def list_policy_docs() -> list[dict]:
    return list_policies()

@router.get("/policies/cities")
def get_cities() -> dict:
    """已收录城市列表(来自 city_policies.csv,核算单下拉/提示用)。

    只有 CSV 里收录的城市才能核算(查得到最低工资/社平工资)。
    """
    cities = list_cities()
    return {"cities": cities, "count": len(cities)}

@router.delete("/policies/{doc_id}")
def remove_policy(doc_id:str)->dict:
    delete_policy(doc_id)
    return {"delete":doc_id}













