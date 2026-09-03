# ai-engine/app/rag/pipeline.py
from app.rag.parser import DocumentParser
from app.rag.splitter import TextSplitter
from app.rag.fusion import rrf_fusion, weighted_fusion
from app.rag.reranker import rerank
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
        """检索相关分块。mode: vector（默认）/ keyword / hybrid"""
        mode = retrieval_config.get("mode", "vector")
        top_k = retrieval_config.get("topK", settings.default_top_k)

        # 纯关键词召回：ts_rank 与余弦相似度不可比，不做阈值过滤
        if mode == "keyword":
            results = self.vector_store.keyword_search(
                query=query, knowledge_base_id=knowledge_base_id, top_k=top_k
            )
        else:
            query_embedding = self.embedding_model.embed_query(query)
            vector_results = self.vector_store.search(
                query_embedding=query_embedding,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
            )
            threshold = retrieval_config.get(
                "similarityThreshold", settings.default_similarity_threshold
            )

            if mode == "hybrid":
                # 向量路先按阈值过滤，再与关键词路融合（默认 RRF，可配加权）
                vector_kept = [
                    r for r in vector_results if r["similarity"] >= threshold
                ]
                keyword_results = self.vector_store.keyword_search(
                    query=query, knowledge_base_id=knowledge_base_id, top_k=top_k
                )
                if retrieval_config.get("fusionMethod") == "weighted":
                    weights = retrieval_config.get("weights", {})
                    fused = weighted_fusion(
                        [vector_kept, keyword_results],
                        [
                            weights.get("vector", 0.5),
                            weights.get("keyword", 0.5),
                        ],
                    )
                else:
                    fused = rrf_fusion([vector_kept, keyword_results])
                results = fused[:top_k]
            else:
                # 默认向量模式：阈值筛选
                results = [
                    r for r in vector_results if r["similarity"] >= threshold
                ]

            # 兜底：阈值过严导致全部被滤掉时，保留最高分候选，避免上下文完全为空
            if not results and vector_results:
                results = [vector_results[0]]

        # Rerank（可选，useRerank 开关）：对召回/融合结果重排，取 rerankTopN
        if retrieval_config.get("useRerank") and results:
            results = rerank(
                query, results, retrieval_config.get("rerankTopN", top_k)
            )
        return results
