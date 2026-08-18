import logging

from fastapi import FastAPI,Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.chat_api import router as chat_router
from app.api.sessions_api import router as sessions_router
from app.core.db import init_db

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("labor_agent")
app = FastAPI(
    title="work-rights-agent",
    description="打工人权益助手",
)

# CORS 跨域处理
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def unhandled_exception_handler(request:Request,exc:Exception)->JSONResponse:
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务内部错误，请稍后重试或换个说法。"},
    )

app.include_router(chat_router)
app.include_router(sessions_router)

@app.on_event("startup")
def on_startup()->None:
    init_db()
    logger.info("打工人权益助手启动完成")
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
