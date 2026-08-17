from typing import Optional, List

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id:Optional[str] = None
    message :str

class Source(BaseModel):
    law: str = ""  # 法律名称，如"劳动合同法"
    article: str = ""  # 条款号，如"47"
    text: str = ""  # 条文原文

class ChatResponse(BaseModel):
    session_id:Optional[str] = None
    query:str
    rewrite_query:str
    reply:str
    sources:List[Source]=[]
    tool_calls:List[str]=[]
