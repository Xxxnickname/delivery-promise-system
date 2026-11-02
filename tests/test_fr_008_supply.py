from datetime import date
from decimal import Decimal

from app.models.domain import InTransitRecord, InventoryRecord
from app.services.supply import SupplyPool


def test_fr_008_supply_uses_inventory_then_eta_order():
    """FR-008：库存先扣已分配，在途按 ETA 顺序消耗并给出齐套日期。"""
    pool = SupplyPool.from_records(
        [InventoryRecord("RM-1", Decimal("10"), Decimal("2"))],
        [
            InTransitRecord("RM-1", Decimal("3"), date(2026, 11, 12), "B2"),
            InTransitRecord("RM-1", Decimal("5"), date(2026, 11, 10), "B1"),
        ],
        date(2026, 11, 2),
    )
    result = pool.consume("RM-1", Decimal("15"))
    assert result.allocated_qty == Decimal("15.000000")
    assert result.ready_date == date(2026, 11, 12)
    assert result.gap_qty == Decimal("0.000000")
    assert [source["batch_no"] for source in result.sources if source["source"] == "in_transit"] == ["B1", "B2"]
