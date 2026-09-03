# AI Engine · Python AI 引擎

AI Engine 是知识库问答的核心服务，负责文档解析、分块、向量化、相似度检索，以及调用大语言模型流式生成回答。

返回 [项目主 README](../README.md) · [English Version](#english-version)

---

## 模块定位

本服务是系统中唯一与 AI 能力交互的部分。它不直接面向用户，只接受来自 `api-gateway` 的内部调用，并通过 `X-Internal-Token` 请求头进行身份验证。

核心职责：

1. **文档处理**：将上传的 PDF、Word、Markdown 等文件解析为纯文本，切分为语义分块，转换为向量后写入 `chunks` 表。
2. **智能问答**：接收用户提问，通过向量、关键词或混合检索获取最相关的分块（可选 Rerank 重排），将其注入提示词，调用大语言模型流式生成回答。

---

## 目录结构

```
ai-engine/
├── app/
│   ├── main.py                  # FastAPI 应用入口，挂载路由
│   ├── config.py                # 配置中心（pydantic-settings，读取 .env）
│   ├── database.py              # SQLAlchemy 引擎与会话管理
│   ├── api/
│   │   ├── deps.py              # 依赖注入：验证内部访问令牌
│   │   └── routes/
│   │       ├── chat.py          # POST /ai/chat/stream 流式对话
│   │       └── documents.py     # 文档处理 / 状态查询 / 向量删除
│   ├── rag/
│   │   ├── parser.py            # 文档解析器（按扩展名分发）
│   │   ├── splitter.py          # 文本分块（递归字符切分）
│   │   ├── pipeline.py          # RAG 流水线：解析 -> 分块 -> 向量化 -> 存储；检索编排
│   │   ├── retriever.py         # 组装 RAG 提示词
│   │   ├── fusion.py            # 多路召回融合（RRF / 加权）
│   │   └── reranker.py          # Rerank 重排（DashScope gte-rerank）
│   ├── models/
│   │   ├── embedding.py         # 向量模型（抽象基类 + OpenAI 兼容实现，默认阿里云百炼）
│   │   └── llm.py               # 大语言模型工厂函数
│   ├── vectorstore/
│   │   └── pgvector.py          # pgvector 向量存储（原生 SQL）
│   └── memory/
│       └── conversation.py      # 对话历史（滑动窗口）
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
└── README.md
```

---

## RAG 流水线

RAG（Retrieval-Augmented Generation）是本模块的核心机制，其目标是让模型基于私有文档作答，而非依赖参数化记忆，从而降低幻觉、保证答案可溯源。

### 文档入库流程

```
文件 -> [parser] 解析为文本 -> [splitter] 切分块 -> [embedding] 批量向量化 -> [pgvector] 写入 chunks 表
```

| 环节 | 实现 | 说明 |
|------|------|------|
| 解析 | `rag/parser.py` | 按扩展名路由至对应解析器：PDF 使用 PyMuPDF（保留页码标记），DOCX 使用 python-docx，HTML 使用 BeautifulSoup（剔除 script 与 style） |
| 分块 | `rag/splitter.py` | 基于 LangChain 递归字符切分器，优先在段落、句子、空格边界断开；显式加入中文标点（。！？），避免切断中文句子 |
| 向量化 | `models/embedding.py` | 调用 OpenAI 兼容 Embedding API（默认阿里云百炼），将文本块转换为 1536 维向量 |
| 存储 | `vectorstore/pgvector.py` | 写入 `chunks` 表，该表建有 HNSW 索引，详见 `scripts/init_pgvector.sql` |

### 问答流程

```
用户问题 -> 召回（向量 / 关键词 / 混合）-> (可选) Rerank 重排
        -> [retriever] 注入系统提示词 -> [llm] 大模型流式生成 -> SSE 回传
```

| 环节 | 说明 |
|------|------|
| 检索 | 由知识库 `retrievalConfig` 决定：`mode` 为 `vector`（默认，余弦相似度 + 阈值筛选，默认 0.7）、`keyword`（PostgreSQL 全文检索）或 `hybrid`（双路召回后按 `fusionMethod` 做 RRF / 加权融合）；阈值全部滤空时兜底保留最高分候选 |
| 重排 | `useRerank` 开启时调用百炼 `gte-rerank-v2` 对候选重排并取 `rerankTopN`；服务不可用时自动降级，不阻断问答 |
| 提示词 | `rag/retriever.py` 在系统提示词中要求模型"依据参考资料作答，资料缺失时如实告知"，以抑制幻觉 |
| 记忆 | `memory/conversation.py` 取最近 20 条消息作为上下文，控制 token 成本 |
| 流式输出 | `api/routes/chat.py` 先发送 `citations` 事件（引用来源），再逐块发送 `token` 事件，最后发送 `done` 事件 |

---

## 设计决策

### 选用 FastAPI

对话生成是典型的长耗时异步场景：单次请求需等待大模型数秒，期间不能阻塞其他请求。FastAPI 原生支持 `async/await` 与 SSE（`sse-starlette`），并提供依赖注入（`verify_internal_token`）与后台任务（`BackgroundTasks`）机制。

### 文档处理采用 BackgroundTasks

上传接口立即返回"处理中"状态，解析与向量化在后台任务中执行。相比引入 Celery 等独立任务队列，该方案无需额外进程，部署与运维成本更低，适合当前规模。

### 向量表使用原生 SQL

网关侧的 Prisma 不支持 `vector(1536)` 类型，因此 `chunks` 表在 `scripts/init_pgvector.sql` 中以原生 SQL 创建，本模块通过 SQLAlchemy 的 `text()` 直接操作。这是项目中有意的混合策略，详见 [api-gateway/README.md](../api-gateway/README.md) 的数据模型一节。

### 内部服务鉴权

所有路由均挂载 `verify_internal_token` 依赖，校验 `X-Internal-Token` 请求头。该服务不应暴露公网端口，仅由网关内部调用；用户身份通过 `X-User-Id` 请求头由网关透传。

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/ai/health` | 健康检查 |
| `POST` | `/ai/chat/stream` | 流式对话（SSE），核心端点 |
| `POST` | `/ai/documents/{id}/process` | 触发文档异步处理 |
| `GET` | `/ai/documents/{id}/status` | 查询处理状态 |
| `DELETE` | `/ai/documents/{id}/vectors` | 删除文档向量 |

除 `/ai/health` 外，所有端点均要求携带 `X-Internal-Token` 请求头。

---

## 配置项

配置通过 `.env` 文件加载（模板见 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://kb_user:kb_pass@localhost:5432/knowledge_base` | 数据库连接串 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 连接串（预留） |
| `INTERNAL_API_TOKEN` | 无 | 必填，必须与 api-gateway 保持一致 |
| `OPENAI_API_KEY` | 无 | 必填，OpenAI 兼容服务的 API 密钥（默认为阿里云百炼） |
| `OPENAI_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 兼容端点，可改为 `https://api.openai.com/v1` 切换回 OpenAI |
| `LLM_MODEL` | `deepseek-v4-flash` | 对话模型 |
| `ENABLE_THINKING` | `true` | 思考模式开关，本项目默认开启（模型先行推理再作答）；追求更快首字响应可设为 `false`；切换回 OpenAI 官方端点时须留空 |
| `EMBEDDING_MODEL` | `text-embedding-v4` | 向量模型 |
| `EMBEDDING_DIMENSION` | `1536` | 向量维度，须与 `chunks` 表定义一致 |
| `DEFAULT_TOP_K` | `10` | 默认检索条数 |
| `DEFAULT_SIMILARITY_THRESHOLD` | `0.7` | 相似度阈值 |
| `MAX_CONVERSATION_HISTORY` | `20` | 对话记忆窗口大小 |
| `RERANK_MODEL` | `gte-rerank-v2` | Rerank 模型（DashScope text-rerank，复用 `OPENAI_API_KEY`） |
| `UPLOAD_DIR` | `../api-gateway/uploads` | 上传文件目录（与网关共享） |

---

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # 填入百炼（DashScope）API Key，变量名为 OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

健康检查：

```bash
curl http://localhost:8000/ai/health
```

---

## 扩展指南

### 支持新的文件格式（以 Excel 为例）

1. 在 `rag/parser.py` 的 `parsers` 字典中新增 `".xlsx": self._parse_xlsx` 映射。
2. 实现 `_parse_xlsx` 方法，返回纯文本。
3. 在 `api-gateway` 的 `document.routes.ts` 中，将 `xlsx` 加入文件类型白名单。

### 更换向量模型（以本地 bge 模型为例）

1. 在 `models/embedding.py` 中新增继承 `EmbeddingModel` 的实现类。
2. 修改 `get_embedding_model()` 工厂函数，返回新实现。
3. 注意事项：若新模型维度不同，需同步修改 `init_pgvector.sql` 中的 `vector(1536)` 定义；已入库文档与新模型不兼容，必须全部重新向量化。

### 更换大语言模型

修改 `models/llm.py` 中的 `get_llm()`，或在知识库的 `modelConfig` 中传入不同的 `model` 字段。

### 新增 RAG 端点

1. 在 `app/api/routes/` 下新建路由文件，使用 `APIRouter(dependencies=[Depends(verify_internal_token)])` 声明。
2. 在 `app/main.py` 中通过 `include_router` 挂载。

---

<a id="english-version"></a>

# AI Engine · Python AI Service

The AI Engine is the core service for knowledge base Q&A. It parses documents, chunks them, vectorizes them, performs similarity search, and calls a large language model to stream answers.

Back to [main README](../README.md)

---

## Module Purpose

This service is the only part of the system that interacts with AI capabilities. It never faces users directly; it only accepts internal calls from `api-gateway`, verified via the `X-Internal-Token` header.

Core responsibilities:

1. **Document processing**: parse uploaded PDF, Word and Markdown files into plain text, split them into semantic chunks, convert them into vectors, and write them to the `chunks` table.
2. **Question answering**: receive user questions, retrieve the most relevant chunks via vector, keyword or hybrid search (with optional reranking), inject them into the prompt, and stream an answer from the LLM.

---

## Directory Structure

```
ai-engine/
├── app/
│   ├── main.py                  # FastAPI entry point, mounts routers
│   ├── config.py                # Config center (pydantic-settings, reads .env)
│   ├── database.py              # SQLAlchemy engine and session management
│   ├── api/
│   │   ├── deps.py              # Dependency injection: verify internal token
│   │   └── routes/
│   │       ├── chat.py          # POST /ai/chat/stream streaming chat
│   │       └── documents.py     # document processing / status / vector deletion
│   ├── rag/
│   │   ├── parser.py            # Document parser (dispatched by extension)
│   │   ├── splitter.py          # Text chunking (recursive character split)
│   │   ├── pipeline.py          # RAG pipeline: parse -> chunk -> embed -> store; retrieval orchestration
│   │   ├── retriever.py         # Assembles the RAG prompt
│   │   ├── fusion.py            # Multi-path recall fusion (RRF / weighted)
│   │   └── reranker.py          # Reranking (DashScope gte-rerank)
│   ├── models/
│   │   ├── embedding.py         # Embedding models (abstract base + OpenAI-compatible impl, Bailian by default)
│   │   └── llm.py               # LLM factory function
│   ├── vectorstore/
│   │   └── pgvector.py          # pgvector store (raw SQL)
│   └── memory/
│       └── conversation.py      # Conversation history (sliding window)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
└── README.md
```

---

## RAG Pipeline

RAG (Retrieval-Augmented Generation) is the core mechanism of this module. Its goal is to make the model answer from private documents rather than parametric memory, which reduces hallucination and keeps answers traceable.

### Document ingestion flow

```
file -> [parser] parse to text -> [splitter] chunk -> [embedding] batch vectorize -> [pgvector] write to chunks table
```

| Stage | Implementation | Description |
|-------|----------------|-------------|
| Parsing | `rag/parser.py` | Routes by extension: PDF via PyMuPDF (keeps page markers), DOCX via python-docx, HTML via BeautifulSoup (strips script and style) |
| Chunking | `rag/splitter.py` | LangChain recursive character splitter; prefers paragraph, sentence and space boundaries, with Chinese punctuation explicitly added to avoid splitting Chinese sentences |
| Embedding | `models/embedding.py` | Calls an OpenAI-compatible Embedding API (Alibaba Cloud Model Studio by default) to convert chunks into 1536-dim vectors |
| Storage | `vectorstore/pgvector.py` | Writes to the `chunks` table, which carries an HNSW index (see `scripts/init_pgvector.sql`) |

### Q&A flow

```
user question -> recall (vector / keyword / hybrid) -> (optional) rerank
             -> [retriever] inject into system prompt -> [llm] stream generation -> SSE response
```

| Stage | Description |
|-------|-------------|
| Retrieval | Driven by each knowledge base's `retrievalConfig`: `mode` can be `vector` (default; cosine similarity with a threshold filter, default 0.7), `keyword` (PostgreSQL full-text search), or `hybrid` (dual-path recall fused via RRF or weighted scoring per `fusionMethod`); if the threshold filters everything out, the best candidate is kept as a fallback |
| Reranking | When `useRerank` is on, candidates are reranked by Bailian `gte-rerank-v2` and truncated to `rerankTopN`; the service degrades gracefully on failure and never blocks Q&A |
| Prompting | `rag/retriever.py` instructs the model to answer from references and admit when information is missing, suppressing hallucination |
| Memory | `memory/conversation.py` uses the last 20 messages as context, controlling token cost |
| Streaming | `api/routes/chat.py` emits a `citations` event first, then `token` events, then a final `done` event |

---

## Design Decisions

### Why FastAPI

Answer generation is a long-running async workload: each request waits seconds on the LLM and must not block others. FastAPI natively supports `async/await` and SSE (`sse-starlette`), and provides dependency injection (`verify_internal_token`) and background tasks (`BackgroundTasks`).

### Why BackgroundTasks for document processing

The upload endpoint returns a "processing" status immediately; parsing and vectorization run in background tasks. Compared to introducing a separate task queue such as Celery, this avoids an extra process and lowers deployment and operational cost, which fits the current scale.

### Why raw SQL for the vector table

Prisma on the gateway side does not support the `vector(1536)` type, so the `chunks` table is created with raw SQL in `scripts/init_pgvector.sql`, and this module operates on it via SQLAlchemy's `text()`. This hybrid strategy is intentional; see the Data Model section in [api-gateway/README.md](../api-gateway/README.md).

### Internal authentication

Every route mounts the `verify_internal_token` dependency, which validates the `X-Internal-Token` header. This service must not be exposed to the public internet; it is called only by the gateway, which passes user identity through the `X-User-Id` header.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ai/health` | Health check |
| `POST` | `/ai/chat/stream` | Streaming chat (SSE), the core endpoint |
| `POST` | `/ai/documents/{id}/process` | Trigger async document processing |
| `GET` | `/ai/documents/{id}/status` | Query processing status |
| `DELETE` | `/ai/documents/{id}/vectors` | Delete document vectors |

All endpoints except `/ai/health` require the `X-Internal-Token` header.

---

## Configuration

Configuration is loaded from `.env` (see the `.env.example` template):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://kb_user:kb_pass@localhost:5432/knowledge_base` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string (reserved) |
| `INTERNAL_API_TOKEN` | none | Required; must match api-gateway's |
| `OPENAI_API_KEY` | none | Required; API key of an OpenAI-compatible service (Alibaba Cloud Model Studio by default) |
| `OPENAI_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Compatible endpoint; set to `https://api.openai.com/v1` to switch back to OpenAI |
| `LLM_MODEL` | `deepseek-v4-flash` | Chat model |
| `ENABLE_THINKING` | `true` | Thinking-mode switch, enabled by default in this project (the model reasons before answering); set `false` for faster first tokens; must be left empty when switching back to OpenAI's official endpoint |
| `EMBEDDING_MODEL` | `text-embedding-v4` | Embedding model |
| `EMBEDDING_DIMENSION` | `1536` | Vector dimensions; must match the `chunks` table definition |
| `DEFAULT_TOP_K` | `10` | Default retrieval count |
| `DEFAULT_SIMILARITY_THRESHOLD` | `0.7` | Similarity threshold |
| `MAX_CONVERSATION_HISTORY` | `20` | Conversation memory window size |
| `RERANK_MODEL` | `gte-rerank-v2` | Rerank model (DashScope text-rerank, reuses `OPENAI_API_KEY`) |
| `UPLOAD_DIR` | `../api-gateway/uploads` | Upload directory (shared with the gateway) |

---

## Running Locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in the Bailian (DashScope) API key via OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/ai/health
```

---

## Extension Guide

### Support a new file format (Excel, for example)

1. Add a `".xlsx": self._parse_xlsx` mapping to the `parsers` dictionary in `rag/parser.py`.
2. Implement `_parse_xlsx`, returning plain text.
3. Add `xlsx` to the file-type allowlist in `api-gateway`'s `document.routes.ts`.

### Swap the embedding model (a local bge model, for example)

1. Add a new implementation class extending `EmbeddingModel` in `models/embedding.py`.
2. Update the `get_embedding_model()` factory to return the new implementation.
3. Important: if the new model uses different dimensions, update the `vector(1536)` definition in `init_pgvector.sql`; existing documents are incompatible and must all be re-vectorized.

### Swap the LLM

Modify `get_llm()` in `models/llm.py`, or pass a different `model` value in a knowledge base's `modelConfig`.

### Add a new RAG endpoint

1. Create a router file under `app/api/routes/`, declared with `APIRouter(dependencies=[Depends(verify_internal_token)])`.
2. Mount it via `include_router` in `app/main.py`.
