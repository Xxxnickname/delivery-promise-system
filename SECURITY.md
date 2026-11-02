# Security Policy

## 报告安全问题

请通过 GitHub Security Advisory（推荐）或私下联系维护者，不要公开提交可利用漏洞。

## 不应该提交的内容

- `.env`
- API Key、JWT Secret、数据库密码
- 真实客户订单、真实 BOM、真实供应商报价
- `plan.db`、导出文件、运行日志

项目通过 `.gitignore` 排除了本地环境文件和数据库；提交前请再次运行：

```powershell
git status
```

## 密钥管理

- DeepSeek Key 只放服务器环境变量；
- 通过 `Authorization: Bearer` 传输；
- 不在前端、URL、日志或报告中出现；
- 生产使用至少 32 字节 `AUTH_SECRET`；
- 更换 Key 后重建 app/worker 容器。

## 生产安全检查

- `AUTH_REQUIRED=true`
- 关闭公开注册
- 反向代理启用 HTTPS
- 限制上传大小和请求频率
- 定期轮换 JWT Secret 与模型 Key
- 备份数据库并演练恢复
