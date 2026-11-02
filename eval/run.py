"""20 单基准对比入口：`python eval/run.py --golden`。"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.bom_expand import edges_from_records
from app.services.parse_tables import parse_table
from app.services.promise import calculate_promises, inventory_from_records, transit_from_records


def run_golden(base_dir: Path | None = None) -> tuple[float, list[dict[str, object]]]:
    """读取 golden_orders.json，按同一输入重算并返回对齐率和差异表。"""
    base = base_dir or ROOT / "samples" / "03"
    golden = json.loads((base / "golden_orders.json").read_text(encoding="utf-8"))
    from app.models.domain import OrderRecord

    orders = [
        OrderRecord(
            order_no=item["order_no"],
            item_code=item["item_code"],
            qty=Decimal(item["qty"]),
            due_date=date.fromisoformat(item["due_date"]),
            customer="基准客户",
        )
        for item in golden["orders"]
    ]
    bom = parse_table("bom", (base / "bom.csv").read_bytes())
    inventory = parse_table("inventory", (base / "inventory.csv").read_bytes())
    transit = parse_table("in_transit", (base / "in_transit.csv").read_bytes())
    promises = calculate_promises(
        orders,
        edges_from_records(bom.records),
        inventory_from_records(inventory.records),
        transit_from_records(transit.records),
        as_of_date=date.fromisoformat(golden["as_of_date"]),
        production_lead_days=3,
        calc_version=golden["calc_version"],
    )
    expected = {item["order_no"]: item for item in golden["orders"]}
    diffs: list[dict[str, object]] = []
    matched = 0
    for promise in promises:
        want = expected[promise.order_no]
        actual = promise.to_dict()
        keys = ("due_date", "kit_date", "can_commit", "delay_days")
        mismatch = {key: {"expected": want.get(key), "actual": actual.get(key)} for key in keys if want.get(key) != actual.get(key)}
        if not mismatch:
            matched += 1
        else:
            diffs.append({"order_no": promise.order_no, "mismatch": mismatch})
    return matched / len(promises) * 100, diffs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", action="store_true", help="运行 20 单基准对比")
    args = parser.parse_args()
    if not args.golden:
        parser.print_help()
        return 2
    rate, diffs = run_golden()
    report = ROOT / "reports" / "eval.md"
    lines = [
        "# 20 单基准对比",
        "",
        f"- 对齐率：**{rate:.2f}%**",
        f"- 差异单数：{len(diffs)}",
        "- 数据说明：原人工基准未随仓库提供，当前 `golden_orders.json` 为按简化规则生成的替身基准。",
        "",
        "## 差异表",
        "",
    ]
    if diffs:
        for diff in diffs:
            lines.append(f"- `{diff['order_no']}`：{json.dumps(diff['mismatch'], ensure_ascii=False)}")
    else:
        lines.append("无差异。")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"alignment_rate": rate, "differences": len(diffs), "report": str(report)}, ensure_ascii=False))
    return 0 if rate >= 98 else 1


if __name__ == "__main__":
    raise SystemExit(main())
