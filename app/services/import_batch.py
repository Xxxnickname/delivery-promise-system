"""导入批次、幂等、全或无提交与错误 CSV 生成。

G2 的内存实现用于接口和算法联调：只有全部解析成功才提交有效记录；
默认出现任何错误即整批回滚。显式允许部分导入时才保留成功行并留痕。
后续接入 PostgreSQL 时，保持同样的批次状态机即可替换存储层。
"""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.core.tenant import get_tenant_id
from app.models.domain import ImportErrorRow, ParsedTable
from app.services.bom_expand import edges_from_records, expand_bom
from app.services.parse_tables import parse_table
from app.services.promise import calculate_promises, inventory_from_records, orders_from_records, transit_from_records


IMPORT_TYPES = ("orders", "bom", "inventory", "in_transit")
TEMPLATE_ROWS: dict[str, str] = {
    "orders": "order_no,item_code,qty,due_date,customer\nSO-DEMO-001,FG-100,10,2026-12-01,演示客户",
    "bom": "parent_code,child_code,qty_per,scrap_rate,substitute_group,level\nFG-100,SUB-L1,1.000000,0.0000,,1",
    "inventory": "item_code,on_hand,allocated,warehouse\nRM-005,80.000000,0.000000,WH-R1",
    "in_transit": "item_code,qty,eta_date,batch_no,supplier\nRM-005,50.000000,2026-11-20,PO-DEMO-001,演示供应商",
}


def _json_value(value: Any) -> Any:
    """把 Decimal/date 等强类型值转换为可安全返回的 JSON 值。"""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _table_dict(table: ParsedTable) -> dict[str, Any]:
    """输出单表摘要和数据；错误行保持契约字段顺序。"""
    return {
        "table_type": table.table_type,
        "ok": table.ok,
        "headers": table.headers,
        "ok_rows": table.ok_rows,
        "failed_rows": len(table.errors),
        "records": [_json_value(record) for record in table.records],
        "errors": [error.to_dict() for error in table.errors],
    }


@dataclass
class ImportBatch:
    """一次四表导入的状态快照。"""

    batch_id: str
    tenant_id: str
    mode: str
    status: str
    file_hash: str
    created_at: datetime
    tables: dict[str, ParsedTable] = field(default_factory=dict)
    committed: bool = False
    raw_files: dict[str, bytes] = field(default_factory=dict, repr=False)

    @property
    def errors(self) -> list[ImportErrorRow]:
        """汇总四张表的错误行，保持表类型、行号、列、原值、原因可追溯。"""
        return [error for table in self.tables.values() for error in table.errors]

    @property
    def ok_rows(self) -> int:
        return sum(table.ok_rows for table in self.tables.values())

    @property
    def failed_rows(self) -> int:
        return len(self.errors)

    @property
    def total_rows(self) -> int:
        return self.ok_rows + self.failed_rows

    @property
    def imported_rows(self) -> int:
        """只有已提交批次才计入实际入库行；回滚批次必须为 0。"""
        return self.ok_rows if self.committed else 0

    def to_dict(self, include_records: bool = False) -> dict[str, Any]:
        """输出 API 响应；列表页可关闭 records 以减少传输量。"""
        table_summaries = []
        for table_type in IMPORT_TYPES:
            table = self.tables.get(table_type)
            if table is None:
                table_summaries.append({
                    "table_type": table_type,
                    "ok": False,
                    "ok_rows": 0,
                    "failed_rows": 1,
                    "errors": [{"row_no": 1, "column": "file", "value": "", "reason": "缺少文件"}],
                })
            elif include_records:
                table_summaries.append(_table_dict(table))
            else:
                table_summaries.append({
                    "table_type": table_type,
                    "ok": table.ok,
                    "ok_rows": table.ok_rows,
                    "failed_rows": len(table.errors),
                    "errors": [error.to_dict() for error in table.errors],
                })
        return {
            "batch_id": self.batch_id,
            "tenant_id": self.tenant_id,
            "mode": self.mode,
            "status": self.status,
            "file_hash": self.file_hash,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "ok_rows": self.ok_rows,
            "failed_rows": self.failed_rows,
            "imported_rows": self.imported_rows,
            "committed": self.committed,
            "error_file": f"/api/imports/{self.batch_id}/errors.csv",
            "tables": table_summaries,
        }


class ImportService:
    """内存导入服务；同一租户、同一文件哈希和同一模式返回同一批次。"""

    def __init__(self, persist: bool = False) -> None:
        self._batches: dict[str, ImportBatch] = {}
        self._idempotency: dict[tuple[str, str, str], str] = {}
        self.persist = persist

    @staticmethod
    def content_hash(files: dict[str, bytes]) -> str:
        """按表类型排序后计算 SHA-256，文件内容相同即视为同一批次。"""
        digest = hashlib.sha256()
        for table_type in sorted(files):
            digest.update(table_type.encode("utf-8"))
            digest.update(b"\0")
            digest.update(files[table_type])
            digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def template(table_type: str) -> str:
        """返回含表头与示例行的模板；类型非法时抛出 1001。"""
        if table_type not in TEMPLATE_ROWS:
            raise ApiError(ErrorCode.VALIDATION, "不支持的表类型", data={"type": table_type})
        return "\ufeff" + TEMPLATE_ROWS[table_type] + "\n"

    def import_bundle(
        self,
        files: dict[str, bytes],
        *,
        mode: str = "ALL_OR_NOTHING",
        allow_partial: bool = False,
    ) -> ImportBatch:
        """解析四表并按全或无/显式部分导入规则生成批次。

        - mode=ALL_OR_NOTHING：有错误时 committed=False、imported_rows=0；
        - mode=PARTIAL_WITH_AUDIT 且 allow_partial=True：保留成功行并标记部分导入；
        - 未显式允许部分导入时拒绝该模式，避免前端误操作。
        """
        if mode not in {"ALL_OR_NOTHING", "PARTIAL_WITH_AUDIT"}:
            raise ApiError(ErrorCode.VALIDATION, "导入模式非法", data={"mode": mode})
        if mode == "PARTIAL_WITH_AUDIT" and not allow_partial:
            raise ApiError(ErrorCode.VALIDATION, "部分导入必须显式确认", data={"allow_partial": False})

        tenant_id = get_tenant_id()
        hash_value = self.content_hash(files)
        idem_key = (tenant_id, mode, hash_value)
        if idem_key in self._idempotency:
            return self._batches[self._idempotency[idem_key]]

        tables: dict[str, ParsedTable] = {}
        for table_type in IMPORT_TYPES:
            content = files.get(table_type)
            if content is None:
                tables[table_type] = ParsedTable(
                    table_type=table_type,
                    errors=[ImportErrorRow(1, "file", "", "缺少文件")],
                )
            else:
                tables[table_type] = parse_table(table_type, content)

        has_errors = any(table.errors for table in tables.values())
        valid_rows = sum(table.ok_rows for table in tables.values())
        if has_errors and mode == "ALL_OR_NOTHING":
            status = "ROLLED_BACK"
            committed = False
        elif has_errors and valid_rows == 0:
            status = "ROLLED_BACK"
            committed = False
        elif has_errors:
            status = "PARTIAL_IMPORTED"
            committed = True
        else:
            status = "COMMITTED"
            committed = True

        now = datetime.now()
        batch_id = f"ib_{now:%Y%m%d%H%M%S%f}_{hash_value[:8]}_{mode[:3]}"
        batch = ImportBatch(
            batch_id=batch_id,
            tenant_id=tenant_id,
            mode=mode,
            status=status,
            file_hash=hash_value,
            created_at=now,
            tables=tables,
            committed=committed,
            raw_files=dict(files),
        )
        self._batches[batch_id] = batch
        self._idempotency[idem_key] = batch_id
        if self.persist:
            from app.core.db import save_import_batch
            save_import_batch(batch)
        return batch

    def latest_committed(self, tenant_id: str | None = None) -> ImportBatch | None:
        """返回当前租户最近一次已提交批次；G3 API 默认使用该批次。"""
        tid = tenant_id or get_tenant_id()
        candidates = [batch for batch in self._batches.values() if batch.tenant_id == tid and batch.committed]
        if not candidates and self.persist:
            from app.core.db import latest_import_batch
            persisted = latest_import_batch(tid)
            if persisted is not None:
                self._batches[persisted.batch_id] = persisted
                candidates = [persisted]
        return max(candidates, key=lambda batch: batch.created_at) if candidates else None

    def calculate_promises(self, batch_id: str, as_of_date: date | None = None):
        """从批次中的四表计算订单承诺；回滚批次禁止继续计算。"""
        batch = self.get_batch(batch_id)
        if not batch.committed:
            raise ApiError(ErrorCode.IMPORT_ROLLED_BACK, "批次已回滚，不能计算交期", data={"batch_id": batch_id})
        for table_type in ("orders", "bom", "inventory", "in_transit"):
            table = batch.tables.get(table_type)
            if table is None or not table.records:
                raise ApiError(ErrorCode.VALIDATION, f"批次缺少有效 {table_type} 数据", data={"batch_id": batch_id})
        return calculate_promises(
            orders_from_records(batch.tables["orders"].records),
            edges_from_records(batch.tables["bom"].records),
            inventory_from_records(batch.tables["inventory"].records),
            transit_from_records(batch.tables["in_transit"].records),
            as_of_date=as_of_date or date.today(),
            production_lead_days=settings.production_lead_days,
        )

    def get_batch(self, batch_id: str) -> ImportBatch:
        """读取当前租户的批次；不存在或跨租户统一返回 1002。"""
        batch = self._batches.get(batch_id)
        if batch is None and self.persist:
            from app.core.db import load_import_batch
            batch = load_import_batch(batch_id, get_tenant_id())
            if batch is not None:
                self._batches[batch_id] = batch
        if batch is None or batch.tenant_id != get_tenant_id():
            raise ApiError(ErrorCode.NOT_FOUND, "导入批次不存在", status_code=404)
        return batch

    def errors_csv(self, batch_id: str) -> str:
        """生成错误 CSV，列固定为 row_no,column,value,reason。"""
        batch = self.get_batch(batch_id)
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["row_no", "column", "value", "reason"])
        for table in batch.tables.values():
            for error in table.errors:
                writer.writerow([error.row_no, error.column, error.value, error.reason])
        return "\ufeff" + output.getvalue()

    def expand_order(self, batch_id: str, root_code: str, qty: Decimal, max_depth: int = 5) -> dict[str, Any]:
        """从已提交/部分提交批次中展开 BOM；回滚批次禁止继续计算。"""
        batch = self.get_batch(batch_id)
        if not batch.committed:
            raise ApiError(ErrorCode.IMPORT_ROLLED_BACK, "批次已回滚，不能执行 BOM 展开", data={"batch_id": batch_id})
        bom_table = batch.tables.get("bom")
        if bom_table is None or not bom_table.records:
            raise ApiError(ErrorCode.BOM_INVALID, "批次中没有有效 BOM 数据", data={"batch_id": batch_id})
        edges = edges_from_records(bom_table.records)
        result = expand_bom(root_code, qty, edges, max_depth=max_depth)
        return result.to_dict()


import_service = ImportService(persist=True)




