from types import SimpleNamespace

import app.services.llm_extract as llm_extract
import app.services.parse_tables as parse_tables
from app.services.parse_tables import parse_table


class FakeLlm:
    def complete_json(self, system_prompt, user_prompt):
        return {"mapping": {"怪列": "order_no"}}


def test_llm_header_mapping_only_when_rules_missing(monkeypatch):
    """规则缺列时调用模型，模型映射通过白名单后进入解析。"""
    monkeypatch.setattr(parse_tables, "settings", SimpleNamespace(llm_enabled=True))
    monkeypatch.setattr(llm_extract, "settings", SimpleNamespace(llm_enabled=True, model_base_url="x", model_api_key="y", model_name="z", model_timeout_seconds=1))
    monkeypatch.setattr(llm_extract, "_build_client", lambda: FakeLlm())
    content = "怪列,物料编码,数量,交期\nSO-LLM-1,FG-100,1,2026-12-01\n".encode("utf-8")
    table = parse_table("orders", content)
    assert table.ok
    assert table.headers[0] == "order_no"
    assert table.records[0]["order_no"] == "SO-LLM-1"
