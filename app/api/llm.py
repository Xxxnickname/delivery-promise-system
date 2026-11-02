"""模型配置状态接口：只报告是否配置，不返回 API Key。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.errors import api_ok


router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/status")
async def llm_status(request: Request):
    """返回可安全公开的模型配置状态。"""
    return api_ok(
        {
            "provider": settings.model_provider,
            "model": settings.model_name,
            "base_url": settings.model_base_url,
            "enabled": settings.llm_enabled,
            "api_key_configured": bool(settings.model_api_key),
            "timeout_seconds": settings.model_timeout_seconds,
        },
        trace_id=getattr(request.state, "trace_id", ""),
    )
