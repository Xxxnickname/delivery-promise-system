"""请求级租户与 trace_id 上下文。"""
from __future__ import annotations

import uuid
from contextvars import ContextVar


_tenant_id: ContextVar[str] = ContextVar("tenant_id", default="demo")
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    """生成短 trace_id，便于在响应和错误日志中串联一次请求。"""
    return f"tr_{uuid.uuid4().hex[:12]}"


def set_request_context(tenant_id: str, trace_id: str) -> tuple[object, object]:
    """设置当前请求上下文并返回 token，调用方应在 finally 中 reset。"""
    return _tenant_id.set(tenant_id or "demo"), _trace_id.set(trace_id or new_trace_id())


def reset_request_context(tokens: tuple[object, object]) -> None:
    """恢复上一个请求上下文，避免异步任务之间串租户。"""
    tenant_token, trace_token = tokens
    _tenant_id.reset(tenant_token)
    _trace_id.reset(trace_token)


def get_tenant_id() -> str:
    """获取当前租户标识，默认 demo 仅用于本地 G2 验证。"""
    return _tenant_id.get()


def get_trace_id() -> str:
    """获取当前 trace_id；没有中间件时回退为临时值。"""
    return _trace_id.get() or new_trace_id()
