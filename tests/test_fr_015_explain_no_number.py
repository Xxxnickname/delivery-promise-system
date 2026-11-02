from datetime import date
from decimal import Decimal

from app.models.domain import GapLine, OrderPromise
from app.services.explain import explain_order


def test_fr_015_explanation_has_no_new_numbers():
    """FR-015：解释文案只描述原因，不生成数量/日期/天数。"""
    promise = OrderPromise(
        "SO-1",
        "客户A",
        "FG-1",
        Decimal("10"),
        date(2026, 11, 10),
        date(2026, 11, 12),
        date(2026, 11, 9),
        False,
        2,
        [GapLine("RM-1", "物料", Decimal("10"), Decimal("5"), Decimal("5"), None)],
    )
    text = explain_order(promise)
    assert not any(char.isdigit() for char in text)
    assert "物料" in text and "建议" in text
