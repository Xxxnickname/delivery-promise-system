# GitHub 上传指南

## 1. 仓库信息

- 仓库：`https://github.com/Xxxnickname/delivery-promise-system`
- 分支：`main`
- 作者：`Xxxnickname`
- License：MIT

## 2. 上传前检查

```powershell
git status
git log -1 --format='%an <%ae> %s'
```

确认以下内容不会进入 Git：

- `.env`
- `.venv/`
- `plan.db`
- `reports/uvicorn*.log`
- `reports/exports/`
- `__pycache__/`、`.pytest_cache/`、`*.pyc`
- 任何真实客户、BOM、供应商数据

`.gitignore` 已配置排除。

## 3. 初始化并上传

```powershell
git init
git add .
git commit -m "feat: initial release of delivery promise and shortage warning system"
git branch -M main
git remote add origin https://github.com/Xxxnickname/delivery-promise-system.git
git push -u origin main
```

如果仓库已有提交，先 `git pull --rebase origin main`，再推送。

## 4. 仓库简介

建议使用：

> 订单交期测算与缺料预警：四表导入、5 层 BOM 展开、供给冲减、交期承诺、场景模拟与快照对比。

## 5. Topics

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

## 6. 首页展示

README 已包含：

- 项目定位与业务问题
- 角色与典型流程
- 功能地图（前端 mock / 后端 API）
- 两种运行方式与 5 分钟启动
- 四表准备与计算口径
- 系统架构与技术栈
- API 速查
- 数据持久化说明
- 配置项、测试结果、当前边界
- 常见问题与安全说明

完整截图位于 `docs/screenshots/`，入口为 `docs/SCREENSHOTS.md`，共 12 张。

## 7. 不要上传的内容

- `.env`：含 DeepSeek Key、JWT Secret、数据库密码
- `plan.db`：本地测试数据
- `reports/uvicorn*.log`：运行日志
- `reports/exports/*.xlsx`：导出文件
- `__pycache__/`、`.pytest_cache/`
- 真实业务样本

## 8. 清理原则

清理的是生产运行产物，不是文档内容：

- 删除：`.env`、`plan.db`、`reports/`、缓存、日志、导出文件；
- 保留：`app/`、`tests/`、`samples/`、`migrations/`、`docs/`、截图、README、LICENSE、`.github/`、Docker/依赖文件。