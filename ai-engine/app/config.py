# ai-engine/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://kb_user:kb_pass@localhost:5432/knowledge_base"
    redis_url: str = "redis://localhost:6379"

    # Internal auth
    internal_api_token: str = "your-internal-token-change-in-production"

    # LLM / Embedding（OpenAI 兼容接口）
    # 默认对接阿里云百炼 DashScope，对话模型为 deepseek-v4-flash；
    # 如需使用 OpenAI 官方服务，将 OPENAI_BASE_URL 设为
    # https://api.openai.com/v1 并更换相应模型名即可
    openai_api_key: str = ""
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.7
    # 思考模式开启后输出更长，上限需预留足够空间
    max_tokens: int = 4096
    # 思考模式开关（仅部分模型支持，如百炼上的 DeepSeek V4 系列）：
    # 设为 true / false 时通过 extra_body 显式传递；留空则不传，使用模型默认行为。
    # 本项目默认开启（.env 中 ENABLE_THINKING=true）。
    # 注意：切换回 OpenAI 官方端点时请留空，官方 API 不识别该参数
    enable_thinking: bool | None = None

    # Embedding
    embedding_model: str = "text-embedding-v4"
    embedding_dimension: int = 1536

    # RAG
    default_top_k: int = 10
    default_similarity_threshold: float = 0.7
    max_conversation_history: int = 20

    # File
    upload_dir: str = "../api-gateway/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
