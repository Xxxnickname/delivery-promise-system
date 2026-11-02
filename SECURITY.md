# Security Policy

## 1. 报告安全问题

请通过 GitHub Security Advisory（推荐）或私下联系维护者，不要公开提交可利用漏洞。

## 2. 不应该提交的内容

- `.env`
- API Key、JWT Secret、数据库密码
- 真实客户订单、真实 BOM、真实供应商报价
- `plan.db`、导出文件、运行日志
- `reports/`、`reports/exports/`、`__pycache__/`

项目通过 `.gitignore` 排除了本地环境文件和数据库；提交前请再次运行：

```powershell
git status
```

## 3. 密钥管理

- DeepSeek Key 只放服务器环境变量；
- 通过 `Authorization: Bearer` 传输；
- 不在前端、URL、日志或报告中出现；
- 生产使用至少 32 字节 `AUTH_SECRET`；
- 更换 Key 后重建 app/worker 容器；
- 不在 Dockerfile、构建参数、Nginx 配置中写 Key；
- `/api/llm/status` 只返回是否配置，不返回 Key。

## 4. 当前安全边界

| 项目 | 当前状态 | 生产要求 |
|---|---|---|
| 登录 | JWT + PBKDF2 密码哈希 | 开启 `AUTH_REQUIRED=true` |
| 角色 | 前端菜单控制；后端导入/模板/BOM 限制 planner/admin | 为订单、导出、模拟补细粒度角色 |
| 客户范围 | 用户表有 `customer_scopes`；后端订单查询未强制过滤 | 查询层按客户范围过滤 |
| 租户 | `X-Tenant-Id` 参与上下文，未与 JWT 强绑定 | 从 JWT 读取租户，禁止客户端任意指定 |
| 导出归属 | 登录后优先 JWT 账号；未登录开发模式回退 `X-User-Id` | 生产不信任 `X-User-Id` |
| 审计 | 表结构与 `audit()` 已建，业务未调用 | 导入/查询/导出/权限变更落审计 |
| 上传 | 有大小限制、CSV 严格校验 | 增加病毒扫描/频率限制 |
| 模型 | 只做表头映射，失败回退规则 | 继续禁止模型算数 |

## 5. 生产安全检查

- `AUTH_REQUIRED=true`
- 关闭公开注册（当前无注册接口）
- 反向代理启用 HTTPS
- 限制上传大小和请求频率
- 定期轮换 JWT Secret 与模型 Key
- 备份数据库并演练恢复
- 对 `X-Trace-Id` 做日志关联，但不记录 Authorization
- 不在日志中打印完整 CSV 内容或客户敏感字段

## 6. 漏洞处理建议

1. 立即停止暴露受影响接口；
2. 轮换 `AUTH_SECRET` 和模型 Key；
3. 保留日志和 `trace_id`；
4. 修复后补回归测试和权限测试；
5. 如涉及真实客户数据，按企业数据安全流程上报。