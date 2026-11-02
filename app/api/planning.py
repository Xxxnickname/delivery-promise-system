"""模拟与快照 API。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query, Request, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.api.auth import require_auth, require_roles
from app.core.errors import ApiError, ErrorCode, api_ok
from app.services.bom_expand import edges_from_records
from app.services.import_batch import import_service
from app.services.promise import inventory_from_records, orders_from_records, transit_from_records
from app.services.simulate import simulate_change
from app.services.snapshot import snapshot_store


router = APIRouter(prefix="/api", tags=["planning"], dependencies=[Depends(require_auth)])


def _trace(request: Request) -> str:
    return getattr(request.state, "trace_id", "")


def _batch(batch_id: str | None):
    if batch_id:
        return import_service.get_batch(batch_id)
    batch = import_service.latest_committed()
    if batch is None:
        raise ApiError(ErrorCode.NOT_FOUND, "还没有可计算的数据批次", status_code=404)
    return batch


def _inputs(batch):
    """把批次记录转换成模拟所需的强类型输入。"""
    return (
        orders_from_records(batch.tables["orders"].records),
        edges_from_records(batch.tables["bom"].records),
        inventory_from_records(batch.tables["inventory"].records),
        transit_from_records(batch.tables["in_transit"].records),
    )


class SimulateRequest(BaseModel):
    """插单/加急请求；结果不落库。"""

    order_no: str
    mode: str = "insert"
    qty: Decimal = Field(gt=0)
    expect_date: date
    batch_id: str | None = None


@router.post("/simulate")
async def simulate(request: Request, payload: SimulateRequest):
    """计算插单/加急影响，明确返回 not_persisted=true。"""
    batch = _batch(payload.batch_id)
    orders, edges, inventory, transit = _inputs(batch)
    try:
        data = simulate_change(
            orders,
            edges,
            inventory,
            transit,
            order_no=payload.order_no,
            mode=payload.mode,
            qty=payload.qty,
            expect_date=payload.expect_date,
            as_of_date=date.today(),
            production_lead_days=settings.production_lead_days,
        )
    except ValueError as exc:
        raise ApiError(ErrorCode.VALIDATION, str(exc)) from exc
    data["batch_id"] = batch.batch_id
    return api_ok(data, trace_id=_trace(request))


@router.post("/snapshots")
async def create_snapshot(request: Request, batch_id: str | None = Query(None)):
    """从当前批次生成快照，供后续两次计算对比。"""
    batch = _batch(batch_id)
    promises = import_service.calculate_promises(batch.batch_id)
    snapshot = snapshot_store.create(promises, promises[0].calc_version if promises else "gen-1.0")
    return api_ok({"snapshot_id": snapshot.snapshot_id, "calc_version": snapshot.calc_version, "orders": len(snapshot.items)}, trace_id=_trace(request))


@router.get("/snapshots/compare")
async def compare_snapshots(request: Request, from_id: str = Query(alias="from"), to_id: str = Query(alias="to")):
    """按订单号对比两次快照。"""
    return api_ok(snapshot_store.compare(from_id, to_id), trace_id=_trace(request))

