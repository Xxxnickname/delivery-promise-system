from decimal import Decimal

import pytest

from app.models.domain import BomEdge
from app.services.bom_expand import BomCycleError, BomDepthError, expand_bom


def test_bom_cycle_is_rejected():
    """循环 BOM 必须报错并保留路径，不能死循环。"""
    edges = [
        BomEdge("X", "Y", Decimal("1")),
        BomEdge("Y", "X", Decimal("1")),
    ]
    with pytest.raises(BomCycleError) as exc:
        expand_bom("X", Decimal("1"), edges)
    assert exc.value.path[-1] == "X"


def test_bom_depth_over_five_is_rejected():
    """超过 5 层必须报错，避免截断后静默算错。"""
    edges = [
        BomEdge("A", "B", Decimal("1")),
        BomEdge("B", "C", Decimal("1")),
        BomEdge("C", "D", Decimal("1")),
        BomEdge("D", "E", Decimal("1")),
        BomEdge("E", "F", Decimal("1")),
        BomEdge("F", "RM", Decimal("1")),
    ]
    with pytest.raises(BomDepthError):
        expand_bom("A", Decimal("1"), edges)
