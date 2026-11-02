# 运维手册

## 启动与停止

本地：
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```
Docker：
```powershell
docker compose up -d --build
docker compose ps
```

停止：
```powershell
docker compose down
```
本项目 compose 工程名固定为 `plan`，端口固定 `8003`。

## 健康与监控

- `/health` 必须返回 200。
- 单次计算目标 ≤5 秒；1000 行订单自动化测试已覆盖。
- 导入失败时检查 `/api/imports/{batch_id}/errors.csv`。
- 导出任务同时每用户最多 1 个；出现 429 时等待当前任务完成。
- 重点关注：导入失败行数、计算耗时、导出失败率、ETA 未确认数。

## 备份

PostgreSQL 上线后使用：
```powershell
docker compose exec -T postgres pg_dump -U plan -d plan > backup-plan.sql
```
恢复：
```powershell
Get-Content backup-plan.sql | docker compose exec -T postgres psql -U plan -d plan
```
当前 G4 演示批次在进程内存，重启后由 `samples/03` 自动重建；正式数据接入 PostgreSQL 后不得依赖此行为。

## 回滚

1. 先停止应用：`docker compose stop app worker`
2. 回滚镜像/代码到上一个发布标签
3. 如数据库迁移不兼容，使用备份恢复
4. 重新启动并检查 `/health`、一次导入、一次订单查询、一次 xlsx 导出

## 失败处理

- 导入错误：下载错误 CSV，按行号修正后重新上传。
- BOM 循环：根据接口返回的 path 修复父子关系。
- 超过 5 层：补充 BOM 层级或调整主数据，不在代码中截断。
- 交期计算异常：先核对导入批次哈希、calc_version 和黄金基准报告。
