"""订单承诺计算：BOM 展开 + 共享供给池 + 齐套日/延期/缺口影响。"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from app.models.domain import (
    BomEdge,
    GapLine,
    InTransitRecord,
    InventoryRecord,
    MaterialReadiness,
    OrderPromise,
    OrderRecord,
)
from app.services.bom_expand import expand_bom
from app.services.kitting import calculate_earliest_start, calculate_kit_date
from app.services.supply import SupplyPool


def orders_from_records(records: Iterable[dict[str, object]]) -> list[OrderRecord]:
    """把 CSV 订单记录转换成强类型订单行。"""
    return [
        OrderRecord(
            order_no=str(record["order_no"]),
            item_code=str(record["item_code"]),
            qty=record["qty"],  # type: ignore[arg-type]
            due_date=record["due_date"],  # type: ignore[arg-type]
            customer=str(record.get("customer", "")),
        )
        for record in records
    ]


def inventory_from_records(records: Iterable[dict[str, object]]) -> list[InventoryRecord]:
    """把 CSV 库存记录转换成强类型记录。"""
    return [
        InventoryRecord(
            item_code=str(record["item_code"]),
            on_hand=record["on_hand"],  # type: ignore[arg-type]
            allocated=record["allocated"],  # type: ignore[arg-type]
            warehouse=str(record.get("warehouse", "")),
        )
        for record in records
    ]


def transit_from_records(records: Iterable[dict[str, object]]) -> list[InTransitRecord]:
    """把 CSV 在途记录转换成强类型记录。"""
    return [
        InTransitRecord(
            item_code=str(record["item_code"]),
            qty=record["qty"],  # type: ignore[arg-type]
            eta_date=record["eta_date"],  # type: ignore[arg-type]
            batch_no=str(record.get("batch_no", "")),
            supplier=str(record.get("supplier", "")),
        )
        for record in records
    ]


def calculate_promises(
    orders: list[OrderRecord],
    edges: list[BomEdge],
    inventory: list[InventoryRecord],
    in_transit: list[InTransitRecord],
    *,
    as_of_date: date,
    production_lead_days: int = 3,
    calc_version: str = "gen-1.0",
) -> list[OrderPromise]:
    """按交期优先级计算所有订单承诺。

    处理顺序：客户交期升序、订单号升序。这样同一物料供给紧张时，
    先到期的订单优先占用库存与在途，影响清单可解释顺延原因。
    """
    pool = SupplyPool.from_records(inventory, in_transit, as_of_date)
    ordered = sorted(orders, key=lambda order: (order.due_date, order.order_no))
    results: dict[str, OrderPromise] = {}

    for order in ordered:
        expansion = expand_bom(order.item_code, order.qty, edges, max_depth=5)
        readiness: list[MaterialReadiness] = [
            pool.consume(item_code, qty) for item_code, qty in sorted(expansion.requirements.items())
        ]
        kit_date = calculate_kit_date(readiness, as_of_date)
        can_commit = kit_date is not None and kit_date <= order.due_date
        delay_days = max(0, (kit_date - order.due_date).days) if kit_date else None
        gaps = [
            GapLine(
                item_code=item.item_code,
                item_name=item.item_code,
                need=item.required_qty,
                available=item.allocated_qty,
                gap=item.gap_qty,
                ready_date=item.ready_date,
            )
            for item in readiness
            if item.gap_qty > 0
        ]
        results[order.order_no] = OrderPromise(
            order_no=order.order_no,
            customer=order.customer,
            item_code=order.item_code,
            qty=order.qty,
            due_date=order.due_date,
            kit_date=kit_date,
            earliest_start_date=calculate_earliest_start(kit_date, production_lead_days),
            can_commit=can_commit,
            delay_days=delay_days,
            gaps=gaps,
            calc_version=calc_version,
        )

    impacts: dict[str, list[str]] = defaultdict(list)
    for promise in results.values():
        for gap in promise.gaps:
            impacts[gap.item_code].append(promise.order_no)
    for promise in results.values():
        for gap in promise.gaps:
            gap.impact_orders = sorted(impacts.get(gap.item_code, []))
    return sorted(results.values(), key=lambda promise: (promise.due_date, promise.order_no))
