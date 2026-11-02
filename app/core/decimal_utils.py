"""Decimal 工具：数量、金额和舍入规则统一在此实现。"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


QTY_QUANT = Decimal("0.000001")
MID_QUANT = Decimal("0.001")
AMOUNT_QUANT = Decimal("0.0001")
DISPLAY_QUANT = Decimal("0.01")


def D(value: object) -> Decimal:
    """将输入安全转换为 Decimal；禁止静默把非法值当成 0。"""
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValueError(f"不是合法数字：{value!r}") from exc


def round_qty(value: Decimal) -> Decimal:
    """最终数量按 6 位小数四舍五入，符合 Decimal(18,6) 存储口径。"""
    return value.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def round_mid(value: Decimal) -> Decimal:
    """BOM 中间量按 3 位小数四舍五入，便于对账和复算。"""
    return value.quantize(MID_QUANT, rounding=ROUND_HALF_UP)


def round_amount(value: Decimal) -> Decimal:
    """金额按 4 位小数四舍五入，符合 Decimal(18,4) 存储口径。"""
    return value.quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP)


def display_qty(value: Decimal) -> str:
    """输出两位小数字符串，避免 API JSON 使用 float。"""
    return format(value.quantize(DISPLAY_QUANT, rounding=ROUND_HALF_UP), "f")
