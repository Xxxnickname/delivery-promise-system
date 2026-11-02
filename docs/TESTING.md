# 测试与验收

## 本地命令

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\g2_check.py
.\.venv\Scripts\python.exe scripts\acceptance.py
.\.venv\Scripts\python.exe eval\run.py --golden
.\.venv\Scripts\python.exe scripts\check_dod.py
```

## 当前结果

| 检查 | 结果 |
|---|---|
| Pytest | 33 passed |
| 22 条边界场景 | 22/22 PASS |
| 20 单基准 | 100.00% 对齐 |
| 1000 行订单计算 | < 5 秒 |
| /health | 200 |
| xlsx 导出 | PK 文件头验证通过 |
| DeepSeek `deepseek-flash` | 真实表头映射通过 |

## 测试覆盖

| 范围 | 文件 |
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
| G2/G3 API 闭环 | `tests/test_api_g2.py`、`tests/test_api_g3.py` |

## 22 条边界场景

`scripts/acceptance.py` 覆盖：空文件、缺列、非法日期、负数量、分配超库存、重复表头、空行、5 层 BOM、环、超层、多路径、替代比例、替代不足、库存+在途、无供给、交期优先级、全或无、部分导入、幂等、快照差异、解释无数字、xlsx。

## 注意事项

- 20 单基准为 synthetic stand-in；真实人工核算到位后需替换并重跑。
- 当前前端演示使用 mock；API 自测和浏览器界面走查分别通过，真实联调是后续项。
- Starlette TestClient 有一条上游弃用警告，不影响测试结果。
