from datetime import date
from decimal import Decimal

from app.models.domain import BomEdge, InTransitRecord, InventoryRecord, OrderRecord
from app.services.simulate import simulate_change


def test_fr_012_insert_simulation_does_not_mutate_inputs():
    """FR-012：插单只在副本上重算，原订单与供给不变，并返回影响清单。"""
    orders = [OrderRecord("SO-1", "FG-1", Decimal("3"), date(2026, 11, 10), "客户A")]
    edges = [BomEdge("FG-1", "RM-1", Decimal("2"))]
    inventory = [InventoryRecord("RM-1", Decimal("8"), Decimal("0"))]
    transit = [InTransitRecord("RM-1", Decimal("2"), date(2026, 11, 12), "PO-1")]
    result = simulate_change(
        orders,
        edges,
        inventory,
        transit,
        order_no="SO-1",
        mode="insert",
        qty=Decimal("3"),
        expect_date=date(2026, 11, 9),
        as_of_date=date(2026, 11, 2),
    )
    assert result["not_persisted"] is True
    assert result["inserted_order"]["order_no"].startswith("SIM-")
    assert len(orders) == 1
    assert inventory[0].on_hand == Decimal("8")
    assert result["summary"]["affected_count"] >= 1
