from decimal import Decimal
from pathlib import Path

from app.services.bom_expand import edges_from_records, expand_bom
from app.services.parse_tables import parse_table


def test_fr_007_same_material_multiple_paths_no_double_count():
    """FR-007：同一物料出现在两条路径时只累加一次总量，但保留两条路径。"""
    table = parse_table("bom", Path("samples/03/bom.csv").read_bytes())
    result = expand_bom("FG-100", Decimal("10"), edges_from_records(table.records))
    assert result.requirements["RM-007"] == Decimal("50.000000")
    assert result.traces["RM-007"] == ["FG-100 > SUB-X > RM-007", "FG-100 > SUB-Y > RM-007"]
