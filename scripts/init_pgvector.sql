-- scripts/init_pgvector.sql
-- 在 PostgreSQL 中执行一次：初始化 pgvector 扩展和 chunks 表

CREATE EXTENSION IF NOT EXISTS vector;

-- 创建 chunks 表（Prisma 不管理这张表，因为 pgvector 类型需要原生 SQL）
CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  -- 注意：不能用 index 作列名，它是 PostgreSQL 保留字
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  embedding vector(1536),           -- 维度与 EMBEDDING_DIMENSION 一致
  created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW 向量索引（加速相似度搜索）
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 按知识库查询的索引
CREATE INDEX IF NOT EXISTS idx_chunks_kb_id ON chunks(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(document_id);
