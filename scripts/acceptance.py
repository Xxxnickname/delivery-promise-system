"""22 条极端/边界场景验收脚本（G4）。"""
from __future__ import annotations

import sys
import tempfile
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.domain import BomEdge, InTransitRecord, InventoryRecord, OrderPromise, OrderRecord, SubstituteRule
from app.services.bom_expand import BomCycleError, BomDepthError, edges_from_records, expand_bom, plan_substitutions
from app.services.explain import explain_order
from app.services.export_service import ExportService
from app.services.import_batch import ImportService
from app.services.parse_tables import parse_table
from app.services.promise import calculate_promises
from app.services.snapshot import SnapshotStore
from app.services.supply import SupplyPool


BASE = ROOT / "samples" / "03"


def _headers(text: str) -> bytes:
    return ("\ufeff" + text + "\n").encode("utf-8")


def _sample_files():
    return {t: (BASE / f"{t}.csv").read_bytes() for t in ("orders", "bom", "inventory", "in_transit")}


def run_checks() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    def check(name: str, func):
        try:
            func()
            results.append({"name": name, "ok": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "ok": False, "error": str(exc)})

    check("01_empty_file", lambda: bool(parse_table("orders", b"").errors) and parse_table("orders", b"").errors[0].column == "file")
    check("02_missing_column", lambda: parse_table("orders", _headers("order_no,item_code\nSO-1,FG-1")).errors[0].column == "qty")
    check("03_invalid_date", lambda: parse_table("orders", _headers("order_no,item_code,qty,due_date\nSO-1,FG-1,1,2026/01/01")).errors[0].column == "due_date")
    check("04_negative_qty", lambda: parse_table("orders", _headers("order_no,item_code,qty,due_date\nSO-1,FG-1,-1,2026-01-01")).errors[0].column == "qty")
    check("05_allocated_over_stock", lambda: parse_table("inventory", _headers("item_code,on_hand,allocated\nRM-1,1,2")).errors[0].column == "allocated")
    check("06_duplicate_header", lambda: parse_table("orders", _headers("订单号,订单编号,物料编码,数量,客户交期\nSO-1,SO-2,FG-1,1,2026-01-01")).errors[0].column == "header")
    check("07_blank_row_ignored", lambda: parse_table("inventory", _headers("item_code,on_hand,allocated\nRM-1,1,0\n,,")).ok_rows == 1)

    def check_eight():
        table = parse_table("bom", (BASE / "bom.csv").read_bytes())
        result = expand_bom("FG-100", Decimal("10"), edges_from_records(table.records))
        assert result.depth_used == 5 and result.requirements["RM-005"] == Decimal("122.400000")

    check("08_bom_five_level", check_eight)

    def check_nine():
        try:
            expand_bom("X", Decimal("1"), [BomEdge("X", "Y", Decimal("1")), BomEdge("Y", "X", Decimal("1"))])
        except BomCycleError:
            return
        raise AssertionError("cycle not detected")

    check("09_bom_cycle", check_nine)

    def check_ten():
        try:
            expand_bom("A", Decimal("1"), [BomEdge("A", "B", Decimal("1")), BomEdge("B", "C", Decimal("1")), BomEdge("C", "D", Decimal("1")), BomEdge("D", "E", Decimal("1")), BomEdge("E", "F", Decimal("1")), BomEdge("F", "RM", Decimal("1"))])
        except BomDepthError:
            return
        raise AssertionError("depth not detected")

    check("10_bom_depth", check_ten)

    def check_eleven():
        table = parse_table("bom", (BASE / "bom.csv").read_bytes())
        result = expand_bom("FG-100", Decimal("10"), edges_from_records(table.records))
        assert result.requirements["RM-007"] == Decimal("50.000000") and len(result.traces["RM-007"]) == 2

    check("11_no_double_count", check_eleven)

    def check_twelve():
        row = plan_substitutions({"RM-1": Decimal("10")}, {"RM-1": Decimal("4")}, [SubstituteRule("SG", "RM-1", "RM-1A", Decimal("0.5"))])[0]
        assert row.substitute_qty == Decimal("3.000000") and row.remaining_gap == Decimal("0.000000")

    check("12_substitute_ratio", check_twelve)

    def check_thirteen():
        row = plan_substitutions({"RM-1": Decimal("10")}, {"RM-1": Decimal("4")}, [SubstituteRule("SG", "RM-1", "RM-1A", Decimal("1"))], {"RM-1A": Decimal("2")})[0]
        assert row.substitute_qty == Decimal("2.000000") and row.remaining_gap == Decimal("4.000000")

    check("13_substitute_short", check_thirteen)

    def check_fourteen():
        pool = SupplyPool.from_records([InventoryRecord("RM-1", Decimal("3"), Decimal("1"))], [InTransitRecord("RM-1", Decimal("2"), date(2026, 11, 10), "PO-1")], date(2026, 11, 2))
        row = pool.consume("RM-1", Decimal("4"))
        assert row.ready_date == date(2026, 11, 10) and row.gap_qty == Decimal("0")

    check("14_supply_mix", check_fourteen)

    def check_fifteen():
        pool = SupplyPool.from_records([], [], date(2026, 11, 2))
        row = pool.consume("RM-2", Decimal("1"))
        assert row.ready_date is None and row.gap_qty == Decimal("1.000000")

    check("15_no_supply", check_fifteen)

    def check_sixteen():
        promises = calculate_promises(
            [OrderRecord("SO-2", "FG-1", Decimal("2"), date(2026, 11, 5), "B"), OrderRecord("SO-1", "FG-1", Decimal("2"), date(2026, 11, 4), "A")],
            [BomEdge("FG-1", "RM-1", Decimal("1"))],
            [InventoryRecord("RM-1", Decimal("2"), Decimal("0"))],
            [],
            as_of_date=date(2026, 11, 2),
        )
        assert promises[0].order_no == "SO-1" and promises[0].can_commit and not promises[1].can_commit

    check("16_due_date_priority", check_sixteen)

    def check_seventeen():
        files = _sample_files(); files["orders"] = (BASE / "sample_error_orders.csv").read_bytes()
        batch = ImportService().import_bundle(files)
        assert batch.status == "ROLLED_BACK" and batch.imported_rows == 0

    check("17_all_or_nothing", check_seventeen)

    def check_eighteen():
        files = _sample_files(); files["orders"] = (BASE / "sample_error_orders.csv").read_bytes()
        batch = ImportService().import_bundle(files, mode="PARTIAL_WITH_AUDIT", allow_partial=True)
        assert batch.status == "PARTIAL_IMPORTED" and batch.imported_rows > 0

    check("18_partial_import", check_eighteen)

    def check_nineteen():
        service = ImportService(); files = _sample_files()
        assert service.import_bundle(files).batch_id == service.import_bundle(files).batch_id

    check("19_idempotent", check_nineteen)

    def check_twenty():
        store = SnapshotStore()
        base = OrderPromise("SO-1", "A", "FG-1", Decimal("1"), date(2026, 11, 10), date(2026, 11, 5), date(2026, 11, 2), True, 0)
        later = OrderPromise("SO-1", "A", "FG-1", Decimal("1"), date(2026, 11, 10), date(2026, 11, 6), date(2026, 11, 3), True, 0)
        a, b = store.create([base], "v"), store.create([later], "v")
        assert store.compare(a.snapshot_id, b.snapshot_id)["items"][0]["delta_days"] == 1

    check("20_snapshot_diff", check_twenty)

    def check_twenty_one():
        promise = OrderPromise("SO-1", "A", "FG-1", Decimal("1"), date(2026, 11, 10), None, None, False, None)
        assert not any(ch.isdigit() for ch in explain_order(promise))

    check("21_explain_no_digits", check_twenty_one)

    def check_twenty_two():
        with tempfile.TemporaryDirectory() as tmp:
            service = ExportService(Path(tmp))
            task = service.create("user-check", "kit_report", [{"order_no": "SO-1", "qty": "1"}], "kit")
            for _ in range(50):
                if task.status == "SUCCESS":
                    break
                time.sleep(0.05)
            assert task.file_path and Path(task.file_path).read_bytes()[:2] == b"PK"

    check("22_xlsx_export", check_twenty_two)
    return results


def main() -> int:
    results = run_checks()
    passed = sum(1 for item in results if item["ok"])
    for item in results:
        print(("PASS" if item["ok"] else "FAIL"), item["name"], item.get("error", ""))
    print(f"SUMMARY {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

