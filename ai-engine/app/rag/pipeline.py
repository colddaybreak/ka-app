# ai-engine/app/rag/pipeline.py
from app.rag.parser import DocumentParser
from app.rag.splitter import TextSplitter
from app.models.embedding import get_embedding_model
from app.vectorstore.pgvector import PgVectorStore
from app.config import settings


class RAGPipeline:
    def __init__(self):
        self.parser = DocumentParser()
        self.embedding_model = get_embedding_model()
        self.vector_store = PgVectorStore()

    def process_document(
        self,
        document_id: str,
        knowledge_base_id: str,
        file_path: str,
        chunk_strategy: dict,
    ):
        """完整的文档处理流水线"""
        # 1. 解析
        text = self.parser.parse(file_path)

        # 2. 分块
        splitter = TextSplitter(
            chunk_size=chunk_strategy.get("chunkSize", 500),
            chunk_overlap=chunk_strategy.get("chunkOverlap", 50),
        )
        chunks = splitter.split(text)

        # 3. 向量化
        texts = [c["content"] for c in chunks]
        embeddings = self.embedding_model.embed_texts(texts)

        # 4. 删除旧数据（重新处理场景）
        self.vector_store.delete_by_document(document_id)

        # 5. 存储
        self.vector_store.insert_chunks(
            document_id, knowledge_base_id, chunks, embeddings
        )

        return len(chunks)

    def retrieve(
        self, query: str, knowledge_base_id: str, retrieval_config: dict
    ) -> list[dict]:
        """检索相关分块"""
        query_embedding = self.embedding_model.embed_query(query)
        results = self.vector_store.search(
            query_embedding=query_embedding,
            knowledge_base_id=knowledge_base_id,
            top_k=retrieval_config.get("topK", settings.default_top_k),
            threshold=retrieval_config.get(
                "similarityThreshold", settings.default_similarity_threshold
            ),
        )
        return results
