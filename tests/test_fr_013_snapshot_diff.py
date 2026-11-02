from datetime import date
from decimal import Decimal

from app.models.domain import OrderPromise
from app.services.snapshot import SnapshotStore


def test_fr_013_snapshot_compare_aligns_by_order_no():
    """FR-013：快照按订单号对齐，延后为正、提前为负。"""
    store = SnapshotStore()
    before = [
        OrderPromise("SO-1", "A", "FG-1", Decimal("1"), date(2026, 11, 10), date(2026, 11, 5), date(2026, 11, 2), True, 0),
        OrderPromise("SO-2", "B", "FG-1", Decimal("1"), date(2026, 11, 11), date(2026, 11, 9), date(2026, 11, 6), True, 0),
    ]
    after = [
        OrderPromise("SO-1", "A", "FG-1", Decimal("1"), date(2026, 11, 10), date(2026, 11, 12), date(2026, 11, 9), False, 2),
        OrderPromise("SO-2", "B", "FG-1", Decimal("1"), date(2026, 11, 11), date(2026, 11, 7), date(2026, 11, 4), True, 0),
    ]
    snap_a = store.create(before, "gen-1.0")
    snap_b = store.create(after, "gen-1.0")
    diff = store.compare(snap_a.snapshot_id, snap_b.snapshot_id)
    assert diff["summary"]["changed"] == 2
    assert diff["summary"]["delayed"] == 1
    assert diff["summary"]["advanced"] == 1
    assert {item["order_no"]: item["delta_days"] for item in diff["items"]} == {"SO-1": 7, "SO-2": -2}
