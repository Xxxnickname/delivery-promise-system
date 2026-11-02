"""脏表头抽取：规则优先，可选 DeepSeek JSON 映射。"""
from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.services.alias import TABLE_SCHEMAS, normalize_headers
from app.services.llm_client import LlmClient, LlmUnavailable


def rule_based_header_mapping(headers: list[str], table_type: str) -> dict[str, str]:
    """根据别名规则返回原表头 -> 标准字段的映射建议。"""
    normalized = normalize_headers(headers)
    mapping: dict[str, str] = {}
    for original, canonical in zip(headers, normalized):
        if canonical in TABLE_SCHEMAS.get(table_type, []):
            mapping[original] = canonical
    return mapping


def _build_client() -> LlmClient:
    """从环境配置构造客户端；Key 不进入任何前端响应。"""
    return LlmClient(
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        model=settings.model_name,
        timeout=settings.model_timeout_seconds,
    )


def suggest_header_mapping(headers: list[str], table_type: str, use_llm: bool | None = None, client: LlmClient | None = None) -> dict[str, object]:
    """返回可审计的表头映射建议。

    模型只返回 JSON 映射建议，服务端再次白名单校验；失败时回退规则映射。
    """
    rules = rule_based_header_mapping(headers, table_type)
    enabled = settings.llm_enabled if use_llm is None else bool(use_llm and settings.llm_enabled)
    if not enabled:
        return {"table_type": table_type, "mapping": rules, "source": "rules", "llm_enabled": False, "note": "模型未启用，使用规则映射"}

    allowed = set(TABLE_SCHEMAS.get(table_type, []))
    system_prompt = "你是ERP表头映射器。只返回JSON对象，内容为 original_header -> canonical_column。不得编造字段，不得计算结果。"
    user_prompt = json.dumps({"table_type": table_type, "headers": headers, "allowed_columns": sorted(allowed)}, ensure_ascii=False)
    try:
        payload = (client or _build_client()).complete_json(system_prompt, user_prompt)
        raw_mapping = payload.get("mapping", payload)
        mapping = {
            str(original): str(canonical)
            for original, canonical in raw_mapping.items()
            if original in headers and canonical in allowed
        }
        if not mapping:
            raise ValueError("模型未返回有效映射")
        merged = {**rules, **mapping}
        return {"table_type": table_type, "mapping": merged, "source": "llm+rules", "llm_enabled": True, "note": "模型建议已通过字段白名单校验"}
    except (LlmUnavailable, ValueError, KeyError, TypeError, RuntimeError, OSError, httpx.HTTPError) as exc:
        return {"table_type": table_type, "mapping": rules, "source": "rules", "llm_enabled": False, "note": f"模型映射失败，已回退规则：{exc}"}

