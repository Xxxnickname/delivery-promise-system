from datetime import date, timedelta
from decimal import Decimal
from time import perf_counter

from app.models.domain import BomEdge, InventoryRecord, OrderRecord
from app.services.promise import calculate_promises


def test_fr_017_thousand_orders_under_five_seconds():
    """FR-017：1000 行订单在内存计算层应低于 5 秒。"""
    orders = [
        OrderRecord(f"SO-PERF-{index:04d}", "FG-P", Decimal("1"), date(2026, 12, 1) + timedelta(days=index % 10), "性能客户")
        for index in range(1000)
    ]
    edges = [BomEdge("FG-P", "RM-P1", Decimal("2")), BomEdge("FG-P", "RM-P2", Decimal("1.5")), BomEdge("FG-P", "RM-P3", Decimal("0.5"))]
    inventory = [InventoryRecord(code, Decimal("1000000"), Decimal("0")) for code in ("RM-P1", "RM-P2", "RM-P3")]
    started = perf_counter()
    promises = calculate_promises(orders, edges, inventory, [], as_of_date=date(2026, 11, 2))
    elapsed = perf_counter() - started
    assert len(promises) == 1000
    assert elapsed < 5
