from fastapi import FastAPI

from app.api.chat_api import router as chat_router
from app.api.sessions_api import router as sessions_router
from app.core.db import init_db
app = FastAPI(
    title="work-rights-agent",
    description="打工人权益助手",
)

app.include_router(chat_router)
app.include_router(sessions_router)

@app.on_event("startup")
def on_startup()->None:
    init_db()
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
