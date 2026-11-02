# DeepSeek API 传参说明

## 环境变量

```env
MODEL_PROVIDER=deepseek
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
# MODEL_API_KEY 由服务器环境变量注入，仓库内不填写
LLM_ENABLED=true
MODEL_TIMEOUT_SECONDS=20
```

- `MODEL_API_KEY` 只放后端 `.env`、Docker secret 或服务器环境变量。
- 前端、浏览器 localStorage、URL、日志、接口响应都不能出现 Key。
- 如果使用 Rose/其他 OpenAI 兼容中转，只改 `MODEL_BASE_URL` 和 `MODEL_NAME`。
- 当前项目实际使用 `MODEL_NAME=deepseek-flash`，并已用该模型完成一次表头映射实调。若服务商不支持该别名，再改为其提供的模型名。

## 实际请求

```http
POST https://api.deepseek.com/chat/completions
Authorization: Bearer <MODEL_API_KEY>
Content-Type: application/json
```

```json
{
  "model": "deepseek-flash",
  "messages": [
    {"role": "system", "content": "只返回 JSON"},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0,
  "response_format": {"type": "json_object"}
}
```

Service 端实现：`app/services/llm_client.py`。  
Key 通过 `Authorization` 头传输，不进入请求体；模型输出会经过字段白名单校验，失败自动回退规则映射。

## 安全原则

- 不在前端调用 DeepSeek。
- 不把 Key 写入 Git 或报告。
- 不记录完整 Authorization 头。
- 模型只做表头抽取/解释，不做任何数量、日期、缺口计算。


## 实测状态

- 2026-11-02 使用 `deepseek-flash` 完成一次真实表头映射调用。
- 测试列“奇怪订单号列”成功映射为 `order_no`，导入批次 `COMMITTED`。
- 实测未在输出、URL 或请求体中暴露 API Key。
## 部署到服务器后怎么改

只改模型配置时，不需要重建镜像，也不需要改代码：

```bash
cd /srv/plan
nano .env
docker compose up -d --force-recreate app worker
curl -s http://127.0.0.1:8003/api/llm/status
```

`/api/llm/status` 只返回模型名、地址、是否启用、Key 是否已配置，不返回 Key 内容。

建议服务器文件权限：

```bash
chmod 600 .env
```

不要执行：

- 不要把 `.env` 提交 Git；
- 不要把 Key 写进 Dockerfile；
- 不要用 `docker build --build-arg` 传 Key；
- 不要把 Key 放到前端或 Nginx 配置。


