# ai-engine/app/api/deps.py
from fastapi import Request, HTTPException
from app.config import settings


async def verify_internal_token(request: Request):
    """验证请求来自 Node.js API 网关"""
    token = request.headers.get("X-Internal-Token")
    if token != settings.internal_api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 从请求头提取网关已校验的用户信息
    request.state.user_id = request.headers.get("X-User-Id")
