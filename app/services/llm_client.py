"""DeepSeek/OpenAI-compatible 模型客户端。

安全边界：
1. API Key 只从后端环境变量读取；
2. 只通过 Authorization: Bearer 头传输；
3. 不写入页面、URL、日志或响应；
4. 模型只返回 JSON 建议，业务数字仍由服务端代码计算。
"""
from __future__ import annotations

import json
from typing import Any

import httpx


class LlmUnavailable(RuntimeError):
    """未启用模型或缺少配置。"""


class LlmClient:
    """OpenAI-compatible Chat Completions 客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)

    @property
    def enabled(self) -> bool:
        """缺少 Key 或地址时保持禁用，调用方应回退规则抽取。"""
        return bool(self.api_key and self.base_url and self.model)

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """调用 /chat/completions，并要求模型返回 JSON 对象。"""
        if not self.enabled:
            raise LlmUnavailable("模型未启用或缺少 MODEL_API_KEY/MODEL_BASE_URL/MODEL_NAME")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = self._client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, dict):
            return content
        text = str(content).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
