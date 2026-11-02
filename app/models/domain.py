"""G2 领域对象：表格解析、BOM 边、替代规则和展开结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ImportErrorRow:
    """一行导入错误；字段顺序与错误 CSV 契约保持一致。"""

    row_no: int
    column: str
    value: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"row_no": self.row_no, "column": self.column, "value": self.value, "reason": self.reason}


@dataclass
class ParsedTable:
    """单张 CSV 的解析结果；records 内保留 Decimal/date 等强类型值供计算层使用。"""

    table_type: str
    headers: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[ImportErrorRow] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def ok_rows(self) -> int:
        return 0 if self.errors else len(self.records)


@dataclass(frozen=True)
class BomEdge:
    """BOM 父子边；scrap_rate 使用小数表达，例如 0.02 表示 2%。"""

    parent_code: str
    child_code: str
    qty_per: Decimal
    scrap_rate: Decimal = Decimal("0")
    substitute_group: str | None = None
    level: int | None = None


@dataclass(frozen=True)
class SubstituteRule:
    """一对一替代规则；substitute_qty = shortage * ratio。"""

    group_code: str
    primary_code: str
    substitute_code: str
    ratio: Decimal = Decimal("1")


@dataclass
class ExpansionResult:
    """BOM 展开结果：叶子物料总量 + 每条路径 + 实际使用的替代料。"""

    root_code: str
    root_qty: Decimal
    requirements: dict[str, Decimal]
    traces: dict[str, list[str]]
    depth_used: int = 0
    substitutes: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_code": self.root_code,
            "root_qty": format(self.root_qty, "f"),
            "depth_used": self.depth_used,
            "requirements": {code: format(qty, "f") for code, qty in sorted(self.requirements.items())},
            "traces": self.traces,
            "substitutes": self.substitutes,
        }


@dataclass
class SubstitutionResult:
    """主料不足时的一对一替代分配结果；不改变总需求，只说明采购/领料结构。"""

    primary_code: str
    substitute_code: str
    group_code: str
    required_qty: Decimal
    available_primary: Decimal
    primary_used: Decimal
    substitute_qty: Decimal
    remaining_gap: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "primary_code": self.primary_code,
            "substitute_code": self.substitute_code,
            "group_code": self.group_code,
            "required_qty": format(self.required_qty, "f"),
            "available_primary": format(self.available_primary, "f"),
            "primary_used": format(self.primary_used, "f"),
            "substitute_qty": format(self.substitute_qty, "f"),
            "remaining_gap": format(self.remaining_gap, "f"),
        }

@dataclass(frozen=True)
class OrderRecord:
    """订单行：G3 以订单行作为计算入口，订单号可重复但样例保持唯一。"""

    order_no: str
    item_code: str
    qty: Decimal
    due_date: date
    customer: str = ""


@dataclass(frozen=True)
class InventoryRecord:
    """库存记录；可用量必须由 on_hand - allocated 得到。"""

    item_code: str
    on_hand: Decimal
    allocated: Decimal
    warehouse: str = ""


@dataclass(frozen=True)
class InTransitRecord:
    """在途批次；按 eta_date 升序参与供给冲减。"""

    item_code: str
    qty: Decimal
    eta_date: date
    batch_no: str = ""
    supplier: str = ""


@dataclass
class MaterialReadiness:
    """某订单对某物料的需求与供给结果。"""

    item_code: str
    required_qty: Decimal
    allocated_qty: Decimal
    ready_date: date | None
    gap_qty: Decimal
    sources: list[dict[str, str]] = field(default_factory=list)


@dataclass
class GapLine:
    """订单缺口行，字段与前端缺口表/接口契约一致。"""

    item_code: str
    item_name: str
    need: Decimal
    available: Decimal
    gap: Decimal
    ready_date: date | None
    impact_orders: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "need": format(self.need, "f"),
            "available": format(self.available, "f"),
            "gap": format(self.gap, "f"),
            "ready_date": self.ready_date.isoformat() if self.ready_date else None,
            "impact_orders": self.impact_orders,
        }


@dataclass
class OrderPromise:
    """订单承诺结果，包含齐套、开工、缺口和影响清单。"""

    order_no: str
    customer: str
    item_code: str
    qty: Decimal
    due_date: date
    kit_date: date | None
    earliest_start_date: date | None
    can_commit: bool
    delay_days: int | None
    gaps: list[GapLine] = field(default_factory=list)
    calc_version: str = "gen-1.0"

    @property
    def status(self) -> str:
        if self.kit_date is None:
            return "NO_SUPPLY"
        return "COMMITTABLE" if self.can_commit else "DELAYED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_no": self.order_no,
            "customer": self.customer,
            "item_code": self.item_code,
            "qty": format(self.qty, "f"),
            "due_date": self.due_date.isoformat(),
            "kit_date": self.kit_date.isoformat() if self.kit_date else None,
            "earliest_start_date": self.earliest_start_date.isoformat() if self.earliest_start_date else None,
            "can_commit": self.can_commit,
            "delay_days": self.delay_days,
            "status": self.status,
            "gaps": [gap.to_dict() for gap in self.gaps],
            "calc_version": self.calc_version,
        }
