# Docker · 基础设施配置

通过 Docker Compose 一键启动项目依赖的中间件：PostgreSQL（含 pgvector 扩展）与 Redis。

返回 [项目主 README](../README.md) · [English Version](#english-version)

---

## 服务清单

| 容器名 | 镜像 | 端口 | 用途 |
|--------|------|------|------|
| `kb-postgres` | `pgvector/pgvector:pg16` | 5432 | 业务数据与向量存储 |
| `kb-redis` | `redis:7-alpine` | 6379 | 缓存与队列（当前预留，尚未使用） |

### 镜像选型说明

标准 PostgreSQL 镜像不包含 pgvector 扩展。本项目采用 `pgvector/pgvector` 官方镜像，其预装了 pgvector，免去手动编译扩展的步骤。这是"单一数据库同时承载业务数据与向量数据"架构方案的前提。

### 数据持久化

PostgreSQL 数据存储于命名卷 `pgdata`。`docker compose down` 不会清除数据；仅 `docker compose down -v` 会删除数据卷。

### 健康检查

两个服务均配置了 `healthcheck`，便于依赖它们的服务（或编排工具）在数据库就绪后再启动。

---

## 常用命令

```bash
# 启动（后台运行）
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f postgres

# 停止（保留数据）
docker compose down

# 停止并清除数据（慎用）
docker compose down -v

# 进入 PostgreSQL 命令行
docker exec -it kb-postgres psql -U kb_user -d knowledge_base
```

---

## 安全说明

`docker-compose.yml` 中的账号密码（`kb_user` / `kb_pass`）仅适用于本地开发环境。生产环境部署时应注意：

1. 凭据改用环境变量或密钥管理服务注入，不得硬编码在配置文件中。
2. 5432 与 6379 端口不得暴露至公网。

---

## 扩展指南

### 将应用服务容器化（生产部署）

当前开发模式下，网关与 AI 引擎直接在宿主机运行，便于调试。生产部署时可在 `docker-compose.yml` 中追加应用服务，示例如下：

```yaml
  api-gateway:
    build: ../api-gateway
    ports: ["3000:3000"]
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://kb_user:kb_pass@postgres:5432/knowledge_base
```

注意：容器之间互访时，`DATABASE_URL` 的主机名应填写服务名（如 `postgres`），而非 `localhost`。

### 新增中间件

在 `services` 下追加服务定义即可。建议为每个服务配置 `healthcheck`，并在依赖方服务中声明 `depends_on` 与 `condition: service_healthy`，确保启动顺序。

---

<a id="english-version"></a>

# Docker · Infrastructure Configuration

Starts the project's middleware with a single Docker Compose command: PostgreSQL (with the pgvector extension) and Redis.

Back to [main README](../README.md)

---

## Services

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `kb-postgres` | `pgvector/pgvector:pg16` | 5432 | Business data and vector storage |
| `kb-redis` | `redis:7-alpine` | 6379 | Cache and queue (reserved, currently unused) |

### Image selection

A standard PostgreSQL image does not include the pgvector extension. This project uses the official `pgvector/pgvector` image, which ships with pgvector pre-installed and avoids manual extension compilation. This is the prerequisite for the project's "single database for both business data and vectors" architecture.

### Data persistence

PostgreSQL data is stored in the named volume `pgdata`. `docker compose down` preserves the data; only `docker compose down -v` removes the volume.

### Health checks

Both services define a `healthcheck`, allowing dependent services (or orchestrators) to start only after the databases are ready.

---

## Common Commands

```bash
# Start (detached)
docker compose up -d

# Check status
docker compose ps

# Tail logs
docker compose logs -f postgres

# Stop (keeps data)
docker compose down

# Stop and remove data (use with caution)
docker compose down -v

# Open a PostgreSQL shell
docker exec -it kb-postgres psql -U kb_user -d knowledge_base
```

---

## Security Notes

The credentials in `docker-compose.yml` (`kb_user` / `kb_pass`) are intended for local development only. For production deployments:

1. Inject credentials via environment variables or a secrets manager; never hardcode them in configuration files.
2. Do not expose ports 5432 and 6379 to the public internet.

---

## Extension Guide

### Containerize the application services (production)

In the current development setup, the gateway and AI engine run directly on the host for easier debugging. For production, append application services to `docker-compose.yml`, for example:

```yaml
  api-gateway:
    build: ../api-gateway
    ports: ["3000:3000"]
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://kb_user:kb_pass@postgres:5432/knowledge_base
```

Note: for inter-container communication, the host in `DATABASE_URL` must be the service name (e.g. `postgres`), not `localhost`.

### Add new middleware

Append a service definition under `services`. It is recommended to configure a `healthcheck` for each service and declare `depends_on` with `condition: service_healthy` in dependent services to guarantee startup order.
