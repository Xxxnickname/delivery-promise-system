import json

import httpx

from app.services.llm_client import LlmClient


def test_deepseek_key_is_sent_only_in_authorization_header():
    """DeepSeek Key 只放 Authorization Bearer 头，不进 URL/Body。"""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{\"mapping\": {\"料号\": \"item_code\"}}"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    llm = LlmClient(base_url="https://api.deepseek.com", api_key="test-key", model="deepseek-chat", client=http_client)
    payload = llm.complete_json("system", "user")
    assert payload == {"mapping": {"料号": "item_code"}}
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert "test-key" not in json.dumps(seen["body"], ensure_ascii=False)
    assert seen["body"]["model"] == "deepseek-chat"
    assert seen["body"]["temperature"] == 0
