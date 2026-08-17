# ai-engine/app/memory/conversation.py
from sqlalchemy import text
from app.database import engine
from app.config import settings


def get_conversation_history(
    conversation_id: str, max_messages: int = None
) -> list[dict]:
    """获取对话历史（滑动窗口）"""
    limit = max_messages or settings.max_conversation_history
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT role, content FROM messages
            WHERE conversation_id = :conv_id
            ORDER BY created_at DESC
            LIMIT :limit
        """
            ),
            {"conv_id": conversation_id, "limit": limit},
        )
        rows = result.fetchall()

    # 反转为时间正序
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]
