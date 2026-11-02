# API 说明

交互式 OpenAPI：启动应用后访问 `/docs`。静态规范：[openapi.json](openapi.json)。

## 1. 基础约定

- Base URL：`http://127.0.0.1:8003`
- API 前缀：`/api`
- 所有响应使用统一结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "trace_id": "tr_xxx"
}
```

- 成功：`code=0`
- 失败：`code` 非 0，`data` 中放行号、列、原值、订单号等可定位信息
- 所有数量/金额字段以字符串传输，避免 JavaScript `float` 精度漂移
- 响应头回传 `X-Trace-Id`

### 1.1 请求头

| 请求头 | 是否必填 | 说明 |
|---|---|---|
| `Authorization` | 生产必填 | `Bearer <JWT>` |
| `X-Tenant-Id` | 否 | 租户标识，默认 `demo`；当前未与 JWT 强绑定 |
| `X-Trace-Id` | 否 | 调用方链路 ID；未传则服务端生成 |
| `X-User-Id` | 导出接口可选 | 未登录开发模式下的任务归属，默认 `demo`；登录后优先使用 JWT 账号 |

### 1.2 错误码

| code | 含义 | 常见 HTTP |
|---|---|---|
| `0` | 成功 | 200 |
| `1001` | 参数/CSV 校验失败 | 400/422 |
| `1002` | 资源不存在 | 404 |
| `1003` | 导入回滚 | 400 |
| `1004` | 重复数据 | 409 |
| `1101` | BOM 环 | 400 |
| `1102` | BOM 超层 | 400 |
| `1103` | BOM 非法 | 400 |
| `401` | 未登录/登录失效 | 401 |
| `403` | 角色无权 | 403 |
| `429` | 导出任务冲突 | 429 |
| `5000` | 服务内部错误 | 500 |

## 2. 鉴权

### 2.1 登录

```http
POST /api/auth/login
Content-Type: application/json

{"account":"planner01","password":"demo123"}
```

演示账号：

| 账号 | 角色 |
|---|---|
| `sales01` | 销售 |
| `planner01` | 计划 |
| `supervisor01` | 主管 |
| `admin` | 管理员 |

后端演示账号统一密码 `demo123`，由 `seed_demo_users()` 从 `app/static/mock/users.json` 初始化。静态 mock 页面则接受任意非空密码，两者不要混淆。

返回：

```json
{
  "code": 0,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user": {
      "account": "planner01",
      "name": "计划演示",
      "role": "planner",
      "tenant_id": "demo",
      "department": "计划运营部",
      "customer_scopes": ["全部客户"]
    }
  }
}
```

### 2.2 当前用户

```http
GET /api/auth/me
Authorization: Bearer <JWT>
```

### 2.3 权限说明

- `AUTH_REQUIRED=false`：开发模式允许无 token 调用，用于本地测试；
- `AUTH_REQUIRED=true`：除 `/health`、`/api/llm/status`、`/api/auth/login` 外都必须登录；
- 角色限制目前只加在导入/模板/BOM 展开路由：`planner` 或 `admin`；
- 其他业务接口只要求“已登录”，尚未按销售/主管细分；
- 客户范围字段已存入用户表，但订单接口尚未强制按客户范围过滤；
- 生产环境必须设置 `AUTH_REQUIRED=true` 和强 `AUTH_SECRET`。

## 3. 接口总览

| 方法 | 路径 | 用途 | 角色 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 公开 |
| GET | `/api/llm/status` | 模型配置状态，不返回 Key | 公开 |
| POST | `/api/auth/login` | 登录并签发 JWT | 公开 |
| GET | `/api/auth/me` | 当前用户 | 已登录 |
| GET | `/api/templates/{type}` | 四表模板 | 计划/管理员 |
| POST | `/api/imports/bundle` | 四表整体导入 | 计划/管理员 |
| GET | `/api/imports/{batch_id}` | 批次详情 | 计划/管理员 |
| GET | `/api/imports/{batch_id}/errors.csv` | 错误 CSV | 计划/管理员 |
| POST | `/api/bom/expand` | BOM 展开 | 计划/管理员 |
| GET | `/api/orders` | 订单承诺列表 | 已登录 |
| GET | `/api/orders/{order_no}` | 订单详情（同承诺） | 已登录 |
| GET | `/api/orders/{order_no}/promise` | 单订单承诺 | 已登录 |
| GET | `/api/orders/{order_no}/explain` | 确定性解释文案 | 已登录 |
| POST | `/api/simulate` | 插单/加急模拟 | 已登录 |
| POST | `/api/snapshots` | 创建快照 | 已登录 |
| GET | `/api/snapshots/compare` | 快照对比 | 已登录 |
| POST | `/api/export` | 创建 xlsx 导出任务 | 已登录 |
| GET | `/api/export/{task_id}` | 轮询导出 | 已登录 |
| GET | `/api/export/{task_id}/download` | 下载 xlsx | 已登录 |

## 4. 导入

### 4.1 模板

```http
GET /api/templates/{type}
```

`type` 取值：`orders`、`bom`、`inventory`、`in_transit`。

返回 UTF-8 BOM CSV，`Content-Disposition` 为附件。

### 4.2 四表整体导入

```http
POST /api/imports/bundle
Content-Type: multipart/form-data
Authorization: Bearer <JWT>
```

表单字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `orders` | 是 | 订单 CSV |
| `bom` | 是 | BOM CSV |
| `inventory` | 是 | 库存 CSV |
| `in_transit` | 是 | 在途 CSV |
| `mode` | 否 | `ALL_OR_NOTHING`（默认）或 `PARTIAL_WITH_AUDIT` |
| `allow_partial` | 否 | `PARTIAL_WITH_AUDIT` 时必须为 `true` |

规则：

- 单文件大小受 `MAX_UPLOAD_MB` 限制，默认 20 MB；
- 默认全或无：任一表任一行错误，整批 `ROLLED_BACK`，`imported_rows=0`；
- 部分导入：`mode=PARTIAL_WITH_AUDIT` 且 `allow_partial=true`，保留成功行并标记 `PARTIAL_IMPORTED`；
- 相同租户 + 相同模式 + 相同文件 SHA-256 会返回同一批次，保证幂等；
- 原始 CSV 以 base64 持久化到 `import_batches_v2.payload`，重启后重新解析。

响应重点：

```json
{
  "code": 0,
  "data": {
    "batch_id": "ib_...",
    "status": "COMMITTED",
    "mode": "ALL_OR_NOTHING",
    "imported_rows": 120,
    "failed_rows": 0,
    "file_hash": "...",
    "tables": {
      "orders": {"ok_rows": 20, "failed_rows": 0},
      "bom": {"ok_rows": 60, "failed_rows": 0},
      "inventory": {"ok_rows": 20, "failed_rows": 0},
      "in_transit": {"ok_rows": 20, "failed_rows": 0}
    }
  }
}
```

### 4.3 批次详情

```http
GET /api/imports/{batch_id}?include_records=false
```

`include_records=true` 时返回强类型转换后的有效记录；默认只返回摘要。

### 4.4 错误 CSV

```http
GET /api/imports/{batch_id}/errors.csv
```

固定列：`row_no,column,value,reason`。

### 4.5 BOM 展开

```http
POST /api/bom/expand
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "batch_id": "ib_...",
  "root_code": "FG-500",
  "qty": "10",
  "max_depth": 5
}
```

- `qty` 用字符串传 Decimal；
- `max_depth` 范围 1–5；
- 回滚批次会被拒绝；
- 环返回 `1101` 和 `path`；
- 超层返回 `1102`；
- 其他 BOM 错误返回 `1103`。

## 5. 订单承诺

### 5.1 订单列表

```http
GET /api/orders?q=&batch_id=
Authorization: Bearer <JWT>
```

| 参数 | 说明 |
|---|---|
| `q` | 订单号/客户/成品料号模糊搜索 |
| `batch_id` | 指定导入批次；不传则用当前租户最近一次已提交批次 |

返回：

```json
{
  "batch_id": "ib_...",
  "calc_version": "gen-1.0",
  "orders": [
    {
      "order_no": "SO202601004",
      "customer": "华东智造",
      "item_code": "FG-500",
      "qty": "100.000000",
      "due_date": "2026-11-10",
      "kit_date": "2026-11-17",
      "earliest_start_date": "2026-11-14",
      "can_commit": false,
      "delay_days": 7,
      "gaps": [
        {
          "item_code": "RM-033",
          "item_name": "RM-033",
          "need": "30012.920000",
          "available": "1200.000000",
          "gap": "28812.920000",
          "ready_date": null,
          "impact_orders": ["SO202601004", "SO202601005"]
        }
      ],
      "calc_version": "gen-1.0"
    }
  ]
}
```

### 5.2 单订单承诺

```http
GET /api/orders/{order_no}/promise?batch_id=
```

字段同上。订单不存在返回 `1002`。

### 5.3 订单详情

```http
GET /api/orders/{order_no}?batch_id=
```

当前与 `/promise` 同源，后续可扩展客户范围鉴权。

### 5.4 解释文案

```http
GET /api/orders/{order_no}/explain?batch_id=
```

返回确定性模板文案，不调用模型、不生成新数字。文案只引用承诺状态，具体数量/日期仍从结构化字段读取。

## 6. 模拟

```http
POST /api/simulate
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "order_no": "SO202601004",
  "mode": "insert",
  "qty": "50",
  "expect_date": "2026-11-08",
  "batch_id": "ib_..."
}
```

| 字段 | 说明 |
|---|---|
| `order_no` | 基准订单，必须存在于批次 |
| `mode` | `insert` 插入模拟订单；`rush` 调整目标订单交期 |
| `qty` | 模拟数量，必须大于 0 |
| `expect_date` | 期望日期 |
| `batch_id` | 可选，不传用最近批次 |

结果固定包含 `not_persisted=true`，不写主表。返回中包含受影响订单、影响原因、插单结果等。

## 7. 快照

### 7.1 创建快照

```http
POST /api/snapshots?batch_id=
Authorization: Bearer <JWT>
```

返回 `snapshot_id`、`calc_version`、`orders` 数量。

### 7.2 对比快照

```http
GET /api/snapshots/compare?from=<snap_a>&to=<snap_b>
Authorization: Bearer <JWT>
```

按订单号对齐，返回延后/提前/新增/消失等差异项，以及两侧快照的 `calc_version`。

## 8. 导出

### 8.1 创建任务

```http
POST /api/export
Authorization: Bearer <JWT>
Content-Type: application/json
```

齐套报告：

```json
{
  "kind": "kit_report",
  "batch_id": "ib_..."
}
```

快照差异：

```json
{
  "kind": "snapshot_diff",
  "from_snapshot": "snap_a",
  "to_snapshot": "snap_b"
}
```

`kind` 仅支持 `kit_report` 和 `snapshot_diff`。

### 8.2 轮询与下载

```http
GET /api/export/{task_id}
GET /api/export/{task_id}/download
```

任务状态：`PENDING`、`RUNNING`、`SUCCESS`、`FAILED`。

同一登录账号同时只允许一个未完成任务，超出返回 429；未登录开发模式用 `X-User-Id` 区分归属。当前导出由 web 进程内线程池执行；Celery 导出任务入口已建但未启用。

> 登录后任务归属优先取 JWT 账号；`X-User-Id` 只作为未登录开发模式的回退，不应在生产环境信任。

## 9. 健康与模型状态

### 9.1 健康检查

```http
GET /health
```

```json
{
  "status": "ok",
  "service": "delivery-promise",
  "version": "0.3.0-g3-g4",
  "port": 8003,
  "timezone": "Asia/Shanghai",
  "timestamp": "2026-11-02T16:58:36+08:00"
}
```

### 9.2 模型状态

```http
GET /api/llm/status
```

返回 `provider`、`model`、`base_url`、`enabled`、`api_key_configured`、`timeout_seconds`，不返回 Key。

## 10. 调用示例

```powershell
# 登录
curl.exe -X POST http://127.0.0.1:8003/api/auth/login -H "Content-Type: application/json" -d '{"account":"planner01","password":"demo123"}'

# 导入
curl.exe -X POST http://127.0.0.1:8003/api/imports/bundle -H "Authorization: Bearer <token>" -F "orders=@samples/03/orders.csv" -F "bom=@samples/03/bom.csv" -F "inventory=@samples/03/inventory.csv" -F "in_transit=@samples/03/in_transit.csv"

# 查询
curl.exe "http://127.0.0.1:8003/api/orders?batch_id=<batch_id>" -H "Authorization: Bearer <token>"
```