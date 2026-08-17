# ai-engine/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://kb_user:kb_pass@localhost:5432/knowledge_base"
    redis_url: str = "redis://localhost:6379"

    # Internal auth
    internal_api_token: str = "your-internal-token-change-in-production"

    # LLM
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    max_tokens: int = 2048

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # RAG
    default_top_k: int = 5
    default_similarity_threshold: float = 0.7
    max_conversation_history: int = 20

    # File
    upload_dir: str = "../api-gateway/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
