# 订单交期测算与缺料预警

> 面向离散制造场景的订单交期承诺、BOM 缺料展开、库存/在途冲减与场景模拟系统。

**作者：** Xxxnickname

<p align="center">
  <img src="docs/screenshots/02-dashboard.png" alt="交付驾驶舱" width="100%" />
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-blue">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688">
  <img alt="JavaScript" src="https://img.shields.io/badge/Frontend-Vanilla%20JS-f7df1e">
  <img alt="Tests" src="https://img.shields.io/badge/tests-33%20passed-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

## 目录

- [1. 这个系统解决什么问题](#1-这个系统解决什么问题)
- [2. 角色与典型流程](#2-角色与典型流程)
- [3. 功能地图](#3-功能地图)
- [4. 两种运行方式](#4-两种运行方式)
- [5. 5 分钟启动](#5-5-分钟启动)
- [6. 实际使用流程](#6-实际使用流程)
- [7. 四张 CSV 怎么准备](#7-四张-csv-怎么准备)
- [8. 计算口径](#8-计算口径)
- [9. 系统架构](#9-系统架构)
- [10. 技术栈](#10-技术栈)
- [11. API 速查](#11-api-速查)
- [12. 数据与持久化](#12-数据与持久化)
- [13. 目录结构](#13-目录结构)
- [14. 配置项](#14-配置项)
- [15. 测试与验收](#15-测试与验收)
- [16. 当前边界](#16-当前边界)
- [17. 常见问题](#17-常见问题)
- [18. 安全与隐私](#18-安全与隐私)
- [19. 文档索引](#19-文档索引)

## 1. 这个系统解决什么问题

离散制造企业里，“这张订单能不能按期交”通常不是一句销售承诺就能回答。它同时取决于：

- 订单要什么成品、数量多少、客户交期是哪天；
- 成品 BOM 展开后，每一层半成品和原材料需要多少；
- 现有库存里有多少已经被别的订单占用；
- 在途采购什么时候到、到多少；
- 同一物料被多张订单共享时，应该先满足谁；
- 如果插单或加急，会影响哪些已有订单。

本项目的目标是把这条链路变成一套**可复算、可追溯、可演示**的工程闭环：

```text
订单 / BOM / 库存 / 在途
          ↓
四表校验、别名归一、批次留痕
          ↓
BOM 递归展开（最多 5 层）
          ↓
库存扣减 + 在途按 ETA 冲减
          ↓
齐套日 / 最早开工日 / 交期承诺
          ↓
缺口明细 / 影响订单 / 场景模拟 / 快照对比 / 导出
```

核心约束：

> **模型不参与数量、日期、缺口和交期计算。** 所有业务数字由 Python `Decimal` 和确定性代码产生；DeepSeek 只用于“规则无法识别的表头映射建议”，且失败会自动回退规则。

## 2. 角色与典型流程

| 角色 | 关心什么 | 当前能做什么 | 当前实现边界 |
|---|---|---|---|
| 销售 | 我的订单到哪一步了，能不能按期交，需不需要催 | 查看授权客户订单、承诺结论、缺口、延期天数、场景模拟；从驾驶舱/订单页下钻 | 前端按客户范围过滤；后端客户范围字段已建模，但订单查询尚未强制按客户范围过滤 |
| 计划员 | 四张表怎么进来，库存和在途是否准确 | 下载模板、导入四表、查看批次错误、查看库存、查看缺料、维护基础数据演示 | 导入/模板 API 已实现；基础数据页目前是 mock；导入 UI 仍是 mock |
| 主管 | 哪些订单有风险，缺口影响谁，插单会带来什么 | 驾驶舱、缺料台账、缺口追溯、影响订单、插单/加急模拟、快照对比、导出缺口表 | 驾驶舱/台账/对比页使用 mock；后端已有对应计算 API |
| 采购 | 主管让我采购什么，哪些到货要回填 | 本期没有独立采购账号；主管导出缺口表后线下交给采购，采购到货后由计划员把在途/库存数据回填 | 采购协同、询价、到货质检是后续扩展 |
| 管理员 | 账号、权限、数据边界 | 查看用户管理演示、切换角色、验证角色菜单 | 用户管理页是 mock；后端只有演示用户种子和角色依赖，没有用户 CRUD API |

推荐的业务闭环：

1. 销售在订单查询页确认客户交期和承诺结论；
2. 计划员从 ERP 导出四张 CSV，通过 API 导入；
3. 系统按 BOM 展开、库存/在途冲减，计算齐套日和缺口；
4. 主管在缺口台账查看高风险物料、受影响订单和 BOM 路径；
5. 主管把缺口表导出，线下交采购催料；
6. 采购到货后，计划员更新在途/库存表，重新导入并复算；
7. 销售看到最新承诺，必要时发起插单/加急模拟。

## 3. 功能地图

| 功能 | 前端页面 | 后端 API | 当前状态 |
|---|---|---|---|
| 登录与角色菜单 | `#/login` | `POST /api/auth/login` | 前端 mock 登录；后端 JWT 登录已实现 |
| 交付驾驶舱 | `#/dashboard` | 无独立聚合接口 | 前端 mock 展示；数据来自 `static/mock` |
| 订单查询 / 详情 | `#/query`、`#/order/:no` | `GET /api/orders`、`GET /api/orders/{order_no}/promise` | 页面 mock；后端承诺计算已实现 |
| 缺料台账 / 缺口追溯 | `#/shortages` | 由订单承诺结果中的 `gaps`、`impact_orders` 提供 | 页面 mock；后端没有独立 `/api/shortages` |
| 库存总览 / 退货 | `#/inventory` | 无独立库存 API | 页面 mock；后端库存只参与计算，退货未建模 |
| 数据导入 | `#/import` | `POST /api/imports/bundle` | 页面 mock；真实导入请用 `/docs` 或 API |
| 基础数据 / 别名 | `#/master` | 无 CRUD API | 页面 mock；别名队列为内存服务 |
| 场景模拟 | `#/simulate` | `POST /api/simulate` | 页面 mock；后端模拟已实现，结果不落库 |
| 快照对比 | `#/compare` | `POST /api/snapshots`、`GET /api/snapshots/compare` | 页面 mock；后端快照已实现 |
| 导出 | 页面内导出按钮 | `POST /api/export`、轮询、下载 | 页面 mock 生成 CSV；后端生成 xlsx |
| 用户管理 | `#/users` | 无用户 CRUD API | 页面 mock；后端有角色依赖和演示账号 |

> 这张表是理解本项目的关键：**前端是 11 屏静态 mock 演示，后端是独立可调用的 FastAPI 服务。** 两者共享同一套业务口径和数据结构，但还没有完成浏览器端真实 API 联调。

## 4. 两种运行方式

### 方式 A：只看界面（静态 mock，推荐先看效果）

不需要安装 Python 依赖，不需要数据库，不会触发真实导入或计算：

```powershell
python -m http.server 8003 --directory app\static
```

打开 <http://127.0.0.1:8003/>。

- 登录账号：`sales01`、`planner01`、`supervisor01`、`admin`
- 密码：任意非空（静态 mock 只校验账号是否存在且启用）
- 数据：全部来自 `app/static/mock/*.json`
- 适合：产品演示、页面走查、截图、角色菜单评审

### 方式 B：运行后端 API（真实导入、计算、导出）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

打开：

- 首页：<http://127.0.0.1:8003/>
- Swagger：<http://127.0.0.1:8003/docs>
- 健康检查：<http://127.0.0.1:8003/health>
- OpenAPI JSON：<http://127.0.0.1:8003/openapi.json>

注意：即使启动 FastAPI，首页前端仍然使用 `MOCK=true` 的静态数据；真实 API 请通过 `/docs` 或 `curl` 调用。前端切换真实 API 是后续路线图项，详见 [当前边界](#16-当前边界)。

### 方式 C：Docker Compose

```powershell
Copy-Item .env.example .env
# 修改 AUTH_SECRET、MODEL_API_KEY、数据库密码
docker compose up -d --build
docker compose ps
```

服务：

- `app`：FastAPI，宿主端口 `8003`
- `postgres`：PostgreSQL 16，不映射宿主端口
- `redis`：Redis 7，不映射宿主端口
- `worker`：Celery worker（队列骨架）

Compose 工程名固定为 `plan`，应用端口固定为 `8003`。

## 5. 5 分钟启动

### 5.1 静态预览

```powershell
cd delivery-promise-system
python -m http.server 8003 --directory app\static
```

浏览器打开 <http://127.0.0.1:8003/>，点击“销售演示/计划演示/主管演示/管理员”快速切换角色。

### 5.2 后端 API

```powershell
cd delivery-promise-system
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

```powershell
curl.exe http://127.0.0.1:8003/health
curl.exe http://127.0.0.1:8003/api/llm/status
```

### 5.3 一键验收

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\acceptance.py
.\.venv\Scripts\python.exe eval\run.py --golden
.\.venv\Scripts\python.exe scripts\check_dod.py
```

当前结果：

- `pytest`：33 passed
- 极端/边界场景：22/22 PASS
- 20 单替身基准：100% 对齐
- 1000 行订单计算：低于 5 秒
- `/health`：200
- xlsx 导出：通过文件头验证

## 6. 实际使用流程

### 6.1 登录

静态 mock：

- `sales01` / 任意非空密码
- `planner01` / 任意非空密码
- `supervisor01` / 任意非空密码
- `admin` / 任意非空密码

真实后端：

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/auth/login -H "Content-Type: application/json" -d '{"account":"planner01","password":"demo123"}'
```

返回 `access_token` 后，后续请求带：

```http
Authorization: Bearer <access_token>
```

> 后端演示账号统一密码为 `demo123`，由 `seed_demo_users()` 从 `app/static/mock/users.json` 初始化。

### 6.2 准备四张 CSV

从 `samples/03/` 复制样例，或通过 API 下载模板：

```powershell
curl.exe -OJ http://127.0.0.1:8003/api/templates/orders
curl.exe -OJ http://127.0.0.1:8003/api/templates/bom
curl.exe -OJ http://127.0.0.1:8003/api/templates/inventory
curl.exe -OJ http://127.0.0.1:8003/api/templates/in_transit
```

模板表头：

| 表 | 必填列 | 可选列 |
|---|---|---|
| `orders.csv` | `order_no, item_code, qty, due_date` | `customer` |
| `bom.csv` | `parent_code, child_code, qty_per` | `scrap_rate, substitute_group, level` |
| `inventory.csv` | `item_code, on_hand, allocated` | `warehouse` |
| `in_transit.csv` | `item_code, qty, eta_date` | `batch_no, supplier` |

### 6.3 导入四表

在 Swagger `/docs` 中选择 `POST /api/imports/bundle`，依次上传四个文件；或用 `curl`：

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/imports/bundle -H "Authorization: Bearer <access_token>" -F "orders=@samples/03/orders.csv" -F "bom=@samples/03/bom.csv" -F "inventory=@samples/03/inventory.csv" -F "in_transit=@samples/03/in_transit.csv" -F "mode=ALL_OR_NOTHING"
```

返回 `batch_id`。默认全或无：任一行有错误，整批 `ROLLED_BACK`、`imported_rows=0`。如果需要部分导入，显式传：

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/imports/bundle -H "Authorization: Bearer <access_token>" -F "orders=@samples/03/sample_error_orders.csv" -F "bom=@samples/03/bom.csv" -F "inventory=@samples/03/inventory.csv" -F "in_transit=@samples/03/in_transit.csv" -F "mode=PARTIAL_WITH_AUDIT" -F "allow_partial=true"
```

### 6.4 查询订单承诺

```powershell
curl.exe "http://127.0.0.1:8003/api/orders?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
```

单张订单：

```powershell
curl.exe "http://127.0.0.1:8003/api/orders/SO202601004/promise?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
```

重点字段：

- `can_commit`：当前供给下能否按客户交期承诺
- `kit_date`：齐套日；有缺口时为 `null`
- `earliest_start_date`：齐套日减生产提前期
- `delay_days`：齐套日晚于客户交期的天数；有缺口时为 `null`
- `gaps`：缺口物料、需求量、已分配量、缺口量、影响订单
- `calc_version`：计算版本，便于对账

### 6.5 查看缺口与影响订单

后端没有独立“缺料台账”接口；缺口来自订单承诺结果的 `gaps` 数组。每个缺口包含：

- `item_code`：物料
- `need`：展开后的总需求
- `available`：实际分配量（库存 + 在途）
- `gap`：未覆盖数量
- `ready_date`：该物料齐套日
- `impact_orders`：同样缺该物料的订单号列表

主管页面中的“缺口台账/追溯抽屉”目前是 mock 展示；真实数据可通过 `/api/orders` 聚合得到。

### 6.6 插单 / 加急模拟

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/simulate -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{"order_no":"SO202601004","mode":"insert","qty":"50","expect_date":"2026-11-08","batch_id":"<batch_id>"}'
```

`mode` 支持：

- `insert`：插入一张模拟订单，观察对现有订单的影响
- `rush`：调整目标订单交期，观察加急影响

返回固定包含 `not_persisted=true`，不会写主表。

### 6.7 快照对比

创建快照：

```powershell
curl.exe -X POST "http://127.0.0.1:8003/api/snapshots?batch_id=<batch_id>" -H "Authorization: Bearer <access_token>"
```

比较两次快照：

```powershell
curl.exe "http://127.0.0.1:8003/api/snapshots/compare?from=<snap_a>&to=<snap_b>" -H "Authorization: Bearer <access_token>"
```

### 6.8 导出 xlsx

齐套报告：

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/export -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{"kind":"kit_report","batch_id":"<batch_id>"}'
```

快照差异：

```powershell
curl.exe -X POST http://127.0.0.1:8003/api/export -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{"kind":"snapshot_diff","from_snapshot":"<snap_a>","to_snapshot":"<snap_b>"}'
```

轮询和下载：

```powershell
curl.exe "http://127.0.0.1:8003/api/export/<task_id>" -H "Authorization: Bearer <access_token>"
curl.exe -OJ "http://127.0.0.1:8003/api/export/<task_id>/download" -H "Authorization: Bearer <access_token>"
```

同一登录账号同时只允许一个未完成导出任务；超出返回 `429`。未登录开发模式下用 `X-User-Id` 区分任务归属。

## 7. 四张 CSV 怎么准备

### 7.1 订单表 `orders.csv`

| 列 | 必填 | 说明 |
|---|---|---|
| `order_no` | 是 | 订单号，必须唯一可识别 |
| `item_code` | 是 | 成品料号，会统一大写、去空格 |
| `qty` | 是 | 订单数量，必须大于 0 |
| `due_date` | 是 | 客户交期，严格 `YYYY-MM-DD` |
| `customer` | 否 | 客户名称，用于销售范围和展示 |

### 7.2 BOM 表 `bom.csv`

| 列 | 必填 | 说明 |
|---|---|---|
| `parent_code` | 是 | 父件料号 |
| `child_code` | 是 | 子件料号 |
| `qty_per` | 是 | 单位用量，必须大于 0 |
| `scrap_rate` | 否 | 损耗率，小数，例如 `0.02` 表示 2% |
| `substitute_group` | 否 | 替代组标识，当前用于数据表达 |
| `level` | 否 | 1–5，导入时校验；实际展开深度由父子边结构决定 |

### 7.3 库存表 `inventory.csv`

| 列 | 必填 | 说明 |
|---|---|---|
| `item_code` | 是 | 物料料号 |
| `on_hand` | 是 | 现有库存，必须大于等于 0 |
| `allocated` | 是 | 已分配数量，不能大于现有库存 |
| `warehouse` | 否 | 仓库/库位 |

### 7.4 在途表 `in_transit.csv`

| 列 | 必填 | 说明 |
|---|---|---|
| `item_code` | 是 | 物料料号 |
| `qty` | 是 | 在途数量，必须大于 0 |
| `eta_date` | 是 | 预计到货日，严格 `YYYY-MM-DD` |
| `batch_no` | 否 | 在途批次号 |
| `supplier` | 否 | 供应商 |

导入规则：

- 编码使用 UTF-8（带 BOM 也可）；
- 日期必须是 `YYYY-MM-DD`，不做自动猜测；
- 空行会跳过，但空文件会报错；
- 重复/归一后重复的表头会报错；
- 每个错误包含行号、列、原值、原因；
- 错误 CSV：`GET /api/imports/{batch_id}/errors.csv`。

## 8. 计算口径

### 8.1 BOM 展开

```text
qty_child = qty_parent × qty_per × (1 + scrap_rate)
```

- 根节点为成品，深度 0；
- 每条父子边深度 +1；
- 最大 5 层，超过立即报错，不截断；
- 检测环，返回环路径；
- 叶子物料按料号合并；
- 每条路径保留 `traces`，用于解释和追溯。

> `level` 字段是导入时的 1–5 校验值；实际展开深度由 BOM 边结构计算。两者不要混淆。

### 8.2 供给冲减

```text
available[item] = on_hand - allocated
in_transit[item] = 按 eta_date 升序、batch_no 升序
```

订单按 `due_date ASC, order_no ASC` 处理。每个订单展开 BOM 后，按物料消耗共享供给池：

1. 先消耗当前可用库存；
2. 再按 ETA 顺序消耗在途；
3. 全部满足时，`ready_date = 最后一批消耗日期`；
4. 仍有缺口时，`gap_qty > 0`，`ready_date = null`；
5. 同一物料被多个订单共享时，先到期订单优先。

### 8.3 齐套、开工、承诺

- `kit_date`：所有物料 `ready_date` 的最大值；任一物料有缺口则为 `null`；
- `earliest_start_date`：`kit_date - PRODUCTION_LEAD_DAYS`，默认提前 3 天；
- `can_commit`：`kit_date is not null and kit_date <= due_date`；
- `delay_days`：`max(0, kit_date - due_date)`；有缺口时为 `null`。

> 当前 `can_commit` 只比较齐套日与客户交期，不把“最早开工日是否早于今天”作为额外门禁；这是当前实现的明确口径，不是遗漏。

### 8.4 替代料

`app/services/bom_expand.py` 中的 `plan_substitutions()` 支持：

- 一对一替代；
- 替代比例折算；
- 替代料可用量不足时返回剩余缺口。

当前状态：该服务已实现并通过单元测试，但**订单承诺主链路尚未自动调用替代料计划**；BOM 展开只按 `qty_per` 和 `scrap_rate` 计算。生产接入前需要把替代组规则、替代料库存和审批策略串进计算链路。

## 9. 系统架构

```mermaid
flowchart LR
    U[销售 / 计划员 / 主管 / 管理员] --> WEB[原生 HTML/CSS/JS 工作台<br/>当前 static mock]
    WEB -. 真实 API 未联调 .-> API[FastAPI API 层]
    API --> AUTH[JWT / 角色依赖]
    API --> IMPORT[四表导入与校验]
    IMPORT --> ALIAS[表头/料号别名归一]
    ALIAS --> BOM[5 层 BOM 展开]
    BOM --> SUPPLY[库存 + 在途冲减]
    SUPPLY --> PROMISE[齐套日 / 交期承诺]
    PROMISE --> GAP[缺口与影响订单]
    PROMISE --> SIM[插单 / 加急模拟]
    PROMISE --> SNAP[快照对比]
    PROMISE --> EXPORT[线程池 xlsx 导出]
    API --> DB[(SQLite / PostgreSQL)]
    API -. 预留 .-> REDIS[(Redis)]
    REDIS -. 预留 .-> WORKER[Celery Worker]
    API -. 仅表头映射 .-> LLM[DeepSeek / OpenAI-compatible]
```

关键边界：

- 请求主链路是同步的：FastAPI → 导入/计算服务 → SQLite/PostgreSQL；
- Redis/Celery 目前是部署骨架，不在请求主链路；
- xlsx 导出当前由 web 进程内线程池完成，Celery 导出任务入口已建但未启用；
- LLM 只在规则无法识别表头时提供映射建议，失败自动回退规则；
- 订单解释文案是确定性模板，不调用模型。

## 10. 技术栈

| 层次 | 技术 | 版本/说明 |
|---|---|---|
| 语言 | Python | 3.11（Dockerfile 与 CI 一致） |
| Web API | FastAPI | `0.115.14` |
| ASGI 服务器 | Uvicorn | `0.32.1`（`[standard]`） |
| 数据校验 | Pydantic | `2.14.2` |
| 数据处理 | Pandas | `2.3.3` |
| 数值计算 | Python `Decimal` | 数量、金额、BOM 用量 |
| ORM | SQLAlchemy | `2.0.55`（requirements 固定 `<2.1`） |
| 本地数据库 | SQLite | 零依赖启动，默认 `./plan.db` |
| 生产数据库 | PostgreSQL | 16（Docker Compose） |
| PostgreSQL 驱动 | psycopg | `3.2.x` |
| Excel 导出 | openpyxl | `3.1.x` |
| 鉴权 | PyJWT + PBKDF2-HMAC-SHA256 | 26 万次迭代，HS256，默认 60 分钟 |
| 上传解析 | python-multipart | `0.0.32` |
| 配置加载 | python-dotenv | 读取项目根目录 `.env` |
| 模型调用 | HTTPX | `0.27.2`，OpenAI-compatible Chat Completions |
| 前端 | HTML5 + CSS + 原生 ES Module JavaScript | 无构建步骤、无框架 |
| 图表 | 内联 SVG | 不依赖图表库 |
| 队列 | Celery + Redis | Celery `5.x`（当前 5.6.3）、Redis `5.x` 客户端；Redis 服务为 7 |
| 测试 | Pytest + FastAPI TestClient + HTTPX MockTransport | `pytest 8.4.2` |
| CI | GitHub Actions | Python 3.11、Ubuntu、pytest、JS 语法、Compose 配置 |
| 安全扫描 | gitleaks | GitHub Actions Secret Scan |

> “前端 0 依赖”指浏览器端不需要 npm、打包器或图表库；后端仍需要 Python 依赖。

## 11. API 速查

完整说明见 [docs/API.md](docs/API.md)，交互式文档启动后访问 `/docs`。

| 方法 | 路径 | 用途 | 角色 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 公开 |
| GET | `/api/llm/status` | 模型配置状态（不返回 Key） | 公开 |
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

统一响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "trace_id": "tr_xxx"
}
```

请求头：

- `Authorization: Bearer <JWT>`：登录后调用；
- `X-Tenant-Id`：租户标识，默认 `demo`；
- `X-Trace-Id`：可选，未传则服务端生成；
- `X-User-Id`：未登录开发模式下的导出任务归属，默认 `demo`；登录后优先使用 JWT 账号。

## 12. 数据与持久化

### 12.1 当前实际持久化

运行时 SQLite/PostgreSQL 中实际使用的表：

| 表 | 用途 |
|---|---|
| `users` | 演示用户、PBKDF2 密码哈希、角色、客户范围 |
| `import_batches_v2` | 导入批次、状态、文件哈希、原始 CSV 的 base64 payload |
| `calc_snapshots_v2` | 订单承诺快照，`items` 为 JSON |
| `audit_logs_v2` | 审计表结构已建，`audit()` 函数存在，但当前业务路径尚未调用 |

四张业务表（订单、BOM、库存、在途）在运行时是**解析后的内存对象**，原始 CSV 以 base64 存在 `import_batches_v2.payload`，重启时重新解析，避免 JSON 丢失 Decimal/date 精度。

### 12.2 目标规范化模型

`migrations/0001_init.py` 还包含面向生产的目标表：

- `items`、`bom_edges`、`inventory`、`in_transit`
- `orders`、`order_lines`
- `calc_snapshots`、`import_batches`、`audit_logs`
- 以及当前运行时使用的 `*_v2` 表

这些目标表是后续 PostgreSQL 迁移和查询优化的方向，不代表当前应用已经写入全部规范化表。详细字段见 [docs/DATA_MODEL.md](docs/DATA_MODEL.md)。

## 13. 目录结构

```text
app/
  api/            FastAPI 路由：鉴权、导入、订单、模拟、快照、导出、LLM 状态
  core/           配置、数据库、JWT、Decimal、租户上下文、统一错误
  models/         领域对象与强类型记录
  services/       解析、别名、BOM、供给、齐套、承诺、模拟、快照、导出、LLM
  workers/        Celery 入口与导出任务骨架
  static/         11 屏前端、CSS、原生 JS、mock 数据、SVG 图标
samples/03/       四表样例、模板、错误样例、20 单替身基准
tests/            FR 编号测试、API 闭环、鉴权、持久化、性能
eval/             20 单基准对比脚本
scripts/          自检、验收、DoD、LLM 检查、OpenAPI 导出
migrations/       PostgreSQL 初始迁移
docs/             架构、数据模型、API、用法、截图、部署、测试、LLM 说明
deploy/           Nginx 示例
.github/          CI、Secret Scan、Issue/PR 模板、Dependabot
```

## 14. 配置项

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | `production` 时默认使用 PostgreSQL DSN |
| `APP_PORT` | `8003` | 应用端口；三项目并行时固定 8003 |
| `DATABASE_URL` | 本地 `sqlite:///./plan.db` | 显式数据库连接串，优先级最高 |
| `DB_DSN` | `postgresql://plan:plan@postgres:5432/plan` | Docker/生产 PostgreSQL |
| `AUTH_REQUIRED` | `false` | 生产必须设为 `true` |
| `AUTH_SECRET` | 开发占位值 | 生产必须换至少 32 字节随机值 |
| `ACCESS_TOKEN_MINUTES` | `60` | JWT 有效期 |
| `MODEL_PROVIDER` | `deepseek` | 仅用于状态展示/扩展 |
| `MODEL_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible 地址 |
| `MODEL_NAME` | `deepseek-flash` | 当前使用的模型名 |
| `MODEL_API_KEY` | 空 | 只在服务器环境变量/`.env` 中填写 |
| `LLM_ENABLED` | `false` | 关闭时只用规则表头映射 |
| `MODEL_TIMEOUT_SECONDS` | `20` | 模型请求超时 |
| `MAX_UPLOAD_MB` | `20` | 单个上传文件大小上限 |
| `MAX_BOM_DEPTH` | `5` | 预留配置；当前计算固定最多 5 层 |
| `PRODUCTION_LEAD_DAYS` | `3` | 最早开工日 = 齐套日 - 该天数 |
| `EXPORT_MAX_ROWS` | `50000` | 预留配置；当前导出未强制行数上限 |

## 15. 测试与验收

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\acceptance.py
.\.venv\Scripts\python.exe eval\run.py --golden
.\.venv\Scripts\python.exe scripts\check_dod.py
```

覆盖范围：

- 四表模板、行列级校验、全或无/部分导入/幂等；
- 5 层 BOM、环检测、超层、多路径、损耗；
- 替代料比例折算（独立服务）；
- 库存 + 在途冲减、齐套日、交期承诺；
- 订单解释不含新数字；
- 插单/加急模拟、快照对比、xlsx 导出；
- JWT 登录、错误密码、持久化、性能；
- 22 条边界场景与 20 单替身基准。

详细说明见 [docs/TESTING.md](docs/TESTING.md)。

## 16. 当前边界

| 项目 | 当前状态 |
|---|---|
| 前端真实数据 | 仍使用 `static/mock`；真实 API 未在浏览器端联调 |
| 客户范围 | 前端 mock 会按销售客户范围过滤；后端订单查询尚未强制过滤 |
| 角色权限 | 前端菜单/页面有角色控制；后端仅导入/模板做 planner/admin 校验；其他接口在 `AUTH_REQUIRED=true` 时要求登录 |
| 租户隔离 | `X-Tenant-Id` 可指定，租户与 JWT 身份尚未强绑定，不能视为生产级隔离 |
| 采购角色 | 无独立账号；主管导出缺口表线下交采购，计划员回填到货 |
| 缺料台账/库存/退货 | 页面 mock；后端没有独立缺料、库存、退货 API；退货未建模 |
| 基础数据 | 页面 mock；别名队列在内存，无持久化 CRUD |
| 用户管理 | 页面 mock；后端无用户 CRUD API |
| 替代料 | 服务与单测已实现，未接入订单承诺主链路 |
| 审计 | 表结构与 `audit()` 已建，业务路径未调用 |
| 导出 | web 进程线程池；Celery 导出任务未启用；登录后任务归属取 JWT 账号，未登录开发模式回退 `X-User-Id` |
| PostgreSQL | 迁移已准备，容器未在本机实际启动验证 |
| Redis/Celery | 骨架与最小 ping 任务；未做生产队列验证 |
| 20 单基准 | synthetic stand-in，不是人工核算真值 |
| 可观测性 | 有 `trace_id` 和统一错误响应；无正式 metrics/alerts |

完整说明与路线图见 [docs/LIMITATIONS.md](docs/LIMITATIONS.md)。

## 17. 常见问题

**Q：为什么我启动了 FastAPI，页面还是 mock 数据？**

A：前端 `app/static/js/api.js` 中 `MOCK=true`，页面只读 `static/mock/*.json`。真实 API 请用 `/docs` 或 `curl`；前端切真实 API 是后续工作。

**Q：静态预览的密码是什么？**

A：任意非空密码。静态 mock 只校验账号存在且状态启用。后端演示账号统一为 `demo123`。

**Q：为什么订单显示有缺口，但没有齐套日？**

A：任一物料 `gap_qty > 0` 时，`kit_date` 返回 `null`，避免给出虚假承诺；`delay_days` 也为 `null`。

**Q：为什么 `can_commit` 和 `earliest_start_date` 看起来不一致？**

A：`can_commit` 只比较 `kit_date <= due_date`；`earliest_start_date` 是 `kit_date - PRODUCTION_LEAD_DAYS` 的参考值，当前不作为额外门禁。

**Q：能不能直接连 ERP？**

A：当前一期用 CSV 导入降低集成成本；ERP 直连、增量同步、主数据治理是后续扩展。

**Q：采购在哪里操作？**

A：本期没有采购账号。主管把缺口表线下交给采购，采购到货后由计划员更新在途/库存并重新导入；采购协同是路线图项。

**Q：DeepSeek Key 放哪里？**

A：只放服务器环境变量或本地 `.env`；不要提交 Git、不要放前端、不要写进 URL 或日志。`/api/llm/status` 只返回是否配置，不返回 Key。

## 18. 安全与隐私

- 仓库不包含 `.env`、数据库、导出文件、日志或真实业务数据；
- 演示账号和客户名称均为匿名化数据；
- 生产必须设置 `AUTH_REQUIRED=true` 和至少 32 字节的 `AUTH_SECRET`；
- DeepSeek Key 只从后端环境变量读取，通过 `Authorization: Bearer` 传输；
- 不在前端、URL、日志、报告中出现 Key；
- 上传接口有文件大小限制，CSV 解析严格校验；
- 当前租户隔离、客户范围过滤和审计落库仍需生产验收，详见 [SECURITY.md](SECURITY.md)。

## 19. 文档索引

- [详细用法](docs/USAGE.md)
- [架构设计](docs/ARCHITECTURE.md)
- [数据模型](docs/DATA_MODEL.md)
- [API 说明](docs/API.md)
- [截图集](docs/SCREENSHOTS.md)
- [测试与验收](docs/TESTING.md)
- [部署说明](docs/DEPLOYMENT.md)
- [运维手册](docs/operations.md)
- [DeepSeek API 传参](docs/llm-api.md)
- [当前边界与路线图](docs/LIMITATIONS.md)
- [安全策略](SECURITY.md)
- [贡献指南](CONTRIBUTING.md)
- [GitHub 上传指南](docs/GITHUB_UPLOAD.md)

## License

[MIT](LICENSE)
