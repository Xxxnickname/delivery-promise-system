from decimal import Decimal
from pathlib import Path

from app.services.bom_expand import edges_from_records, expand_bom
from app.services.parse_tables import parse_table


def test_fr_005_expand_five_levels_with_scrap():
    """FR-005/FR-006：5 层展开与损耗必须得到可复算的 Decimal 结果。"""
    table = parse_table("bom", Path("samples/03/bom.csv").read_bytes())
    result = expand_bom("FG-100", Decimal("10"), edges_from_records(table.records))
    assert result.depth_used == 5
    assert result.requirements["RM-005"] == Decimal("122.400000")
    assert result.requirements["RM-006"] == Decimal("40.800000")
    assert result.requirements["RM-007"] == Decimal("50.000000")
