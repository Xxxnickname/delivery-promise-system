# DeepSeek / OpenAI-compatible 传参说明

## 1. 作用范围

模型在本项目中只做一件事：

> 当四张 CSV 的表头无法被规则识别时，给出 `原始表头 -> 标准字段` 的映射建议。

模型不参与：

- 数量、金额、缺口计算；
- 交期、齐套日、最早开工日计算；
- BOM 展开结果；
- 订单承诺判断；
- 订单解释文案（解释由确定性模板生成）。

## 2. 环境变量

```env
MODEL_PROVIDER=deepseek
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
# MODEL_API_KEY 由服务器环境变量注入，仓库内不填写
LLM_ENABLED=true
MODEL_TIMEOUT_SECONDS=20
```

| 变量 | 说明 |
|---|---|
| `MODEL_PROVIDER` | 供应商标识，当前仅用于状态展示 |
| `MODEL_BASE_URL` | OpenAI-compatible Base URL，不含 `/chat/completions` |
| `MODEL_NAME` | 模型名，当前 `deepseek-flash` |
| `MODEL_API_KEY` | 只放服务器环境变量或本地 `.env` |
| `LLM_ENABLED` | `false` 时只用规则映射；默认 `false` |
| `MODEL_TIMEOUT_SECONDS` | 请求超时，默认 20 秒 |

## 3. 实际请求

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

实现位置：`app/services/llm_client.py`、`app/services/llm_extract.py`。

## 4. 调用流程

1. `parse_tables.py` 先用 `alias.py` 的规则归一表头；
2. 如果仍有必填列缺失，且 `LLM_ENABLED=true`，调用 `suggest_header_mapping()`；
3. 模型返回 JSON 映射；
4. 服务端只接受：

   - key 必须在该 CSV 的原始表头中；
   - value 必须在 `TABLE_SCHEMAS[table_type]` 白名单中；

5. 合并规则映射与模型映射；
6. 仍缺列、超时、网络错误、Key 缺失或返回非法 JSON 时，自动回退规则映射。

## 5. 为什么不让模型算数

- 业务数字必须可复算、可对账；
- 模型输出不稳定，不能作为承诺依据；
- 数量/日期一旦由模型生成，无法保证同一输入同一输出；
- 因此模型只输出“字段映射建议”，不输出业务数值。

## 6. 状态接口

```http
GET /api/llm/status
```

返回：

```json
{
  "provider": "deepseek",
  "model": "deepseek-flash",
  "base_url": "https://api.deepseek.com",
  "enabled": false,
  "api_key_configured": false,
  "timeout_seconds": 20
}
```

只返回 `api_key_configured` 布尔值，不返回 Key 内容。

## 7. 安全原则

- 不在前端调用 DeepSeek；
- 不把 Key 写入 Git、URL、日志或报告；
- 不记录完整 `Authorization` 头；
- 不在 Dockerfile 中写 Key；
- 不用 `docker build --build-arg` 传 Key；
- 生产用服务器环境变量或 Docker secret；
- 更换 Key 后重建 app/worker 容器。

## 8. 服务器上怎么改

只改模型配置时，不需要重建镜像，也不需要改代码：

```bash
cd /srv/plan
nano .env
docker compose up -d --force-recreate app worker
curl -s http://127.0.0.1:8003/api/llm/status
```

建议权限：

```bash
chmod 600 .env
```

## 9. 实测状态

- 2026-11-02 使用 `deepseek-flash` 完成一次真实表头映射调用（项目记录）；
- 测试列“奇怪订单号列”成功映射为 `order_no`，导入批次 `COMMITTED`；
- 实测未在输出、URL 或请求体中暴露 API Key；
- CI 不依赖真实 Key；`tests/test_deepseek_client.py` 使用 MockTransport 验证“Key 只出现在 Authorization 头”。

## 10. 常见问题

**Q：没有 Key 能不能跑？**

A：能。`LLM_ENABLED=false` 或 Key 为空时，表头映射走规则；业务计算完全不受影响。

**Q：模型返回了不存在的字段怎么办？**

A：服务端白名单会丢弃，仍缺列则导入报错或回退规则，不会把未知字段写进业务。

**Q：解释文案是模型生成的吗？**

A：不是。`app/services/explain.py` 是确定性模板，不调用模型，且文案不含具体数字，避免篡改计算结果。