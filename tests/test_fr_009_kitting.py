from datetime import date

from app.services.kitting import calculate_earliest_start, calculate_kit_date


def test_fr_009_kit_date_and_earliest_start():
    """FR-009：无缺口时取最晚到料日，并按生产提前期倒推开开工日。"""
    from decimal import Decimal
    from app.models.domain import MaterialReadiness

    readiness = [
        MaterialReadiness("A", Decimal("1"), Decimal("1"), date(2026, 11, 5), Decimal("0")),
        MaterialReadiness("B", Decimal("1"), Decimal("1"), date(2026, 11, 7), Decimal("0")),
    ]
    kit = calculate_kit_date(readiness, date(2026, 11, 2))
    assert kit == date(2026, 11, 7)
    assert calculate_earliest_start(kit, 3) == date(2026, 11, 4)
