"""齐套日与最早开工日计算。"""
from __future__ import annotations

from datetime import date, timedelta

from app.models.domain import MaterialReadiness


def calculate_kit_date(readiness: list[MaterialReadiness], as_of_date: date) -> date | None:
    """取所有物料最晚齐套日；任一物料有缺口则返回 None。"""
    if any(item.gap_qty > 0 for item in readiness):
        return None
    if not readiness:
        return as_of_date
    dates = [item.ready_date for item in readiness if item.ready_date is not None]
    return max(dates) if dates else as_of_date


def calculate_earliest_start(kit_date: date | None, production_lead_days: int) -> date | None:
    """最早开工日 = 齐套日 - 生产提前期；无齐套日时返回 None。"""
    if kit_date is None:
        return None
    return kit_date - timedelta(days=production_lead_days)
