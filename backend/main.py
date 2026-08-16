from fastapi import FastAPI

from app.api.chat_api import router as chat_router
app = FastAPI(
    title="work-rights-agent",
    description="打工人权益助手",
)

app.include_router(chat_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
