# Frontend · Vue 3 前端

Frontend 是用户直接交互的单页应用，提供登录、知识库管理、文档上传、流式对话与数据仪表盘功能。

返回 [项目主 README](../README.md) · [English Version](#english-version)

---

## 模块定位

本应用运行于浏览器中，通过 HTTP 调用 `api-gateway`。开发环境下，Vite 开发服务器将 `/api` 请求代理至 `:3000`，因此前端代码中不包含任何后端地址硬编码。

---

## 目录结构

```
frontend/
├── src/
│   ├── main.ts                      # 应用入口：挂载 Pinia / Router / ElementPlus
│   ├── App.vue                      # 根组件（仅包含 <router-view />）
│   ├── router/
│   │   └── index.ts                 # 路由定义 + 登录守卫
│   ├── stores/
│   │   └── auth.ts                  # 认证状态（token / user / login / logout）
│   ├── api/
│   │   ├── client.ts                # axios 实例：自动附加 JWT、统一错误处理
│   │   └── chatStream.ts            # SSE 流式对话（fetch + ReadableStream）
│   ├── components/
│   │   └── layout/
│   │       └── AppLayout.vue        # 登录后布局：侧边栏 + 顶栏
│   ├── views/                       # 页面级组件（一个文件对应一个页面）
│   │   ├── Login.vue                # 登录 / 注册
│   │   ├── Dashboard.vue            # 仪表盘
│   │   ├── KnowledgeBases.vue       # 知识库列表
│   │   ├── KnowledgeBaseDetail.vue  # 知识库详情 + 文档上传
│   │   ├── Conversations.vue        # 对话列表
│   │   └── Chat.vue                 # 流式对话界面
│   └── env.d.ts
├── public/                          # 静态资源（favicon、图标）
├── index.html
├── vite.config.ts                   # Vite 配置：@ 别名 + 开发代理
├── package.json
└── README.md
```

---

## 技术选型

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| Vue 3（Composition API） | 前端框架 | `<script setup>` 语法简洁，学习曲线平缓 |
| Vite | 构建工具 | 启动与热更新速度快，开发体验良好 |
| TypeScript | 类型系统 | 降低运行时错误 |
| Pinia | 状态管理 | Vue 3 官方推荐，API 较 Vuex 更简洁 |
| Vue Router | 路由 | 支持路由守卫，便于实现登录拦截 |
| Element Plus | UI 组件库 | 表格、表单、上传、对话框等组件完善，适合管理类界面 |
| markdown-it + highlight.js | AI 回复渲染 | 支持 Markdown 与代码高亮 |

---

## 认证与路由守卫

### 登录流程（`stores/auth.ts`）

登录成功后，`token` 与 `user` 同时写入 Pinia 状态与 `localStorage`，刷新页面后可自动恢复会话；退出登录时清空两处存储。

### 路由守卫（`router/index.ts`）

```ts
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.token) next('/login');
  else next();
});
```

除 `/login` 外，所有页面均位于 `AppLayout` 布局之下（标记 `requiresAuth`）。访问受保护页面且无有效令牌时，自动重定向至登录页。

---

## API 层设计

### 常规请求（`api/client.ts`）

全局 `axios` 实例配合两个拦截器：

- 请求拦截器：自动附加 `Authorization: Bearer <token>` 请求头，业务代码无需关心认证细节。
- 响应拦截器：收到 401 时自动登出并重定向至登录页；其余错误统一以 `ElMessage` 提示。各页面只需编写成功逻辑，错误处理集中收敛。

### 流式对话（`api/chatStream.ts`）

该模块使用 `fetch` 而非浏览器原生的 `EventSource`。原因是 `EventSource` 仅支持 GET 请求，而对话接口需要以 POST 提交消息体。

实现方式：`fetch` 获取响应体的可读流（ReadableStream），通过 `reader` 逐块读取，按行解析 SSE 协议（`event:` 与 `data:` 行），再通过回调函数（`onToken`、`onCitations`、`onDone`、`onError`）通知页面。`buffer` 变量用于拼接跨数据块的不完整行。

---

## 页面清单

| 路由 | 页面文件 | 说明 |
|------|----------|------|
| `/login` | `Login.vue` | 登录与注册切换 |
| `/` | `Dashboard.vue` | 统计卡片与近 30 天对话趋势 |
| `/knowledge-bases` | `KnowledgeBases.vue` | 知识库列表、创建、删除 |
| `/knowledge-bases/:id` | `KnowledgeBaseDetail.vue` | 文档列表、上传、配置展示、发起对话 |
| `/conversations` | `Conversations.vue` | 对话列表 |
| `/conversations/:id` | `Chat.vue` | 流式对话、引用来源折叠展示 |

`Chat.vue` 是交互最复杂的页面，需要关注以下实现：

- 消息分为"已完成"与"流式输出中"两种渲染状态。
- AI 回复经 markdown-it 渲染（禁用原始 HTML 以防范 XSS，启用自动链接与换行）。
- 每条助手消息下方可展开引用来源，展示文档名、相似度与内容片段。
- 新消息到达时自动滚动至底部。

---

## 开发配置（`vite.config.ts`）

```ts
server: {
  port: 5173,
  proxy: {
    '/api': 'http://localhost:3000',       // 常规 API 请求
    '/ai-stream': 'http://localhost:3000', // 预留的流式端点
  },
}
```

`@` 为 `src/` 目录别名（例如 `import client from '@/api/client'`），在 `vite.config.ts` 与 `tsconfig.json` 中均有配置，修改时须保持两处一致。

---

## 本地运行

```bash
pnpm install
pnpm dev        # 启动于 :5173，自动代理 /api 至 :3000
```

前置条件：`api-gateway` 已在 `:3000` 运行。

生产构建：`pnpm build`。该命令先执行 `vue-tsc` 类型检查，再由 Vite 打包输出至 `dist/`。

---

## 扩展指南

### 新增页面

1. 在 `src/views/` 下创建 `MyPage.vue`。
2. 在 `router/index.ts` 的 `AppLayout` children 数组中添加路由条目（即可获得侧边栏布局）。
3. 如需侧边栏入口，在 `AppLayout.vue` 的 `<el-menu>` 中添加对应的 `<el-menu-item>`。

### 调用后端接口

```ts
import client from '@/api/client';

// 无需手动附加 token，错误已统一处理
const list = await client.get('/knowledge-bases');
await client.post('/knowledge-bases', { name: '新知识库' });
```

### 新增全局状态

在 `src/stores/` 下新建 `defineStore`，写法参照 `auth.ts`（Composition API 风格）。

### 组件规范

- 页面级组件置于 `views/`，可复用组件置于 `components/`。
- 统一使用 `<script setup lang="ts">` 语法。
- 优先使用 Element Plus 组件，避免重复实现。

---

<a id="english-version"></a>

# Frontend · Vue 3 Application

The Frontend is the user-facing single-page application, providing login, knowledge base management, document uploads, streaming chat and an analytics dashboard.

Back to [main README](../README.md)

---

## Module Purpose

The application runs in the browser and calls `api-gateway` over HTTP. In development, the Vite dev server proxies `/api` requests to `:3000`, so no backend URLs are hardcoded in the frontend.

---

## Directory Structure

```
frontend/
├── src/
│   ├── main.ts                      # Entry: mount Pinia / Router / ElementPlus
│   ├── App.vue                      # Root component (only <router-view />)
│   ├── router/
│   │   └── index.ts                 # Route definitions + auth guard
│   ├── stores/
│   │   └── auth.ts                  # Auth state (token / user / login / logout)
│   ├── api/
│   │   ├── client.ts                # axios instance: auto JWT + unified errors
│   │   └── chatStream.ts            # SSE streaming chat (fetch + ReadableStream)
│   ├── components/
│   │   └── layout/
│   │       └── AppLayout.vue        # Post-login layout: sidebar + header
│   ├── views/                       # Page components (one file per page)
│   │   ├── Login.vue                # Login / register
│   │   ├── Dashboard.vue            # Dashboard
│   │   ├── KnowledgeBases.vue       # Knowledge base list
│   │   ├── KnowledgeBaseDetail.vue  # KB detail + document upload
│   │   ├── Conversations.vue        # Conversation list
│   │   └── Chat.vue                 # Streaming chat UI
│   └── env.d.ts
├── public/                          # Static assets (favicon, icons)
├── index.html
├── vite.config.ts                   # Vite config: @ alias + dev proxy
├── package.json
└── README.md
```

---

## Tech Choices

| Technology | Purpose | Rationale |
|------------|---------|-----------|
| Vue 3 (Composition API) | Framework | Clean `<script setup>` syntax, gentle learning curve |
| Vite | Build tool | Fast startup and hot module replacement |
| TypeScript | Type system | Fewer runtime errors |
| Pinia | State management | Official Vue 3 recommendation, simpler API than Vuex |
| Vue Router | Routing | Route guards enable login interception |
| Element Plus | UI library | Complete table, form, upload and dialog components, suited to admin interfaces |
| markdown-it + highlight.js | AI reply rendering | Markdown and code highlighting support |

---

## Authentication and Route Guards

### Login flow (`stores/auth.ts`)

On successful login, `token` and `user` are written to both Pinia state and `localStorage`, so the session is restored after a page refresh. Logout clears both stores.

### Route guard (`router/index.ts`)

```ts
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.token) next('/login');
  else next();
});
```

All pages except `/login` live under the `AppLayout` layout (marked `requiresAuth`). Accessing a protected page without a valid token redirects to the login page.

---

## API Layer Design

### Regular requests (`api/client.ts`)

A global `axios` instance with two interceptors:

- Request interceptor: automatically attaches the `Authorization: Bearer <token>` header; business code never handles auth manually.
- Response interceptor: a 401 triggers auto-logout and a redirect to login; all other errors surface as a unified `ElMessage` notification. Pages only implement success logic; error handling is centralized.

### Streaming chat (`api/chatStream.ts`)

This module uses `fetch` instead of the browser's native `EventSource`, because `EventSource` only supports GET requests while the chat endpoint requires POST with a message body.

Implementation: `fetch` returns a ReadableStream, consumed chunk by chunk via a `reader`; SSE protocol lines (`event:` and `data:`) are parsed manually, then dispatched through callbacks (`onToken`, `onCitations`, `onDone`, `onError`). A `buffer` variable stitches together lines split across chunks.

---

## Page Inventory

| Route | File | Description |
|-------|------|-------------|
| `/login` | `Login.vue` | Login and registration toggle |
| `/` | `Dashboard.vue` | Stat cards and 30-day conversation trend |
| `/knowledge-bases` | `KnowledgeBases.vue` | Knowledge base list, create, delete |
| `/knowledge-bases/:id` | `KnowledgeBaseDetail.vue` | Documents, upload, config display, start chat |
| `/conversations` | `Conversations.vue` | Conversation list |
| `/conversations/:id` | `Chat.vue` | Streaming chat with collapsible citations |

`Chat.vue` is the most interactive page. Key implementation details:

- Messages render in two states: completed and streaming.
- AI replies are rendered by markdown-it (raw HTML disabled to prevent XSS; autolink and line breaks enabled).
- Each assistant message has collapsible citations showing document name, similarity and content snippet.
- The view auto-scrolls to the bottom when new messages arrive.

---

## Development Configuration (`vite.config.ts`)

```ts
server: {
  port: 5173,
  proxy: {
    '/api': 'http://localhost:3000',       // regular API requests
    '/ai-stream': 'http://localhost:3000', // reserved streaming endpoint
  },
}
```

`@` is an alias for the `src/` directory (e.g. `import client from '@/api/client'`). It is configured in both `vite.config.ts` and `tsconfig.json`; keep the two in sync when making changes.

---

## Running Locally

```bash
pnpm install
pnpm dev        # runs on :5173, proxies /api to :3000
```

Prerequisite: `api-gateway` must be running on `:3000`.

Production build: `pnpm build`. The command runs a `vue-tsc` type check first, then bundles to `dist/`.

---

## Extension Guide

### Add a new page

1. Create `MyPage.vue` under `src/views/`.
2. Add a route entry to the `AppLayout` children array in `router/index.ts` (this provides the sidebar layout).
3. For a sidebar entry, add a corresponding `<el-menu-item>` to the `<el-menu>` in `AppLayout.vue`.

### Call backend APIs

```ts
import client from '@/api/client';

// No manual token handling needed; errors are handled centrally
const list = await client.get('/knowledge-bases');
await client.post('/knowledge-bases', { name: 'New KB' });
```

### Add global state

Create a new `defineStore` under `src/stores/`, following the `auth.ts` style (Composition API).

### Component conventions

- Page-level components go in `views/`; reusable components go in `components/`.
- Always use the `<script setup lang="ts">` syntax.
- Prefer Element Plus components over custom implementations.
