# ai-engine/app/models/llm.py
from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(model: str = None, temperature: float = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or settings.llm_model,
        temperature=temperature or settings.llm_temperature,
        max_tokens=settings.max_tokens,
        openai_api_key=settings.openai_api_key,
        streaming=True,
    )
