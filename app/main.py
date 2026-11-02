"""FastAPI 应用入口：业务 API + 静态前端。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.export import router as export_router
from app.api.imports import router as imports_router
from app.api.llm import router as llm_router
from app.api.orders import router as orders_router
from app.api.planning import router as planning_router
from app.core.config import settings
from app.core.db import init_db, seed_demo_users
from app.core.errors import ApiError, ErrorCode, api_error_payload
from app.core.tenant import get_tenant_id, new_trace_id, reset_request_context, set_request_context
from app.services.import_batch import import_service


logger = logging.getLogger("plan")
APP_VERSION = "0.3.0-g3-g4"


def bootstrap_demo_batch() -> None:
    """本地开发启动时若无批次，自动导入 samples/03，保证前端/API 有演示数据。"""
    if import_service.latest_committed(get_tenant_id()) is not None:
        return
    base = settings.samples_dir
    files = {
        "orders": (base / "orders.csv").read_bytes(),
        "bom": (base / "bom.csv").read_bytes(),
        "inventory": (base / "inventory.csv").read_bytes(),
        "in_transit": (base / "in_transit.csv").read_bytes(),
    }
    import_service.import_bundle(files)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化演示数据；关闭时无需额外清理。"""
    init_db()
    seed_demo_users()
    bootstrap_demo_batch()
    yield


app = FastAPI(title=settings.app_name, version=APP_VERSION, lifespan=lifespan)
init_db()
seed_demo_users()


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """为每个请求注入租户和 trace_id，并在响应头回传 trace_id。"""
    tenant_id = request.headers.get("X-Tenant-Id", "demo")
    trace_id = request.headers.get("X-Trace-Id") or new_trace_id()
    request.state.tenant_id = tenant_id
    request.state.trace_id = trace_id
    tokens = set_request_context(tenant_id, trace_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_context(tokens)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    """业务异常统一返回 code/message/data/trace_id。"""
    trace_id = getattr(request.state, "trace_id", "")
    return JSONResponse(status_code=exc.status_code, content=api_error_payload(exc, trace_id=trace_id))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """请求参数错误统一映射为 1001，并保留 FastAPI 字段定位。"""
    trace_id = getattr(request.state, "trace_id", "")
    error = ApiError(ErrorCode.VALIDATION, "请求参数不合法", status_code=422, data=exc.errors())
    return JSONResponse(status_code=422, content=api_error_payload(error, trace_id=trace_id))


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    """兜底 500 响应；详细堆栈只写日志，不泄露给前端。"""
    logger.exception("未处理异常", exc_info=exc)
    trace_id = getattr(request.state, "trace_id", "")
    error = ApiError(5000, "服务内部错误", status_code=500)
    return JSONResponse(status_code=500, content=api_error_payload(error, trace_id=trace_id))


@app.get("/health")
async def health():
    """健康检查：启动门禁和容器 healthcheck。"""
    return {
        "status": "ok",
        "service": "delivery-promise",
        "version": APP_VERSION,
        "port": settings.app_port,
        "timezone": settings.timezone,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


app.include_router(auth_router)
app.include_router(imports_router)
app.include_router(llm_router)
app.include_router(orders_router)
app.include_router(planning_router)
app.include_router(export_router)
app.mount("/", StaticFiles(directory=str(settings.static_dir), html=True), name="static")



