"""生成 20 单演示基准。

说明：原计划书的 20 单人工核算样本未随仓库提供；本脚本按当前简化规则生成
一份可复算的替身基准，用于验证算法回归，不冒充真实人工核算数据。
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.import_batch import ImportService


def main() -> None:
    base = ROOT / "samples" / "03"
    headers = "订单号,物料编码,数量,客户交期,客户\n"
    lines = []
    for index in range(1, 21):
        due = date(2026, 11, 15) + timedelta(days=index)
        lines.append(f"SO-GOLD-{index:03d},FG-100,1,{due.isoformat()},基准客户{index:02d}")
    orders_bytes = ("\ufeff" + headers + "\n".join(lines) + "\n").encode("utf-8")
    (base / "orders_20.csv").write_bytes(orders_bytes)

    files = {
        "orders": orders_bytes,
        "bom": (base / "bom.csv").read_bytes(),
        "inventory": (base / "inventory.csv").read_bytes(),
        "in_transit": (base / "in_transit.csv").read_bytes(),
    }
    service = ImportService()
    batch = service.import_bundle(files)
    promises = service.calculate_promises(batch.batch_id, as_of_date=date(2026, 11, 2))
    payload = {
        "note": "synthetic stand-in for manual golden orders",
        "as_of_date": "2026-11-02",
        "calc_version": "gen-1.0",
        "orders": [
            {
                "order_no": promise.order_no,
                "item_code": promise.item_code,
                "qty": format(promise.qty, "f"),
                "due_date": promise.due_date.isoformat(),
                "kit_date": promise.kit_date.isoformat() if promise.kit_date else None,
                "can_commit": promise.can_commit,
                "delay_days": promise.delay_days,
                "gaps_count": len(promise.gaps),
            }
            for promise in promises
        ],
    }
    (base / "golden_orders.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"golden written: {len(promises)} orders")


if __name__ == "__main__":
    main()
