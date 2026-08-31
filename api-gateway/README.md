# API Gateway · Node.js API 网关

API Gateway 是所有客户端请求的统一入口，负责身份认证、业务数据的增删改查、文件上传，并将 AI 相关请求转发至 Python 引擎。

返回 [项目主 README](../README.md) · [English Version](#english-version)

---

## 模块定位

前端的所有请求均到达本服务（默认端口 `:3000`）。本模块承担三类职责：

1. **认证与鉴权**：验证 JWT 令牌，确认调用方身份与权限。
2. **业务处理**：通过 Prisma 操作 PostgreSQL，处理用户、知识库、文档、对话的增删改查。
3. **请求转发**：涉及 AI 的请求（流式对话、文档处理）透传至 `ai-engine`，本模块不包含任何 AI 逻辑。

模块边界约定：业务规则保留在网关，AI 逻辑保留在 `ai-engine`。两者通过共享的 `INTERNAL_API_TOKEN` 建立信任。

---

## 目录结构

```
api-gateway/
├── src/
│   ├── server.ts                    # 入口：加载配置并监听端口
│   ├── app.ts                       # 组装 Fastify 实例：注册插件与路由
│   ├── middleware/
│   │   └── auth.middleware.ts       # authenticate / requireAdmin 守卫
│   ├── proxy/
│   │   └── ai-proxy.ts              # 转发到 AI 引擎（SSE 流式 + 同步）
│   └── routes/
│       ├── auth.routes.ts           # 注册 / 登录 / 获取当前用户
│       ├── knowledge-base.routes.ts # 知识库 CRUD
│       ├── document.routes.ts       # 文件上传 / 状态 / 删除
│       ├── conversation.routes.ts   # 对话 CRUD + 流式提问
│       └── dashboard.routes.ts      # 统计数据与趋势
├── prisma/
│   └── schema.prisma                # 数据模型定义（5 张业务表）
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

---

## 认证与授权

### JWT 流程

- 注册与登录（`auth.routes.ts`）：密码经 `bcrypt`（10 轮）哈希后存储；验证通过后签发 JWT，默认有效期 7 天。
- 路由守卫（`auth.middleware.ts`）：`authenticate` 验证令牌；`requireAdmin` 在其基础上追加角色检查。除 `/api/auth/register` 与 `/api/auth/login` 外，所有路由均挂载守卫。

### 角色模型

| 角色 | 数据可见范围 |
|------|--------------|
| `admin` | 全部知识库、文档、对话 |
| `user` | 仅限本人创建的资源 |

实现方式：查询时管理员不附加过滤条件，普通用户附加 `where: { userId }` 条件。

---

## AI 代理

`proxy/ai-proxy.ts` 提供两种转发模式：

### SSE 流式代理（`proxyChatStream`）

用于对话场景，将 Python 引擎生成的回答逐字转发给前端：

- 使用 `axios` 以 `responseType: 'stream'` 请求 Python 引擎，获取可读流。
- 直接操作 `reply.raw`（底层 HTTP 响应对象），绕过 Fastify 的序列化缓冲，逐块写入。
- 设置 `X-Accel-Buffering: no` 响应头，防止反向代理（如 Nginx）对响应进行攒批缓冲。

### 同步代理（`proxyToAI`）

用于文档处理、状态查询等普通请求：转发请求并等待结果返回，超时时间为 30 秒。

所有转发请求均附带 `X-Internal-Token` 与 `X-User-Id` 请求头。

---

## 数据模型

`schema.prisma` 定义 5 张业务表，关系如下：

```
User ──< KnowledgeBase ──< Document
                │
                └──< Conversation ──< Message
```

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `users` | email、passwordHash、role | 用户与角色 |
| `knowledge_bases` | embeddingModel、chunkStrategy、retrievalConfig | 分块与检索配置以 JSON 存储，支持按知识库定制 |
| `documents` | status、chunkCount | 处理状态机：pending -> processing -> done / failed |
| `conversations` | systemPrompt、modelConfig | 每个对话绑定一个知识库 |
| `messages` | role、citations、tokenUsage | citations 存储引用来源，供前端展示 |

向量表 `chunks` 不在 Prisma 管理范围内（Prisma 不支持 vector 类型），由 `scripts/init_pgvector.sql` 以原生 SQL 创建。删除文档时，网关先调用 AI 引擎删除向量，再删除业务记录。

---

## API 端点清单

| 方法 | 路径 | 说明 | 需要认证 |
|------|------|------|----------|
| `POST` | `/api/auth/register` | 注册 | 否 |
| `POST` | `/api/auth/login` | 登录 | 否 |
| `GET` | `/api/auth/me` | 当前用户信息 | 是 |
| `POST` | `/api/knowledge-bases` | 创建知识库 | 是 |
| `GET` | `/api/knowledge-bases` | 知识库列表 | 是 |
| `GET` | `/api/knowledge-bases/:id` | 知识库详情（含文档） | 是 |
| `PUT` | `/api/knowledge-bases/:id` | 更新知识库 | 是 |
| `DELETE` | `/api/knowledge-bases/:id` | 删除知识库（级联删除） | 是 |
| `POST` | `/api/documents/upload/:knowledgeBaseId` | 上传文档 | 是 |
| `GET` | `/api/documents/knowledge-base/:kbId` | 文档列表 | 是 |
| `GET` | `/api/documents/:id/status` | 处理状态（前端轮询） | 是 |
| `DELETE` | `/api/documents/:id` | 删除文档及其向量 | 是 |
| `POST` | `/api/conversations` | 创建对话 | 是 |
| `GET` | `/api/conversations` | 对话列表 | 是 |
| `GET` | `/api/conversations/:id` | 对话详情（含消息历史） | 是 |
| `PUT` | `/api/conversations/:id` | 更新对话设置 | 是 |
| `DELETE` | `/api/conversations/:id` | 删除对话 | 是 |
| `POST` | `/api/conversations/stream` | 流式提问（SSE） | 是 |
| `GET` | `/api/dashboard/stats` | 统计卡片 | 是 |
| `GET` | `/api/dashboard/trends` | 对话趋势 | 是 |
| `GET` | `/api/health` | 健康检查 | 否 |

---

## 配置项

配置通过 `.env` 文件加载（模板见 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://kb_user:kb_pass@localhost:5432/knowledge_base` | 数据库连接串 |
| `JWT_SECRET` | 无 | 必填，生产环境必须修改 |
| `JWT_EXPIRES_IN` | `7d` | 令牌有效期 |
| `AI_ENGINE_URL` | `http://localhost:8000` | Python 引擎地址 |
| `INTERNAL_API_TOKEN` | 无 | 必填，必须与 ai-engine 保持一致 |
| `UPLOAD_DIR` | `./uploads` | 上传文件存储目录 |
| `PORT` | `3000` | 监听端口 |

---

## 本地运行

```bash
cp .env.example .env
pnpm install
pnpm db:generate     # 生成 Prisma Client
pnpm db:migrate      # 创建 / 迁移数据表
pnpm dev             # 启动于 :3000（tsx watch 热重载）
```

健康检查：

```bash
curl http://localhost:3000/api/health
```

---

## 扩展指南

### 新增路由模块

1. 在 `src/routes/` 下新建 `xxx.routes.ts`，导出 `async function xxxRoutes(app: FastifyInstance)`。
2. 需要登录保护时，在函数体内调用 `app.addHook('preHandler', authenticate)`。
3. 在 `app.ts` 中注册：`app.register(xxxRoutes, { prefix: '/api/xxx' })`。

### 修改数据模型

1. 编辑 `prisma/schema.prisma`。
2. 执行 `pnpm db:migrate` 生成并应用迁移。
3. 执行 `pnpm db:generate` 重新生成类型安全的 Client。

### 新增依赖 AI 的功能

- 同步调用：`await proxyToAI('/ai/xxx', body)`。
- 流式调用：参照 `proxyChatStream` 的实现，以 `responseType: 'stream'` 请求 Python 引擎，并将数据块逐一写入 `reply.raw`。

---

<a id="english-version"></a>

# API Gateway · Node.js Service

The API Gateway is the single entry point for all client requests. It handles authentication, business CRUD operations and file uploads, and forwards AI-related requests to the Python engine.

Back to [main README](../README.md)

---

## Module Purpose

All frontend requests reach this service (default port `:3000`). The module has three responsibilities:

1. **Authentication and authorization**: verify JWT tokens and determine the caller's identity and permissions.
2. **Business logic**: operate on PostgreSQL through Prisma to manage users, knowledge bases, documents and conversations.
3. **Request forwarding**: AI-related requests (streaming chat, document processing) are passed through to `ai-engine`; this module contains no AI logic.

Module boundary: business rules stay in the gateway; AI logic stays in `ai-engine`. The two services trust each other via a shared `INTERNAL_API_TOKEN`.

---

## Directory Structure

```
api-gateway/
├── src/
│   ├── server.ts                    # Entry: load config and listen
│   ├── app.ts                       # Assemble Fastify: register plugins and routes
│   ├── middleware/
│   │   └── auth.middleware.ts       # authenticate / requireAdmin guards
│   ├── proxy/
│   │   └── ai-proxy.ts              # Forward to AI engine (SSE stream + sync)
│   └── routes/
│       ├── auth.routes.ts           # register / login / current user
│       ├── knowledge-base.routes.ts # knowledge base CRUD
│       ├── document.routes.ts       # file upload / status / delete
│       ├── conversation.routes.ts   # conversation CRUD + streaming chat
│       └── dashboard.routes.ts      # statistics and trends
├── prisma/
│   └── schema.prisma                # Data models (5 business tables)
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

---

## Authentication and Authorization

### JWT flow

- Registration and login (`auth.routes.ts`): passwords are hashed with `bcrypt` (10 rounds) before storage; a JWT with a default 7-day TTL is issued upon successful verification.
- Route guards (`auth.middleware.ts`): `authenticate` verifies the token; `requireAdmin` adds a role check. All routes except `/api/auth/register` and `/api/auth/login` are guarded.

### Role model

| Role | Data visibility |
|------|-----------------|
| `admin` | All knowledge bases, documents and conversations |
| `user` | Only resources they created |

Implementation: admin queries carry no filter; regular user queries carry a `where: { userId }` condition.

---

## AI Proxy

`proxy/ai-proxy.ts` provides two forwarding modes:

### SSE streaming proxy (`proxyChatStream`)

Used for chat: forwards the Python engine's answer to the frontend token by token.

- Uses `axios` with `responseType: 'stream'` to obtain a readable stream from the Python engine.
- Writes directly to `reply.raw` (the underlying HTTP response), bypassing Fastify's serialization buffer.
- Sets the `X-Accel-Buffering: no` header to prevent reverse proxies (e.g. Nginx) from buffering the response.

### Synchronous proxy (`proxyToAI`)

Used for document processing, status queries and similar requests: forwards the request and waits for the result, with a 30-second timeout.

All forwarded requests carry the `X-Internal-Token` and `X-User-Id` headers.

---

## Data Model

`schema.prisma` defines 5 business tables:

```
User ──< KnowledgeBase ──< Document
                │
                └──< Conversation ──< Message
```

| Table | Key fields | Notes |
|-------|-----------|-------|
| `users` | email, passwordHash, role | Users and roles |
| `knowledge_bases` | embeddingModel, chunkStrategy, retrievalConfig | Chunking and retrieval config stored as JSON, customizable per knowledge base |
| `documents` | status, chunkCount | State machine: pending -> processing -> done / failed |
| `conversations` | systemPrompt, modelConfig | Each conversation binds to one knowledge base |
| `messages` | role, citations, tokenUsage | citations store sources for frontend display |

The vector table `chunks` is not managed by Prisma (Prisma does not support the vector type); it is created via raw SQL in `scripts/init_pgvector.sql`. When deleting a document, the gateway first asks the AI engine to delete vectors, then removes the business record.

---

## API Endpoints

| Method | Path | Description | Auth required |
|--------|------|-------------|---------------|
| `POST` | `/api/auth/register` | Register | No |
| `POST` | `/api/auth/login` | Login | No |
| `GET` | `/api/auth/me` | Current user | Yes |
| `POST` | `/api/knowledge-bases` | Create knowledge base | Yes |
| `GET` | `/api/knowledge-bases` | List knowledge bases | Yes |
| `GET` | `/api/knowledge-bases/:id` | Detail (with documents) | Yes |
| `PUT` | `/api/knowledge-bases/:id` | Update knowledge base | Yes |
| `DELETE` | `/api/knowledge-bases/:id` | Delete (cascade) | Yes |
| `POST` | `/api/documents/upload/:knowledgeBaseId` | Upload document | Yes |
| `GET` | `/api/documents/knowledge-base/:kbId` | List documents | Yes |
| `GET` | `/api/documents/:id/status` | Processing status (polled) | Yes |
| `DELETE` | `/api/documents/:id` | Delete document and vectors | Yes |
| `POST` | `/api/conversations` | Create conversation | Yes |
| `GET` | `/api/conversations` | List conversations | Yes |
| `GET` | `/api/conversations/:id` | Detail (with message history) | Yes |
| `PUT` | `/api/conversations/:id` | Update settings | Yes |
| `DELETE` | `/api/conversations/:id` | Delete conversation | Yes |
| `POST` | `/api/conversations/stream` | Streaming chat (SSE) | Yes |
| `GET` | `/api/dashboard/stats` | Stat cards | Yes |
| `GET` | `/api/dashboard/trends` | Conversation trends | Yes |
| `GET` | `/api/health` | Health check | No |

---

## Configuration

Configuration is loaded from `.env` (see the `.env.example` template):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://kb_user:kb_pass@localhost:5432/knowledge_base` | Database connection string |
| `JWT_SECRET` | none | Required; must be changed in production |
| `JWT_EXPIRES_IN` | `7d` | Token TTL |
| `AI_ENGINE_URL` | `http://localhost:8000` | Python engine URL |
| `INTERNAL_API_TOKEN` | none | Required; must match ai-engine's |
| `UPLOAD_DIR` | `./uploads` | Upload storage directory |
| `PORT` | `3000` | Listen port |

---

## Running Locally

```bash
cp .env.example .env
pnpm install
pnpm db:generate     # generate Prisma Client
pnpm db:migrate      # create / migrate tables
pnpm dev             # runs on :3000 (tsx watch hot reload)
```

Health check:

```bash
curl http://localhost:3000/api/health
```

---

## Extension Guide

### Add a new route module

1. Create `xxx.routes.ts` under `src/routes/`, exporting `async function xxxRoutes(app: FastifyInstance)`.
2. For auth protection, call `app.addHook('preHandler', authenticate)` inside the function.
3. Register it in `app.ts`: `app.register(xxxRoutes, { prefix: '/api/xxx' })`.

### Modify the data model

1. Edit `prisma/schema.prisma`.
2. Run `pnpm db:migrate` to generate and apply migrations.
3. Run `pnpm db:generate` to regenerate the type-safe Client.

### Add a feature that depends on AI

- Synchronous call: `await proxyToAI('/ai/xxx', body)`.
- Streaming call: follow the `proxyChatStream` implementation — request the Python engine with `responseType: 'stream'` and write each chunk to `reply.raw`.
