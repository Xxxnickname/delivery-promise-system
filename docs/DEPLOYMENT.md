# 部署说明

## 1. 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

## 2. Docker Compose

```powershell
Copy-Item .env.example .env
# 修改 AUTH_SECRET、MODEL_API_KEY、数据库密码
docker compose up -d --build
docker compose ps
```

服务：

- `app`：FastAPI，宿主端口 8003
- `postgres`：PostgreSQL 16，不映射宿主端口
- `redis`：Redis 7，不映射宿主端口
- `worker`：Celery worker

## 3. 生产环境变量

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

## 4. Nginx

参考：`deploy/nginx.conf.example`

要求：

- HTTPS
- `client_max_body_size` ≥ 上传上限
- 只代理 app 的 8003
- 不暴露 PostgreSQL/Redis
- 访问日志不记录 Authorization 头

## 5. 健康检查

```bash
curl -fsS http://127.0.0.1:8003/health
curl -fsS http://127.0.0.1:8003/api/llm/status
```

## 6. 备份与恢复

```bash
docker compose exec -T postgres pg_dump -U plan -d plan > backup-plan.sql
```

恢复前先备份当前库，再执行：

```bash
Get-Content backup-plan.sql | docker compose exec -T postgres psql -U plan -d plan
```

## 7. 发布回滚

1. 记录当前镜像/commit；
2. 执行发布；
3. 验证 `/health`、登录、一次导入、一次查询、一次导出；
4. 失败时回滚镜像，必要时用数据库备份恢复；
5. 发布前后各保留一份日志和 trace_id。

## 8. 生产前仍需完成

- 前端从 mock 切真实 API
- PostgreSQL 实跑与迁移核对
- Redis/Celery 实际 worker 验证
- Nginx/TLS 配置
- 监控、告警、备份演练
- 20 并发与故障注入测试
