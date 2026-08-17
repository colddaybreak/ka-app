# ai-engine/app/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_query(query: str, params: dict = None):
    """执行原生 SQL（用于 chunks 表操作）"""
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        return result
