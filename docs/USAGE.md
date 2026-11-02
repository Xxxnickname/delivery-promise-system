# 详细用法

本文按“先看界面，再跑后端，最后做真实导入”的顺序说明。只想看页面效果，读到第 2 节即可；要验证计算和导出，从第 3 节开始。

## 1. 先确认你要用哪一种模式

| 模式 | 启动方式 | 数据来源 | 适合谁 |
|---|---|---|---|
| 静态 mock 演示 | `python -m http.server 8003 --directory app\static` | `app/static/mock/*.json` | 产品演示、页面评审、截图 |
| 后端 API | `uvicorn app.main:app --port 8003` | SQLite/PostgreSQL、真实导入 | 验证导入、BOM、承诺、模拟、导出 |
| Docker Compose | `docker compose up -d --build` | PostgreSQL + Redis + app + worker | 部署演练 |

重要：静态页面的 `app/static/js/api.js` 中 `MOCK=true`。即使后端已启动，首页仍然展示 mock 数据；真实接口请通过 `/docs` 或 `curl` 调用。

## 2. 静态 mock 演示怎么点

### 2.1 启动

```powershell
cd delivery-promise-system
python -m http.server 8003 --directory app\static
```

打开 <http://127.0.0.1:8003/>。

### 2.2 登录

演示账号：

| 账号 | 角色 | 首页 |
|---|---|---|
| `sales01` | 销售 | 我的订单 |
| `planner01` | 计划 | 数据导入 |
| `supervisor01` | 主管 | 交付驾驶舱 |
| `admin` | 管理员 | 用户管理 |

静态 mock 密码：任意非空。页面会读取 `app/static/mock/users.json` 校验账号是否存在、状态是否启用。

### 2.3 推荐走查路径

1. 用 `supervisor01` 登录，看交付驾驶舱的延期订单、缺料汇总、本周关键缺料；
2. 点“缺料台账”，按风险/影响订单筛选；
3. 点一行物料，打开缺口追溯抽屉，查看受影响订单、BOM 路径、在途 ETA、供给时间轴；
4. 点订单号进入订单详情，查看承诺、缺口、延期天数；
5. 进入“场景模拟”，切换插单/加急，查看影响订单；
6. 进入“快照对比”，查看延后标红、提前标绿；
7. 切到 `sales01`，确认只看到授权客户订单；
8. 切到 `planner01`，看数据导入、库存总览、基础数据；
9. 切到 `admin`，看用户管理与角色菜单。

### 2.4 四态演示

页面支持 `ready / loading / empty / error` 四种状态。地址栏加 `?state=loading`、`?state=empty`、`?state=error` 可切换；侧边栏也有状态下拉框。用于评审空态、加载态和错误态。

### 2.5 深链接

- 订单详情：`#/order/SO202601004`
- 缺料台账：`#/shortages`
- 指定物料缺口：`#/shortages/RM-033`
- 库存总览：`#/inventory`
- 退货库存：`#/inventory/returns`
- 场景模拟：`#/simulate`
- 数据导入：`#/import`
- 快照对比：`#/compare`
- 基础数据：`#/master`
- 用户管理：`#/users`

直接输入无权限的地址会显示“当前角色无权访问”，不会绕过前端角色控制。

## 3. 后端 API 怎么跑

### 3.1 安装与启动

```powershell
cd delivery-promise-system
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

检查：

```powershell
curl.exe http://127.0.0.1:8003/health
curl.exe http://127.0.0.1:8003/api/llm/status
```

`/health` 返回 `status=ok`、端口、版本、时区。`/api/llm/status` 返回模型名、地址、是否启用、Key 是否配置，不返回 Key。

### 3.2 登录拿 JWT

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/auth/login -H "Content-Type: application/json" -d '{"account":"planner01","password":"demo123"}'
```

返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user": {"account": "planner01", "role": "planner"}
  },
  "trace_id": "tr_xxx"
}
```

后续请求加：

```http
Authorization: Bearer <access_token>
```

### 3.3 下载模板

```powershell
curl.exe -OJ http://127.0.0.1:8003/api/templates/orders -H "Authorization: Bearer <access_token>"
curl.exe -OJ http://127.0.0.1:8003/api/templates/bom -H "Authorization: Bearer <access_token>"
curl.exe -OJ http://127.0.0.1:8003/api/templates/inventory -H "Authorization: Bearer <access_token>"
curl.exe -OJ http://127.0.0.1:8003/api/templates/in_transit -H "Authorization: Bearer <access_token>"
```

模板是 UTF-8 BOM CSV，可以直接用 Excel 打开编辑，保存为 CSV。

### 3.4 导入四表

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/imports/bundle -H "Authorization: Bearer <access_token>" -F "orders=@samples/03/orders.csv" -F "bom=@samples/03/bom.csv" -F "inventory=@samples/03/inventory.csv" -F "in_transit=@samples/03/in_transit.csv" -F "mode=ALL_OR_NOTHING"
```

默认全或无。返回里重点关注：

- `batch_id`：后续查询/模拟/导出使用；
- `status`：`COMMITTED`、`ROLLED_BACK`、`PARTIAL_IMPORTED`；
- `imported_rows`：实际导入行数；
- `tables`：每张表的有效行/错误行；
- `file_hash`：内容哈希，用于幂等。

部分导入：

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/imports/bundle -H "Authorization: Bearer <access_token>" -F "orders=@samples/03/sample_error_orders.csv" -F "bom=@samples/03/bom.csv" -F "inventory=@samples/03/inventory.csv" -F "in_transit=@samples/03/in_transit.csv" -F "mode=PARTIAL_WITH_AUDIT" -F "allow_partial=true"
```

### 3.5 查批次与错误

```powershell
curl.exe "http://127.0.0.1:8003/api/imports/<batch_id>?include_records=true" -H "Authorization: Bearer <access_token>"
curl.exe -OJ "http://127.0.0.1:8003/api/imports/<batch_id>/errors.csv" -H "Authorization: Bearer <access_token>"
```

错误 CSV 固定列：`row_no,column,value,reason`。

### 3.6 查订单承诺

```powershell
curl.exe "http://127.0.0.1:8003/api/orders?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
curl.exe "http://127.0.0.1:8003/api/orders/SO202601004/promise?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
curl.exe "http://127.0.0.1:8003/api/orders/SO202601004/explain?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
```

`/explain` 返回确定性模板文案，不调用模型，不生成新数字。

### 3.7 模拟插单/加急

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/simulate -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{"order_no":"SO202601004","mode":"insert","qty":"50","expect_date":"2026-11-08","batch_id":"<batch_id>"}'
```

`mode=insert` 插入模拟订单；`mode=rush` 调整目标订单交期。结果包含 `not_persisted=true`。

### 3.8 快照与对比

```powershell
curl.exe -X POST "http://127.0.0.1:8003/api/snapshots?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
curl.exe "http://127.0.0.1:8003/api/snapshots/compare?from=<snap_a>&to=<snap_b>" -H "Authorization: Bearer <access_token>"
```

快照按订单号对齐，返回延后/提前/新增/消失等差异项。

### 3.9 导出 xlsx

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/export -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{"kind":"kit_report","batch_id":"<batch_id>"}'
curl.exe "http://127.0.0.1:8003/api/export/<task_id>" -H "Authorization: Bearer <access_token>"
curl.exe -OJ "http://127.0.0.1:8003/api/export/<task_id>/download" -H "Authorization: Bearer <access_token>"
```

`kind` 支持 `kit_report` 和 `snapshot_diff`。同一登录账号同时只允许一个未完成任务，超出返回 429；未登录开发模式用 `X-User-Id` 区分归属。

## 4. 四张表准备细节

### 4.1 订单表

```csv
order_no,item_code,qty,due_date,customer
SO202601004,FG-500,100,2026-11-10,华东智造
```

### 4.2 BOM 表

```csv
parent_code,child_code,qty_per,scrap_rate,substitute_group,level
FG-500,SUB-120,1,0.02,SG-120,1
SUB-120,RM-033,2,0,,
```

### 4.3 库存表

```csv
item_code,on_hand,allocated,warehouse
RM-033,1200,0,原料仓
```

### 4.4 在途表

```csv
item_code,qty,eta_date,batch_no,supplier
RM-033,44812.92,2026-11-16,PO-2026-118,华东供应商
```

注意：

- 日期严格 `YYYY-MM-DD`；
- 数量不要带千分位逗号；
- 编码统一 UTF-8；
- 同一料号在库存表多行会累加可用量；
- 同一物料在途多批会按 ETA 顺序消耗；
- `allocated` 不能大于 `on_hand`；
- BOM 环、超过 5 层会被拒绝，不会静默截断。

## 5. 角色场景

### 5.1 销售：我现在最关心什么

1. 登录后看“我的订单”；
2. 按订单号/客户/成品搜索；
3. 看 `can_commit`、`kit_date`、`delay_days`；
4. 点订单详情看缺口和影响物料；
5. 需要插单/加急时进入场景模拟，先看对已有订单的影响。

当前边界：静态 mock 会按 `customer_scopes` 过滤；真实后端订单接口尚未强制客户范围。

### 5.2 计划员：数据怎么进来

1. 从 ERP 导出四张表；
2. 按模板整理表头；
3. 用 `/api/imports/bundle` 导入；
4. 下载错误 CSV，按行号修正；
5. 重新导入，拿到新的 `batch_id`；
6. 用 `/api/orders` 检查承诺结果；
7. 采购到货后更新在途/库存，重复导入。

### 5.3 主管：缺口怎么追

1. 打开驾驶舱，看延期订单和高风险物料；
2. 进入缺料台账，按影响订单数排序；
3. 打开缺口抽屉，看受影响订单、BOM 路径、在途 ETA；
4. 决定催料、顺延或插单；
5. 用场景模拟验证插单影响；
6. 用快照对比记录调整前后差异；
7. 导出缺口表，线下交采购。

### 5.4 采购：本期怎么协同

本期没有采购登录账号。推荐流程：

1. 主管导出缺口表（当前可由 `/api/export` 的 `kit_report` 或页面导出按钮生成）；
2. 线下发给采购；
3. 采购反馈交期/数量；
4. 计划员把到货批次写入 `in_transit.csv`；
5. 到货后更新 `inventory.csv` 的 `on_hand`；
6. 重新导入并复算。

后续可扩展：采购账号、询价单、到货质检、退货入库、供应商交期确认。

## 6. 常见错误与处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 401 未登录 | 未带 Bearer token，或 `AUTH_REQUIRED=true` | 调 `/api/auth/login`，带 `Authorization` |
| 403 当前角色无权 | 用了非计划/管理员账号调导入接口 | 换 `planner01` 或 `admin` |
| 导入 `ROLLED_BACK` | 任一行校验失败 | 下载 `errors.csv`，按行号修正 |
| BOM 环 | 父子关系形成循环 | 按返回的 `path` 修复 BOM |
| BOM 超层 | 超过 5 层 | 调整 BOM 层级，不在代码中截断 |
| 订单无结果 | 没有已提交批次/订单号不存在 | 先导入，或检查 `batch_id`/订单号 |
| 429 导出 | 同一账号有未完成任务 | 轮询完成后再发起 |
| 页面仍是 mock | `MOCK=true` | 用 `/docs` 调真实 API，或后续接前端适配层 |

## 7. 重置本地演示数据

本地默认数据库是项目根目录 `plan.db`。如果要恢复初始样例：

```powershell
# 先停止 uvicorn
Remove-Item .\plan.db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

启动时 `bootstrap_demo_batch()` 会从 `samples/03` 自动导入一份演示批次；`seed_demo_users()` 会从 `app/static/mock/users.json` 初始化演示账号。

> 生产环境不要依赖“删库自动重建”；正式数据必须走迁移、备份和恢复流程。

## 8. 部署后怎么验证

1. `curl /health` 返回 200；
2. `curl /api/llm/status` 返回模型名和 `api_key_configured`；
3. 登录拿 token；
4. 导入一次四表；
5. 查询一张订单承诺；
6. 创建一次快照并比较；
7. 创建一次 xlsx 导出并下载；
8. 查看日志是否有异常和 `trace_id`。

## 9. 相关文档

- [README](../README.md)
- [API 说明](API.md)
- [架构设计](ARCHITECTURE.md)
- [数据模型](DATA_MODEL.md)
- [部署说明](DEPLOYMENT.md)
- [运维手册](operations.md)
- [测试与验收](TESTING.md)
- [当前边界](LIMITATIONS.md)