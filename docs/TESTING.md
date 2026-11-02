# 测试与验收

## 1. 测试环境

- Python 3.11
- 依赖：`requirements-dev.txt`
- 数据库：本地 SQLite（测试用临时库）
- 前端：原生 JavaScript，无构建步骤
- CI：GitHub Actions，Ubuntu + Python 3.11

## 2. 本地命令

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\g2_check.py
.\.venv\Scripts\python.exe scripts\acceptance.py
.\.venv\Scripts\python.exe eval\run.py --golden
.\.venv\Scripts\python.exe scripts\check_dod.py
```

## 3. 当前结果

| 检查 | 结果 |
|---|---|
| Pytest | 33 passed |
| 22 条边界场景 | 22/22 PASS |
| 20 单基准 | 100.00% 对齐 |
| 1000 行订单计算 | < 5 秒 |
| `/health` | 200 |
| xlsx 导出 | PK 文件头验证通过 |
| DeepSeek `deepseek-flash` | 真实表头映射通过（项目记录） |

> 20 单基准是 synthetic stand-in，用于回归和演示，不是人工核算真值。真实业务基准到位后应替换并重跑。

## 4. 覆盖范围

| 范围 | 文件/命令 |
|---|---|
| FR-001 模板 | `tests/test_fr_001_template.py` |
| FR-002 行列校验 | `tests/test_fr_002_validation.py` |
| FR-003 回滚/部分导入/幂等 | `tests/test_fr_003_rollback.py` |
| FR-004 别名归一 | `tests/test_fr_004_alias.py` |
| FR-005 5 层展开 | `tests/test_fr_005_expand_5level.py` |
| FR-006 替代料 | `tests/test_fr_006_substitute.py` |
| FR-007 多路径 | `tests/test_fr_007_no_double_count.py` |
| FR-008 供给冲减 | `tests/test_fr_008_supply.py` |
| FR-009 齐套日 | `tests/test_fr_009_kitting.py` |
| FR-010 交期承诺 | `tests/test_fr_010_promise.py` |
| FR-012 模拟 | `tests/test_fr_012_simulate.py` |
| FR-013 快照对比 | `tests/test_fr_013_snapshot_diff.py` |
| FR-015 解释不含数字 | `tests/test_fr_015_explain_no_number.py` |
| FR-017 性能 | `tests/test_fr_017_performance.py` |
| FR-020 20 单基准 | `tests/test_fr_020_golden.py` |
| 鉴权 | `tests/test_auth.py` |
| 持久化 | `tests/test_persistence.py` |
| DeepSeek 传输 | `tests/test_deepseek_client.py` |
| 导入/承诺/模拟/导出 API 闭环 | `tests/test_api_g2.py`、`tests/test_api_g3.py` |
| BOM 环/深度 | `tests/test_bom_cycle_depth.py` |
| 表头映射 | `tests/test_llm_header_mapping.py` |

## 5. 22 条边界场景

`scripts/acceptance.py` 覆盖：

1. 空文件
2. 缺列
3. 非法日期
4. 负数量
5. 已分配超库存
6. 重复表头
7. 空行
8. 5 层 BOM
9. BOM 环
10. BOM 超层
11. 多路径不重复计数
12. 替代比例
13. 替代不足
14. 库存 + 在途
15. 无供给
16. 交期优先级
17. 全或无
18. 部分导入
19. 幂等
20. 快照差异
21. 解释无数字
22. xlsx 导出

## 6. API 验收

```powershell
# 健康
curl.exe http://127.0.0.1:8003/health

# 模型状态
curl.exe http://127.0.0.1:8003/api/llm/status

# 登录
curl.exe -X POST http://127.0.0.1:8003/api/auth/login -H "Content-Type: application/json" -d '{"account":"planner01","password":"demo123"}'

# 导入
curl.exe -X POST http://127.0.0.1:8003/api/imports/bundle -H "Authorization: Bearer <token>" -F "orders=@samples/03/orders.csv" -F "bom=@samples/03/bom.csv" -F "inventory=@samples/03/inventory.csv" -F "in_transit=@samples/03/in_transit.csv"

# 查询
curl.exe "http://127.0.0.1:8003/api/orders?batch_id=<batch_id>" -H "Authorization: Bearer <token>"
```

## 7. 前端检查

```powershell
Get-ChildItem app\static\js -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

静态预览：

```powershell
python -m http.server 8003 --directory app\static
```

浏览器走查：登录 → 驾驶舱 → 缺料台账 → 缺口追溯 → 订单详情 → 模拟 → 快照对比 → 移动端查询。

## 8. 已知说明

- 前端演示使用 mock；API 自测和浏览器界面走查分别通过，真实联调是后续项；
- Starlette TestClient 有一条上游弃用警告，不影响测试结果；
- 替代料服务有单测，但未接入订单承诺主链路；
- PostgreSQL、Redis/Celery 未在本机做生产级实跑；
- DeepSeek 真实调用受账号、网络、模型名影响，CI 不依赖真实 Key。