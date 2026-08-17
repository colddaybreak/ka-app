# ai-engine/app/main.py
from fastapi import FastAPI
from app.api.routes import chat, documents

app = FastAPI(title="Knowledge Base AI Engine", version="0.1.0")

app.include_router(chat.router, prefix="/ai")
app.include_router(documents.router, prefix="/ai")


@app.get("/ai/health")
async def health_check():
    return {"status": "ok", "service": "ai-engine"}
