"""服务端 xlsx 导出接口与任务轮询。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Header, Request, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.auth import require_auth, require_roles
from app.core.errors import ApiError, ErrorCode, api_ok
from app.services.export_service import export_service
from app.services.import_batch import import_service
from app.services.snapshot import snapshot_store


router = APIRouter(prefix="/api/export", tags=["export"], dependencies=[Depends(require_auth)])


class ExportRequest(BaseModel):
    """导出请求：齐套报告或快照差异。"""

    kind: str
    batch_id: str | None = None
    from_snapshot: str | None = None
    to_snapshot: str | None = None


def _trace(request: Request) -> str:
    return getattr(request.state, "trace_id", "")


def _rows_for_request(payload: ExportRequest) -> tuple[list[dict[str, Any]], str]:
    """把业务结果拍平成 xlsx 行；所有数值保持字符串，避免 float 精度漂移。"""
    if payload.kind == "kit_report":
        batch = import_service.get_batch(payload.batch_id) if payload.batch_id else import_service.latest_committed()
        if batch is None:
            raise ApiError(ErrorCode.NOT_FOUND, "没有可导出的计算批次", status_code=404)
        promises = import_service.calculate_promises(batch.batch_id)
        rows = []
        for promise in promises:
            gaps = "; ".join(f"{gap.item_code}:{gap.gap}" for gap in promise.gaps)
            rows.append({
                "order_no": promise.order_no,
                "customer": promise.customer,
                "item_code": promise.item_code,
                "qty": format(promise.qty, "f"),
                "due_date": promise.due_date.isoformat(),
                "kit_date": promise.kit_date.isoformat() if promise.kit_date else "",
                "earliest_start_date": promise.earliest_start_date.isoformat() if promise.earliest_start_date else "",
                "can_commit": promise.can_commit,
                "delay_days": promise.delay_days,
                "gaps": gaps,
                "calc_version": promise.calc_version,
            })
        return rows, "kit_report"
    if payload.kind == "snapshot_diff":
        if not payload.from_snapshot or not payload.to_snapshot:
            raise ApiError(ErrorCode.VALIDATION, "快照比较需要 from_snapshot 和 to_snapshot")
        data = snapshot_store.compare(payload.from_snapshot, payload.to_snapshot)
        return data["items"], "snapshot_diff"
    raise ApiError(ErrorCode.VALIDATION, "不支持的导出类型", data={"kind": payload.kind})


@router.post("")
async def create_export(request: Request, payload: ExportRequest, x_user_id: str = Header("demo", alias="X-User-Id")):
    """创建 xlsx 导出任务；同用户同时只允许一个任务。"""
    rows, sheet_name = _rows_for_request(payload)
    task = export_service.create(x_user_id, payload.kind, rows, sheet_name)
    return api_ok(task.to_dict(), trace_id=_trace(request))


@router.get("/{task_id}")
async def get_export(request: Request, task_id: str):
    """轮询导出任务状态。"""
    task = export_service.get(task_id)
    return api_ok(task.to_dict(), trace_id=_trace(request))


@router.get("/{task_id}/download")
async def download_export(task_id: str):
    """下载已完成的 xlsx 文件。"""
    task = export_service.get(task_id)
    if task.status != "SUCCESS" or not task.file_path:
        raise ApiError(ErrorCode.NOT_FOUND, "导出文件尚未生成", status_code=409, data=task.to_dict())
    return FileResponse(task.file_path, filename=f"{task.kind}-{date.today().isoformat()}.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

