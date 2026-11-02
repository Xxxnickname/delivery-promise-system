from decimal import Decimal

from app.models.domain import SubstituteRule
from app.services.bom_expand import plan_substitutions


def test_fr_006_one_to_one_substitute_ratio():
    """FR-006：主料不足时按比例折算替代料，并保留剩余缺口。"""
    rules = [SubstituteRule("SG-RM-005", "RM-005", "RM-005A", Decimal("1.0"))]
    result = plan_substitutions(
        {"RM-005": Decimal("122.4")},
        {"RM-005": Decimal("100")},
        rules,
        available_substitute={"RM-005A": Decimal("20")},
    )[0]
    assert result.primary_used == Decimal("100.000000")
    assert result.substitute_qty == Decimal("20.000000")
    assert result.remaining_gap == Decimal("2.400000")


def test_fr_006_non_unit_ratio():
    """FR-006：比例不等于 1 时，替代数量按主料缺口乘比例。"""
    rules = [SubstituteRule("SG-RM-007", "RM-007", "RM-007A", Decimal("0.85"))]
    result = plan_substitutions({"RM-007": Decimal("50")}, {"RM-007": Decimal("0")}, rules)[0]
    assert result.substitute_qty == Decimal("42.500000")
