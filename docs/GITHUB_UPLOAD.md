# GitHub 上传指南

## 推荐仓库名

- `delivery-promise-system`
- `order-promise-shortage-warning`
- `manufacturing-delivery-copilot`

## 上传前检查

```powershell
git status
```

确认以下内容不会进入 Git：

- `.env`
- `.venv/`
- `plan.db`
- `reports/uvicorn*.log`
- `reports/exports/`
- 任何真实客户、BOM、供应商数据

`.gitignore` 已配置排除。

## 初始化并上传

```powershell
git init
git add .
git commit -m "feat: deliver order promise and shortage warning system"
git branch -M main
git remote add origin https://github.com/Xxxnickname/delivery-promise-system.git
git push -u origin main
```

## 仓库简介

建议使用：

> 订单交期测算与缺料预警：四表导入、5 层 BOM 展开、供给冲减、交期承诺、场景模拟与快照对比。

## Topics

```text
manufacturing
supply-chain
delivery-promise
bom
shortage-warning
fastapi
pandas
vanilla-javascript
sqlalchemy
deepseek
```

## 首页展示

README 已包含：

- 项目概览
- 架构图
- 数据流程图
- 6 张界面预览
- 快速开始
- 33 条测试与 22 条边界验收结果
- 文档索引
- 当前边界

完整截图位于 `docs/screenshots/`，入口为 `docs/SCREENSHOTS.md`。

## 不要上传的内容

- `.env`：含 DeepSeek Key、JWT Secret、数据库密码
- `plan.db`：本地测试数据
- `reports/uvicorn*.log`：运行日志
- `reports/exports/*.xlsx`：导出文件
- 真实业务样本
