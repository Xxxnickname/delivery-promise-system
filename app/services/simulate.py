"""场景模拟：插单/加急在内存副本上重算，不修改基准订单与供给。"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.decimal_utils import round_qty
from app.models.domain import BomEdge, InTransitRecord, InventoryRecord, OrderRecord
from app.services.promise import calculate_promises


def _promise_map(promises):
    """把承诺结果按订单号字典化，便于前后对比。"""
    return {promise.order_no: promise for promise in promises}


def simulate_change(
    orders: list[OrderRecord],
    edges: list[BomEdge],
    inventory: list[InventoryRecord],
    in_transit: list[InTransitRecord],
    *,
    order_no: str,
    mode: str,
    qty: Decimal,
    expect_date: date,
    as_of_date: date,
    production_lead_days: int = 3,
    calc_version: str = "gen-1.0",
) -> dict[str, Any]:
    """在订单副本上执行插单或加急，并返回相对基线的变化清单。"""
    if mode not in {"insert", "rush"}:
        raise ValueError("模拟模式必须是 insert 或 rush")
    if qty <= 0:
        raise ValueError("模拟数量必须大于 0")
    target = next((order for order in orders if order.order_no == order_no), None)
    if target is None:
        raise ValueError(f"基准订单不存在：{order_no}")

    baseline = calculate_promises(
        orders,
        edges,
        inventory,
        in_transit,
        as_of_date=as_of_date,
        production_lead_days=production_lead_days,
        calc_version=calc_version,
    )
    scenario_orders = list(orders)
    inserted = None
    if mode == "insert":
        inserted_no = f"SIM-{datetime.now():%Y%m%d%H%M%S}"
        inserted = OrderRecord(inserted_no, target.item_code, round_qty(qty), expect_date, target.customer)
        scenario_orders.append(inserted)
    else:
        scenario_orders = [replace(order, due_date=expect_date) if order.order_no == order_no else order for order in orders]

    scenario = calculate_promises(
        scenario_orders,
        edges,
        inventory,
        in_transit,
        as_of_date=as_of_date,
        production_lead_days=production_lead_days,
        calc_version=f"{calc_version}-sim",
    )
    before_by_no = _promise_map(baseline)
    after_by_no = _promise_map(scenario)
    affected: list[dict[str, Any]] = []
    for no in sorted(set(before_by_no) | set(after_by_no)):
        before = before_by_no.get(no)
        after = after_by_no.get(no)
        if before is None and after is None:
            continue
        before_kit = before.kit_date if before else None
        after_kit = after.kit_date if after else None
        if before and after and before_kit == after_kit:
            continue
        delta = (after_kit - before_kit).days if before_kit and after_kit else None
        affected.append({
            "order_no": no,
            "customer": after.customer if after else before.customer,
            "before_kit_date": before_kit.isoformat() if before_kit else None,
            "after_kit_date": after_kit.isoformat() if after_kit else None,
            "delay_days": delta,
            "reason": "插单占用供给" if mode == "insert" else "加急调整交期",
        })

    positive_delays = [item["delay_days"] for item in affected if item["delay_days"] is not None and item["delay_days"] > 0]
    inserted_result = after_by_no.get(inserted.order_no).to_dict() if inserted and after_by_no.get(inserted.order_no) else None
    return {
        "mode": mode,
        "order_no": order_no,
        "not_persisted": True,
        "summary": {
            "affected_count": len(affected),
            "max_delay_days": max(positive_delays) if positive_delays else 0,
        },
        "inserted_order": inserted_result,
        "affected": affected,
        "baseline_calc_version": calc_version,
        "simulation_calc_version": f"{calc_version}-sim",
    }
