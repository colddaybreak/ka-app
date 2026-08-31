# Scripts · 数据库初始化脚本

存放需要手动执行的数据库脚本。当前仅包含一个脚本：`init_pgvector.sql`。

返回 [项目主 README](../README.md) · [English Version](#english-version)

---

## init_pgvector.sql

### 脚本内容

1. **启用 pgvector 扩展**：执行 `CREATE EXTENSION IF NOT EXISTS vector;`，使 PostgreSQL 支持向量类型与相似度运算符。
2. **创建 `chunks` 表**：存储文档分块的文本内容、元数据及对应的 1536 维向量。
3. **创建索引**：一个 HNSW 向量索引（加速相似度检索），以及两个普通索引（按知识库、按文档查询）。

### 为什么不使用 Prisma 管理该表

其余 5 张业务表均由 `api-gateway` 的 Prisma 自动创建与迁移，但 Prisma 不支持 `vector` 类型，无法在 `schema.prisma` 中声明向量字段，因此 `chunks` 表只能以原生 SQL 创建。这是项目中有意的混合策略，详见 [api-gateway/README.md](../api-gateway/README.md) 的数据模型一节。

### 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键，自动生成 |
| `document_id` | UUID | 外键，引用 `documents`，级联删除 |
| `knowledge_base_id` | UUID | 外键，引用 `knowledge_bases`，级联删除 |
| `index` | INTEGER | 该分块在原文档中的序号 |
| `content` | TEXT | 分块文本内容 |
| `metadata` | JSONB | 预留的元数据字段 |
| `embedding` | vector(1536) | 向量，维度须与 `EMBEDDING_DIMENSION` 配置一致 |
| `created_at` | TIMESTAMP | 创建时间 |

### HNSW 索引参数说明

```sql
CREATE INDEX idx_chunks_embedding ON chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

| 参数 | 取值 | 说明 |
|------|------|------|
| `m` | 16 | 每个节点的连接数。取值越大召回率越高，但内存占用也越高；16 为常用默认值 |
| `ef_construction` | 64 | 建索引时的搜索宽度，影响索引质量与构建速度的平衡 |
| 运算符类 | `vector_cosine_ops` | 使用余弦距离，与检索代码中的 `<=>` 运算符对应 |

---

## 执行时机与方法

**前提条件**：

- PostgreSQL 已启动（`docker compose up -d`）。
- 业务表已创建：须先执行 `api-gateway` 的 `pnpm db:migrate`，因为 `chunks` 表的外键引用了 `documents` 与 `knowledge_bases`。

**执行命令**（仅需执行一次；脚本内均为 `IF NOT EXISTS` 语句，重复执行是安全的）：

```bash
docker exec -i kb-postgres psql -U kb_user -d knowledge_base < scripts/init_pgvector.sql
```

---

## 常见修改

### 更换向量维度

若更换为不同维度的向量模型（例如 768 维的本地模型），需依次执行：

1. 将本脚本中的 `vector(1536)` 修改为 `vector(768)`，并删除旧表后重建（不同维度的向量无法共存于同一列）。
2. 同步修改 `ai-engine/.env` 中的 `EMBEDDING_DIMENSION`。
3. 重新处理所有已入库文档；旧向量与新模型不兼容。

### 调整索引参数

数据量增长导致检索变慢时，可适当调大 `m` 与 `ef_construction` 并重建索引，以内存占用换取更高的检索精度。

---

<a id="english-version"></a>

# Scripts · Database Initialization

Contains database scripts that must be run manually. Currently there is a single script: `init_pgvector.sql`.

Back to [main README](../README.md)

---

## init_pgvector.sql

### What the script does

1. **Enables the pgvector extension**: runs `CREATE EXTENSION IF NOT EXISTS vector;`, giving PostgreSQL vector types and similarity operators.
2. **Creates the `chunks` table**: stores document chunk text, metadata, and the corresponding 1536-dimensional vectors.
3. **Creates indexes**: one HNSW vector index (accelerates similarity search) and two regular indexes (lookup by knowledge base and by document).

### Why this table is not managed by Prisma

The other five business tables are created and migrated automatically by the gateway's Prisma, but Prisma does not support the `vector` type and cannot declare vector fields in `schema.prisma`. The `chunks` table must therefore be created with raw SQL. This hybrid strategy is intentional; see the Data Model section in [api-gateway/README.md](../api-gateway/README.md).

### Table schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `document_id` | UUID | Foreign key to `documents`, cascade delete |
| `knowledge_base_id` | UUID | Foreign key to `knowledge_bases`, cascade delete |
| `index` | INTEGER | Position of the chunk within the source document |
| `content` | TEXT | Chunk text content |
| `metadata` | JSONB | Reserved metadata field |
| `embedding` | vector(1536) | Vector; dimensions must match the `EMBEDDING_DIMENSION` setting |
| `created_at` | TIMESTAMP | Creation time |

### HNSW index parameters

```sql
CREATE INDEX idx_chunks_embedding ON chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| `m` | 16 | Connections per node. Higher values improve recall at the cost of memory; 16 is a common default |
| `ef_construction` | 64 | Search width during index construction, balancing index quality against build speed |
| Operator class | `vector_cosine_ops` | Uses cosine distance, matching the `<=>` operator used in retrieval code |

---

## When and How to Run

**Prerequisites**:

- PostgreSQL is running (`docker compose up -d`).
- The business tables exist: run the gateway's `pnpm db:migrate` first, since `chunks` has foreign keys referencing `documents` and `knowledge_bases`.

**Command** (run once; all statements use `IF NOT EXISTS`, so re-running is safe):

```bash
docker exec -i kb-postgres psql -U kb_user -d knowledge_base < scripts/init_pgvector.sql
```

---

## Common Modifications

### Changing vector dimensions

If you switch to an embedding model with different dimensions (a 768-dim local model, for example), proceed as follows:

1. Change `vector(1536)` to `vector(768)` in this script, then drop and recreate the table (vectors of different dimensions cannot coexist in the same column).
2. Update `EMBEDDING_DIMENSION` in `ai-engine/.env` accordingly.
3. Reprocess all existing documents; old vectors are incompatible with the new model.

### Tuning index parameters

If search slows down as data grows, increase `m` and `ef_construction` and rebuild the index, trading memory usage for higher retrieval accuracy.
