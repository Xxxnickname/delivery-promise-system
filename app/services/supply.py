"""供给冲减：库存先扣已分配，在途按 ETA 升序逐批消耗。"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.core.decimal_utils import round_qty
from app.models.domain import InTransitRecord, InventoryRecord, MaterialReadiness


@dataclass
class SupplyBatch:
    """可消耗的在途批次；remaining 在消费过程中递减。"""

    batch_no: str
    eta_date: date
    qty: Decimal
    remaining: Decimal
    supplier: str = ""


@dataclass
class SupplyPool:
    """按物料维护库存与在途，订单按优先级顺序消费同一池子。"""

    as_of_date: date
    available: dict[str, Decimal] = field(default_factory=dict)
    in_transit: dict[str, list[SupplyBatch]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def from_records(cls, inventory: list[InventoryRecord], in_transit: list[InTransitRecord], as_of_date: date) -> "SupplyPool":
        """从库存和在途记录构建共享供给池。"""
        pool = cls(as_of_date=as_of_date)
        for record in inventory:
            available = round_qty(record.on_hand - record.allocated)
            if available < 0:
                raise ValueError(f"库存已分配超过现有：{record.item_code}")
            pool.available[record.item_code] = round_qty(pool.available.get(record.item_code, Decimal("0")) + available)
        grouped: dict[str, list[SupplyBatch]] = defaultdict(list)
        for record in in_transit:
            grouped[record.item_code].append(SupplyBatch(record.batch_no, record.eta_date, round_qty(record.qty), round_qty(record.qty), record.supplier))
        for item_code, batches in grouped.items():
            pool.in_transit[item_code] = sorted(batches, key=lambda batch: (batch.eta_date, batch.batch_no))
        return pool

    def consume(self, item_code: str, required_qty: Decimal) -> MaterialReadiness:
        """消耗指定物料；返回实际分配、齐套日期和剩余缺口。"""
        required = round_qty(required_qty)
        remaining = required
        allocated = Decimal("0")
        sources: list[dict[str, str]] = []
        dates: list[date] = []

        stock = round_qty(self.available.get(item_code, Decimal("0")))
        if stock > 0 and remaining > 0:
            used = min(stock, remaining)
            self.available[item_code] = round_qty(stock - used)
            allocated += used
            remaining = round_qty(remaining - used)
            sources.append({"source": "inventory", "qty": format(used, "f"), "date": self.as_of_date.isoformat()})
            dates.append(self.as_of_date)

        for batch in self.in_transit.get(item_code, []):
            if remaining <= 0:
                break
            if batch.remaining <= 0:
                continue
            used = min(batch.remaining, remaining)
            batch.remaining = round_qty(batch.remaining - used)
            allocated += used
            remaining = round_qty(remaining - used)
            dates.append(batch.eta_date)
            sources.append({"source": "in_transit", "batch_no": batch.batch_no, "qty": format(used, "f"), "date": batch.eta_date.isoformat()})

        ready_date = max(dates) if dates and remaining == 0 else None
        return MaterialReadiness(
            item_code=item_code,
            required_qty=required,
            allocated_qty=round_qty(allocated),
            ready_date=ready_date,
            gap_qty=round_qty(max(Decimal("0"), remaining)),
            sources=sources,
        )
