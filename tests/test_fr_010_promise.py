from datetime import date
from decimal import Decimal

from app.models.domain import BomEdge, InTransitRecord, InventoryRecord, OrderRecord
from app.services.promise import calculate_promises


def test_fr_010_promise_assigns_shared_supply_by_due_date():
    """FR-010：共享供给按交期优先分配，第二张单使用较晚在途导致延期。"""
    orders = [
        OrderRecord("SO-2", "FG-1", Decimal("3"), date(2026, 11, 10), "客户B"),
        OrderRecord("SO-1", "FG-1", Decimal("3"), date(2026, 11, 5), "客户A"),
    ]
    edges = [BomEdge("FG-1", "RM-1", Decimal("2"))]
    inventory = [InventoryRecord("RM-1", Decimal("10"), Decimal("0"))]
    transit = [InTransitRecord("RM-1", Decimal("2"), date(2026, 11, 12), "PO-2")]
    promises = calculate_promises(
        orders,
        edges,
        inventory,
        transit,
        as_of_date=date(2026, 11, 2),
        production_lead_days=3,
    )
    by_no = {promise.order_no: promise for promise in promises}
    assert by_no["SO-1"].kit_date == date(2026, 11, 2)
    assert by_no["SO-1"].can_commit is True
    assert by_no["SO-2"].kit_date == date(2026, 11, 12)
    assert by_no["SO-2"].delay_days == 2
    assert by_no["SO-2"].can_commit is False
