# 部署说明

## 1. 本地静态预览

只看界面时不需要 Python 依赖和数据库：

```powershell
python -m http.server 8003 --directory app\static
```

打开 <http://127.0.0.1:8003/>。数据来自 `app/static/mock`，登录密码任意非空。

## 2. 本地后端开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

访问：

- 首页：<http://127.0.0.1:8003/>
- Swagger：<http://127.0.0.1:8003/docs>
- 健康检查：<http://127.0.0.1:8003/health>

注意：首页仍是 `MOCK=true` 的静态前端；真实 API 通过 `/docs` 或 `curl` 调用。

## 3. Docker Compose

```powershell
Copy-Item .env.example .env
# 修改 AUTH_SECRET、MODEL_API_KEY、数据库密码
docker compose up -d --build
docker compose ps
```

服务：

| 服务 | 镜像/构建 | 说明 |
|---|---|---|
| `app` | `Dockerfile`，Python 3.11-slim | FastAPI + 静态前端，宿主端口 8003 |
| `postgres` | `postgres:16` | 目标数据库，不映射宿主端口 |
| `redis` | `redis:7-alpine` | 队列 broker/backend，不映射宿主端口 |
| `worker` | 同一镜像 | Celery worker 骨架 |

- Compose 工程名固定为 `plan`；
- 应用端口固定为 `8003`；
- `app` 和 `worker` 通过 `env_file: .env` 读取配置；
- 没有 `.env` 时 `docker compose` 会因 `env_file` 缺失而失败，所以必须先复制 `.env.example`。

## 4. 生产环境变量

```env
APP_ENV=production
APP_PORT=8003
DB_DSN=postgresql://plan:plan@postgres:5432/plan
REDIS_URL=redis://redis:6379/0
AUTH_REQUIRED=true
AUTH_SECRET=<至少32字节随机值>
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
MODEL_API_KEY=<服务器注入>
LLM_ENABLED=true
```

说明：

- `MODEL_API_KEY` 只放服务器环境变量或 `.env`，不要提交 Git；
- `AUTH_SECRET` 至少 32 字节；
- `AUTH_REQUIRED=true` 生产必须开启；
- `LLM_ENABLED=false` 时系统只用规则表头映射，仍可正常运行；
- `APP_PORT` 只用于健康检查和文档展示，uvicorn 启动命令仍固定 8003。

## 5. Nginx

参考：`deploy/nginx.conf.example`

要求：

- HTTPS；
- `client_max_body_size` ≥ 上传上限（默认 20 MB）；
- 只代理 app 的 8003；
- 不暴露 PostgreSQL/Redis；
- 访问日志不记录 `Authorization`；
- 透传 `X-Trace-Id`，或在入口生成。

## 6. 健康检查

```bash
curl -fsS http://127.0.0.1:8003/health
curl -fsS http://127.0.0.1:8003/api/llm/status
```

`/health` 返回服务名、版本、端口、时区、时间戳；`/api/llm/status` 不返回 Key。

## 7. 备份与恢复

PostgreSQL：

```bash
docker compose exec -T postgres pg_dump -U plan -d plan > backup-plan.sql
```

恢复前先备份当前库，再执行：

```bash
Get-Content backup-plan.sql | docker compose exec -T postgres psql -U plan -d plan
```

SQLite 本地：

```powershell
Copy-Item .\plan.db .\plan.db.bak
```

注意：`plan.db`、`reports/`、`reports/exports/`、日志是生产运行产物，不应提交 Git；文档、测试、样例和截图是项目资产，不应删除。

## 8. 发布回滚

1. 记录当前镜像/commit；
2. 执行发布；
3. 验证 `/health`、登录、一次导入、一次查询、一次快照、一次导出；
4. 失败时回滚镜像/代码；
5. 数据库迁移不兼容时用备份恢复；
6. 发布前后各保留一份日志和 `trace_id`。

## 9. 生产前仍需完成

- 前端从 mock 切真实 API；
- PostgreSQL 实跑与迁移核对；
- Redis/Celery 实际 worker 验证；
- Nginx/TLS 配置；
- 监控、告警、备份演练；
- 20 并发与故障注入测试；
- 客户范围过滤、租户绑定、审计落库；
- 替代料计划接入订单承诺主链路。