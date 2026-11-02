"""导入模板、四表导入、错误 CSV 与 BOM 展开接口。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.api.auth import require_auth, require_roles
from app.core.errors import ApiError, ErrorCode, api_ok
from app.services.bom_expand import BomCycleError, BomDepthError, BomError
from app.services.import_batch import import_service


router = APIRouter(prefix="/api", dependencies=[Depends(require_roles("planner"))], tags=["imports"])


class BomExpandRequest(BaseModel):
    """BOM 展开请求；数量用 Decimal 接收，避免前端 float 进入计算层。"""

    batch_id: str
    root_code: str = Field(min_length=1)
    qty: Decimal = Field(gt=0)
    max_depth: int = Field(default=5, ge=1, le=5)


async def _read_upload(upload: UploadFile) -> bytes:
    """读取上传文件并执行大小限制，避免一次性占用过多内存。"""
    content = await upload.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ApiError(ErrorCode.VALIDATION, "文件超过大小限制", data={"filename": upload.filename, "max_mb": settings.max_upload_mb})
    return content


def _trace(request: Request) -> str:
    """优先使用中间件写入的 trace_id。"""
    return getattr(request.state, "trace_id", "")


@router.get("/templates/{table_type}")
async def download_template(table_type: str) -> Response:
    """下载指定表的 UTF-8 BOM CSV 模板。"""
    content = import_service.template(table_type)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{table_type}-template.csv"'},
    )


@router.post("/imports/bundle")
async def upload_bundle(
    request: Request,
    orders: UploadFile = File(...),
    bom: UploadFile = File(...),
    inventory: UploadFile = File(...),
    in_transit: UploadFile = File(...),
    mode: str = Form("ALL_OR_NOTHING"),
    allow_partial: bool = Form(False),
):
    """四表整体导入：任一表错误时按策略回滚或显式部分导入。"""
    files = {
        "orders": await _read_upload(orders),
        "bom": await _read_upload(bom),
        "inventory": await _read_upload(inventory),
        "in_transit": await _read_upload(in_transit),
    }
    batch = import_service.import_bundle(files, mode=mode, allow_partial=allow_partial)
    return api_ok(batch.to_dict(include_records=False), trace_id=_trace(request))


@router.get("/imports/{batch_id}")
async def get_import_batch(request: Request, batch_id: str, include_records: bool = Query(False)):
    """查询导入批次；include_records=true 时返回强类型转换后的有效记录。"""
    batch = import_service.get_batch(batch_id)
    return api_ok(batch.to_dict(include_records=include_records), trace_id=_trace(request))


@router.get("/imports/{batch_id}/errors.csv")
async def download_errors(batch_id: str):
    """下载错误 CSV，固定列为 row_no,column,value,reason。"""
    content = import_service.errors_csv(batch_id)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{batch_id}-errors.csv"'},
    )


@router.post("/bom/expand")
async def expand_bom_endpoint(request: Request, payload: BomExpandRequest):
    """从已提交批次展开指定成品 BOM；回滚批次会被拒绝。"""
    try:
        data = import_service.expand_order(
            payload.batch_id,
            payload.root_code,
            payload.qty,
            max_depth=payload.max_depth,
        )
    except BomCycleError as exc:
        raise ApiError(ErrorCode.BOM_CYCLE, str(exc), data={"path": exc.path}) from exc
    except BomDepthError as exc:
        raise ApiError(ErrorCode.BOM_DEPTH, str(exc)) from exc
    except BomError as exc:
        raise ApiError(ErrorCode.BOM_INVALID, str(exc)) from exc
    return api_ok(data, trace_id=_trace(request))

