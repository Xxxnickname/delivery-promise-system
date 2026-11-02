"""G2 一键自检：读取四表样例并输出 BOM 展开关键结果。"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.bom_expand import edges_from_records, expand_bom
from app.services.import_batch import ImportService


def main() -> int:
    """执行四表导入与 5 层展开；失败时返回非 0，便于 CI/手工门禁。"""
    base = Path("samples/03")
    files = {
        "orders": (base / "orders.csv").read_bytes(),
        "bom": (base / "bom.csv").read_bytes(),
        "inventory": (base / "inventory.csv").read_bytes(),
        "in_transit": (base / "in_transit.csv").read_bytes(),
    }
    batch = ImportService().import_bundle(files)
    if not batch.committed:
        print(json.dumps(batch.to_dict(include_records=True), ensure_ascii=False, indent=2))
        return 1

    bom_table = batch.tables["bom"]
    expansion = expand_bom("FG-100", Decimal("10"), edges_from_records(bom_table.records))
    result = {
        "batch_id": batch.batch_id,
        "status": batch.status,
        "ok_rows": batch.ok_rows,
        "failed_rows": batch.failed_rows,
        "expansion": expansion.to_dict(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    expected = {
        "RM-005": Decimal("122.400000"),
        "RM-006": Decimal("40.800000"),
        "RM-007": Decimal("50.000000"),
    }
    return 0 if all(expansion.requirements.get(code) == qty for code, qty in expected.items()) else 2


if __name__ == "__main__":
    raise SystemExit(main())


