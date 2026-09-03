# ai-engine/app/models/llm.py
from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(model: str = None, temperature: float = None) -> ChatOpenAI:
    # enable_thinking 非 OpenAI 标准参数，需经 extra_body 传递（百炼等端点支持）；
    # 未配置时不传，避免 OpenAI 官方 API 因不识别该参数而报错
    extra_body = None
    if settings.enable_thinking is not None:
        extra_body = {"enable_thinking": settings.enable_thinking}

    return ChatOpenAI(
        model=model or settings.llm_model,
        temperature=temperature or settings.llm_temperature,
        max_tokens=settings.max_tokens,
        openai_api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        extra_body=extra_body,
        streaming=True,
        # 流式模式下也上报 token 用量（最后一个 chunk 携带 usage 信息）
        stream_usage=True,
    )
