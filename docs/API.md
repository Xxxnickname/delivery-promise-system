# API 说明

交互式 OpenAPI：启动应用后访问 `/docs`。静态规范：[openapi.json](openapi.json)。

## 统一响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "trace_id": "tr_xxx"
}
```

失败时 `code` 非 0，`data` 中包含可定位信息。所有数量/金额字段使用字符串传输。

## 鉴权

生产环境必须：

```http
Authorization: Bearer <JWT>
```

JWT 由登录接口签发：

```http
POST /api/auth/login
Content-Type: application/json

{"account":"sales01","password":"demo123"}
```

开发环境 `AUTH_REQUIRED=false`，生产环境必须 `AUTH_REQUIRED=true`。

## 接口总览

| 方法 | 路径 | 用途 | 角色 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 公开 |
| GET | `/api/llm/status` | 模型配置状态，不返回 Key | 公开 |
| POST | `/api/auth/login` | 登录并签发 JWT | 公开 |
| GET | `/api/auth/me` | 当前用户 | 已登录 |
| GET | `/api/templates/{type}` | 四表模板 | 计划/管理员 |
| POST | `/api/imports/bundle` | 四表整体导入 | 计划/管理员 |
| GET | `/api/imports/{batch_id}` | 批次详情 | 已登录 |
| GET | `/api/imports/{batch_id}/errors.csv` | 错误 CSV | 已登录 |
| POST | `/api/bom/expand` | BOM 展开 | 已登录 |
| GET | `/api/orders` | 订单承诺列表 | 已登录 |
| GET | `/api/orders/{order_no}/promise` | 单订单承诺 | 已登录 |
| GET | `/api/orders/{order_no}/explain` | 解释文案 | 已登录 |
| POST | `/api/simulate` | 插单/加急模拟 | 已登录 |
| POST | `/api/snapshots` | 创建快照 | 已登录 |
| GET | `/api/snapshots/compare?from=&to=` | 快照对比 | 已登录 |
| POST | `/api/export` | 创建 xlsx 导出任务 | 已登录 |
| GET | `/api/export/{task_id}` | 轮询导出 | 已登录 |
| GET | `/api/export/{task_id}/download` | 下载 xlsx | 已登录 |

## 导入

```http
POST /api/imports/bundle
Content-Type: multipart/form-data
```

字段：`orders`、`bom`、`inventory`、`in_transit`，可选：

- `mode=ALL_OR_NOTHING|PARTIAL_WITH_AUDIT`
- `allow_partial=true`

默认全或无；失败时 `status=ROLLED_BACK`，`imported_rows=0`。

## 模拟

```json
{
  "batch_id": "ib_xxx",
  "order_no": "SO-DEMO-001",
  "mode": "insert",
  "qty": "50",
  "expect_date": "2026-11-08"
}
```

结果固定包含 `not_persisted=true`，不写主表。

## 导出

```json
{
  "kind": "kit_report",
  "batch_id": "ib_xxx"
}
```

或：

```json
{
  "kind": "snapshot_diff",
  "from_snapshot": "snap_a",
  "to_snapshot": "snap_b"
}
```

同一 `X-User-Id` 同时只允许一个未完成导出任务，超出返回 `429`。

