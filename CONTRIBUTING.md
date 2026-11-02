# 贡献指南

## 1. 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

静态前端预览：

```powershell
python -m http.server 8003 --directory app\static
```

## 2. 提交前检查

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\acceptance.py
.\.venv\Scripts\python.exe eval\run.py --golden
Get-ChildItem app\static\js -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

## 3. 代码约定

- 业务数字必须使用 Decimal；
- 不把数量、日期、缺口计算交给 LLM；
- 前端不自行推导缺口与交期；
- 新功能必须有 FR 编号测试；
- 不修改 golden 数据来让测试通过；
- 错误必须包含行号/列/原值/原因；
- 不提交密钥和真实业务数据。

## 4. 文档约定

- README 面向第一次打开仓库的人，先讲“解决什么问题”，再讲“怎么用”；
- 功能描述必须区分“前端 mock”和“后端真实 API”；
- 技术栈写版本和用途，不写空泛的“高性能”；
- 计算口径写公式和边界，不写“智能计算”；
- 已知限制必须写清楚，不能把未来计划写成已完成；
- 更新 API 时同步 `docs/API.md` 和 `docs/USAGE.md`。

## 5. 清理规则

只删除生产运行产物：

- `.env`
- `plan.db`
- `reports/`
- `reports/exports/*.xlsx`
- `reports/uvicorn*.log`
- `__pycache__/`、`.pytest_cache/`、`*.pyc`

不要删除文档、测试、样例、迁移、截图和 GitHub 工程文件。

## 6. PR 内容

- 说明改动目标；
- 列出受影响模块；
- 附验证命令和结果；
- 说明回滚方式；
- UI 改动附截图；
- 文档改动附链接和变更摘要。