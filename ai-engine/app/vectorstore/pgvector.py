# ai-engine/app/vectorstore/pgvector.py
from sqlalchemy import text
from app.database import engine


class PgVectorStore:
    def insert_chunks(
        self,
        document_id: str,
        knowledge_base_id: str,
        chunks: list[dict],
        embeddings: list[list[float]],
    ):
        """批量插入分块和向量"""
        with engine.begin() as conn:
            for chunk, embedding in zip(chunks, embeddings):
                conn.execute(
                    text(
                        """
                    INSERT INTO chunks (document_id, knowledge_base_id, chunk_index,
                                        content, metadata, embedding)
                    VALUES (:doc_id, :kb_id, :chunk_index, :content, :metadata::jsonb,
                            :embedding::vector)
                """
                    ),
                    {
                        "doc_id": document_id,
                        "kb_id": knowledge_base_id,
                        "chunk_index": chunk["index"],
                        "content": chunk["content"],
                        "metadata": "{}",
                        "embedding": str(embedding),
                    },
                )

    def search(
        self,
        query_embedding: list[float],
        knowledge_base_id: str,
        top_k: int = 5,
    ) -> list[dict]:
        """余弦相似度搜索，返回按相似度降序的 top_k 候选（阈值过滤由调用方负责）"""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT c.id, c.content, c.metadata, c.document_id,
                       d.filename as document_name,
                       1 - (c.embedding <=> :query::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.knowledge_base_id = :kb_id
                ORDER BY c.embedding <=> :query::vector
                LIMIT :top_k
            """
                ),
                {
                    "query": str(query_embedding),
                    "kb_id": knowledge_base_id,
                    "top_k": top_k,
                },
            )
            rows = result.fetchall()
            return [
                {
                    "chunk_id": str(row[0]),
                    "content": row[1],
                    "metadata": row[2],
                    "document_id": str(row[3]),
                    "document_name": row[4],
                    "similarity": float(row[5]),
                }
                for row in rows
            ]

    def keyword_search(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int = 5,
    ) -> list[dict]:
        """关键词全文检索（ts_rank 排序），返回结构与 search() 一致"""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT c.id, c.content, c.metadata, c.document_id,
                       d.filename as document_name,
                       ts_rank(c.tsv, plainto_tsquery('simple', :query)) as rank
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.knowledge_base_id = :kb_id
                  AND c.tsv @@ plainto_tsquery('simple', :query)
                ORDER BY rank DESC
                LIMIT :top_k
            """
                ),
                {
                    "query": query,
                    "kb_id": knowledge_base_id,
                    "top_k": top_k,
                },
            )
            rows = result.fetchall()
            return [
                {
                    "chunk_id": str(row[0]),
                    "content": row[1],
                    "metadata": row[2],
                    "document_id": str(row[3]),
                    "document_name": row[4],
                    # ts_rank 分数与向量余弦相似度量纲不同，加权融合前需归一化
                    "similarity": float(row[5]),
                }
                for row in rows
            ]

    def delete_by_document(self, document_id: str):
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM chunks WHERE document_id = :doc_id"),
                {"doc_id": document_id},
            )

    def delete_by_knowledge_base(self, knowledge_base_id: str):
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM chunks WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )

    def count(self, knowledge_base_id: str) -> int:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM chunks WHERE knowledge_base_id = :kb_id"
                ),
                {"kb_id": knowledge_base_id},
            )
            return result.scalar()
