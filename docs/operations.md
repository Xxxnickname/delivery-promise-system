# 运维手册

## 1. 启动与停止

### 静态预览

```powershell
python -m http.server 8003 --directory app\static
```

### 本地后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

### Docker

```powershell
docker compose up -d --build
docker compose ps
docker compose down
```

Compose 工程名固定为 `plan`，应用端口固定为 `8003`。

## 2. 健康与监控

- `/health` 必须返回 200；
- `/api/llm/status` 检查模型名、地址、是否启用、Key 是否配置；
- 单次计算目标 ≤ 5 秒，1000 行订单自动化测试已覆盖；
- 导入失败时检查 `GET /api/imports/{batch_id}/errors.csv`；
- 导出任务同一登录账号（未登录开发模式用 `X-User-Id`）同时最多 1 个，429 表示有未完成任务；
- 重点关注：导入失败行数、计算耗时、导出失败率、ETA 未确认数、401/403/429 比例。

## 3. 数据生命周期

- 本地默认数据库：项目根目录 `plan.db`；
- 批次原始 CSV、状态、哈希保存在 `import_batches_v2`；
- 快照保存在 `calc_snapshots_v2`；
- 应用重启后会从 `import_batches_v2` 重新解析批次，不是纯内存数据；
- 没有已提交批次时，启动时从 `samples/03` 自动导入演示批次；
- 生产环境不要依赖“删库自动重建”，正式数据必须走迁移、备份和恢复。

## 4. 运行产物与清理

以下文件/目录是运行时产生的，不应提交 Git，也不应误删文档：

| 产物 | 说明 |
|---|---|
| `.env` | 本地/服务器环境变量，含密钥 |
| `plan.db` | SQLite 数据库 |
| `reports/` | 导出、验收报告 |
| `reports/exports/*.xlsx` | 导出文件 |
| `reports/uvicorn*.log` | 运行日志 |
| `__pycache__/`、`.pytest_cache/` | Python 缓存 |
| `*.pyc` | 字节码 |

文档、测试、样例、截图、迁移和部署文件属于项目资产，不要因为清理运行产物而删除。

## 5. 导入失败处理

1. 调 `GET /api/imports/{batch_id}` 看 `tables` 每张表的错误行；
2. 调 `GET /api/imports/{batch_id}/errors.csv` 下载 `row_no,column,value,reason`；
3. 按行号修正 CSV；
4. 重新导入，拿到新 `batch_id`；
5. 默认全或无；需要部分导入时显式 `mode=PARTIAL_WITH_AUDIT&allow_partial=true`。

## 6. 计算异常处理

- BOM 环：按接口返回 `path` 修复父子关系；
- 超过 5 层：调整 BOM 层级，不在代码中截断；
- 齐套日为 null：检查是否仍有 `gap_qty > 0`；
- `can_commit=false`：比较 `kit_date` 与 `due_date`；
- 交期异常：核对 `batch_id`、`file_hash`、`calc_version` 和 golden 报告；
- 供给异常：检查库存 `allocated` 是否超过 `on_hand`、在途 ETA 是否录入正确。

## 7. 导出与下载

- `POST /api/export` 创建任务；
- `GET /api/export/{task_id}` 轮询；
- `GET /api/export/{task_id}/download` 下载；
- 当前由 web 进程内线程池生成 xlsx；
- Celery 导出任务入口已建但未启用；
- 同一登录账号同时只允许一个未完成任务；
- 登录后任务归属优先取 JWT 账号，未登录开发模式才回退 `X-User-Id`。

## 8. 备份与恢复

PostgreSQL：

```powershell
docker compose exec -T postgres pg_dump -U plan -d plan > backup-plan.sql
Get-Content backup-plan.sql | docker compose exec -T postgres psql -U plan -d plan
```

SQLite：

```powershell
Copy-Item .\plan.db .\plan.db.bak
Copy-Item .\plan.db.bak .\plan.db
```

恢复前先停止应用，避免写入冲突。

## 9. 发布回滚

1. `docker compose stop app worker`；
2. 回滚镜像/代码到上一个发布标签；
3. 数据库迁移不兼容时使用备份恢复；
4. 重新启动；
5. 检查 `/health`、一次登录、一次导入、一次订单查询、一次快照、一次 xlsx 导出。

## 10. 故障排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 启动失败，提示缺少 `.env` | Docker Compose 使用 `env_file: .env` | `Copy-Item .env.example .env` |
| 401 | 未带 token 或 token 过期 | 重新登录；检查 `AUTH_REQUIRED` |
| 403 | 非计划/管理员调导入接口 | 换 `planner01`/`admin` |
| 页面仍是 mock | `MOCK=true` | 用 `/docs` 调真实 API |
| 429 | 导出任务未完成 | 轮询完成后再发起 |
| 健康检查失败 | 端口占用/启动异常 | 检查 8003 占用和 uvicorn 日志 |
| 导出文件不存在 | 任务未完成/失败 | 先轮询 `SUCCESS`，再下载 |