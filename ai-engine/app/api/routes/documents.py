# ai-engine/app/api/routes/documents.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import verify_internal_token
from app.database import get_db, engine
from app.rag.pipeline import RAGPipeline
from app.vectorstore.pgvector import PgVectorStore
from app.config import settings
from pathlib import Path
import json

router = APIRouter(
    prefix="/documents", dependencies=[Depends(verify_internal_token)]
)
rag_pipeline = RAGPipeline()


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """触发文档异步处理"""
    # 查询文档信息
    doc = db.execute(
        text(
            """
        SELECT d.file_path, d.knowledge_base_id, kb.chunk_strategy
        FROM documents d
        JOIN knowledge_bases kb ON d.knowledge_base_id = kb.id
        WHERE d.id = :doc_id
    """
        ),
        {"doc_id": document_id},
    ).fetchone()

    if not doc:
        return {"error": "文档不存在"}

    # 更新状态为 processing
    db.execute(
        text("UPDATE documents SET status = 'processing' WHERE id = :doc_id"),
        {"doc_id": document_id},
    )
    db.commit()

    # 解析 chunk_strategy（可能是 JSON 字符串或 dict）
    chunk_strategy = doc[2]
    if isinstance(chunk_strategy, str):
        chunk_strategy = json.loads(chunk_strategy)

    # 拼接文件完整路径：网关保存的是绝对路径（兼容 Windows 反斜杠）；
    # 历史数据中的相对路径以 api-gateway 目录为基准（upload_dir 指向其下的 uploads）
    file_path = doc[0].replace("\\", "/")
    if not Path(file_path).is_absolute():
        file_path = str(Path(settings.upload_dir).parent / file_path)

    # 异步处理
    background_tasks.add_task(
        _process_document_task,
        document_id,
        str(doc[1]),  # knowledge_base_id
        file_path,
        chunk_strategy,
    )

    return {"status": "processing", "document_id": document_id}


def _process_document_task(
    document_id: str,
    knowledge_base_id: str,
    file_path: str,
    chunk_strategy: dict,
):
    """后台任务：文档解析 -> 分块 -> 向量化"""
    try:
        chunk_count = rag_pipeline.process_document(
            document_id, knowledge_base_id, file_path, chunk_strategy
        )
        # 更新状态
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                UPDATE documents SET status = 'done', chunk_count = :count,
                processed_at = NOW() WHERE id = :doc_id
            """
                ),
                {"count": chunk_count, "doc_id": document_id},
            )
    except Exception as e:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                UPDATE documents SET status = 'failed', error_message = :err
                WHERE id = :doc_id
            """
                ),
                {"err": str(e), "doc_id": document_id},
            )


@router.get("/{document_id}/status")
async def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """查询文档处理状态（Node.js 轮询此端点）"""
    result = db.execute(
        text(
            """
        SELECT status, error_message, chunk_count FROM documents WHERE id = :doc_id
    """
        ),
        {"doc_id": document_id},
    ).fetchone()

    if not result:
        return {"error": "文档不存在"}

    return {
        "document_id": document_id,
        "status": result[0],
        "error_message": result[1],
        "chunk_count": result[2],
    }


@router.delete("/{document_id}/vectors")
async def delete_document_vectors(document_id: str):
    """删除文档的所有向量数据（删除文档时由 Node.js 调用）"""
    vector_store = PgVectorStore()
    vector_store.delete_by_document(document_id)
    return {"success": True}
