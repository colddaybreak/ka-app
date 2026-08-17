# ai-engine/app/models/embedding.py
from abc import ABC, abstractmethod
from langchain_openai import OpenAIEmbeddings
from app.config import settings


class EmbeddingModel(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class OpenAIEmbedding(EmbeddingModel):
    def __init__(self):
        self.model = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.model.embed_query(text)


def get_embedding_model() -> EmbeddingModel:
    """工厂函数，后期可切换为本地模型"""
    return OpenAIEmbedding()
