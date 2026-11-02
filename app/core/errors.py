"""统一错误对象与响应结构。"""
from __future__ import annotations

from typing import Any

from app.core.tenant import get_trace_id


class ApiError(Exception):
    """业务异常：携带统一错误码、HTTP 状态码和可定位的附加数据。"""

    def __init__(self, code: int, message: str, status_code: int = 400, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data


class ErrorCode:
    """G2 阶段使用的稳定错误码，后续 API 不得随意重排。"""

    VALIDATION = 1001
    NOT_FOUND = 1002
    IMPORT_ROLLED_BACK = 1003
    DUPLICATE = 1004
    BOM_CYCLE = 1101
    BOM_DEPTH = 1102
    BOM_INVALID = 1103


def api_ok(data: Any = None, message: str = "ok", trace_id: str | None = None) -> dict[str, Any]:
    """构造成功响应，数量和金额字符串由服务层负责，避免 float 误差。"""
    return {"code": 0, "message": message, "data": data, "trace_id": trace_id or get_trace_id()}


def api_error_payload(error: ApiError, trace_id: str | None = None) -> dict[str, Any]:
    """构造失败响应；错误详情优先放在 data，便于前端定位行号/列/原值。"""
    return {"code": error.code, "message": error.message, "data": error.data, "trace_id": trace_id or get_trace_id()}

