# 贡献指南

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

## 提交前检查

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\acceptance.py
.\.venv\Scripts\python.exe eval\run.py --golden
```

## 代码约定

- 业务数字必须使用 Decimal；
- 不把数量、日期、缺口计算交给 LLM；
- 前端不自行推导缺口与交期；
- 新功能必须有 FR 编号测试；
- 不修改 golden 数据来让测试通过；
- 错误必须包含行号/列/原值/原因；
- 不提交密钥和真实业务数据。

## PR 内容

- 说明改动目标；
- 列出受影响模块；
- 附验证命令和结果；
- 说明回滚方式；
- UI 改动附截图。
