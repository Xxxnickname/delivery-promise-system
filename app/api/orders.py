"""订单承诺、详情与缺口接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request, Depends

from app.api.auth import require_auth, require_roles
from app.core.errors import ApiError, ErrorCode, api_ok
from app.services.explain import explain_order
from app.services.import_batch import import_service


router = APIRouter(prefix="/api/orders", tags=["orders"], dependencies=[Depends(require_auth)])


def _trace(request: Request) -> str:
    return getattr(request.state, "trace_id", "")


def _resolve_batch(batch_id: str | None):
    """优先使用显式批次，否则回退当前租户最近一次已提交批次。"""
    if batch_id:
        return import_service.get_batch(batch_id)
    batch = import_service.latest_committed()
    if batch is None:
        raise ApiError(ErrorCode.NOT_FOUND, "还没有可计算的数据批次，请先导入四表", status_code=404)
    return batch


@router.get("")
async def list_orders(request: Request, q: str = Query(""), batch_id: str | None = None):
    """查询订单承诺列表；支持订单号、客户、成品料号搜索。"""
    batch = _resolve_batch(batch_id)
    promises = import_service.calculate_promises(batch.batch_id)
    keyword = q.strip().lower()
    payload = [
        promise.to_dict()
        for promise in promises
        if not keyword or any(keyword in str(value).lower() for value in (promise.order_no, promise.customer, promise.item_code))
    ]
    return api_ok({"batch_id": batch.batch_id, "calc_version": promises[0].calc_version if promises else "gen-1.0", "orders": payload}, trace_id=_trace(request))


@router.get("/{order_no}/promise")
async def get_order_promise(request: Request, order_no: str, batch_id: str | None = None):
    """读取单张订单的承诺结论；订单不存在返回 1002。"""
    batch = _resolve_batch(batch_id)
    promises = import_service.calculate_promises(batch.batch_id)
    for promise in promises:
        if promise.order_no == order_no:
            return api_ok(promise.to_dict(), trace_id=_trace(request))
    raise ApiError(ErrorCode.NOT_FOUND, "订单不存在", status_code=404, data={"order_no": order_no})


@router.get("/{order_no}")
async def get_order_detail(request: Request, order_no: str, batch_id: str | None = None):
    """订单详情与承诺接口同源，后续可扩展客户范围鉴权。"""
    return await get_order_promise(request, order_no, batch_id)


@router.get("/{order_no}/explain")
async def explain(request: Request, order_no: str, batch_id: str | None = None):
    """返回不含新数字的自然语言解释，只引用结构化承诺结果。"""
    batch = _resolve_batch(batch_id)
    promises = import_service.calculate_promises(batch.batch_id)
    for promise in promises:
        if promise.order_no == order_no:
            return api_ok({"order_no": order_no, "text": explain_order(promise)}, trace_id=_trace(request))
    raise ApiError(ErrorCode.NOT_FOUND, "订单不存在", status_code=404, data={"order_no": order_no})

