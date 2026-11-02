"""表头别名与料号归一。

G2 采用规则优先：先处理已知中文/英文别名，无法映射的列原样保留，
由 parse_tables 生成“缺少必填列”错误，避免静默猜测。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


TABLE_SCHEMAS: dict[str, list[str]] = {
    "orders": ["order_no", "item_code", "qty", "due_date", "customer"],
    "bom": ["parent_code", "child_code", "qty_per", "scrap_rate", "substitute_group", "level"],
    "inventory": ["item_code", "on_hand", "allocated", "warehouse"],
    "in_transit": ["item_code", "qty", "eta_date", "batch_no", "supplier"],
}

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "orders": ["order_no", "item_code", "qty", "due_date"],
    "bom": ["parent_code", "child_code", "qty_per"],
    "inventory": ["item_code", "on_hand", "allocated"],
    "in_transit": ["item_code", "qty", "eta_date"],
}

HEADER_ALIASES: dict[str, str] = {
    "订单号": "order_no", "订单编号": "order_no", "orderid": "order_no", "orderno": "order_no",
    "料号": "item_code", "物料号": "item_code", "物料编码": "item_code", "图号": "item_code",
    "itemcode": "item_code", "materialcode": "item_code", "料号编码": "item_code",
    "父件": "parent_code", "父件料号": "parent_code", "parent": "parent_code", "parentcode": "parent_code",
    "子件": "child_code", "子件料号": "child_code", "child": "child_code", "childcode": "child_code",
    "用量": "qty_per", "单位用量": "qty_per", "qtyper": "qty_per", "用量系数": "qty_per",
    "损耗率": "scrap_rate", "损耗": "scrap_rate", "scraprate": "scrap_rate",
    "替代组": "substitute_group", "替代料组": "substitute_group", "substitutegroup": "substitute_group",
    "层级": "level", "bom层级": "level", "level": "level",
    "数量": "qty", "订购数量": "qty", "qty": "qty",
    "交期": "due_date", "客户交期": "due_date", "交货日期": "due_date", "duedate": "due_date",
    "客户": "customer", "客户名称": "customer", "customer": "customer",
    "现有库存": "on_hand", "库存数量": "on_hand", "库存": "on_hand", "onhand": "on_hand",
    "已分配": "allocated", "分配量": "allocated", "allocated": "allocated",
    "仓库": "warehouse", "库位": "warehouse", "warehouse": "warehouse",
    "预计到货日": "eta_date", "预计到货": "eta_date", "到货日": "eta_date", "etadate": "eta_date",
    "批次号": "batch_no", "批次": "batch_no", "batchno": "batch_no",
    "供应商": "supplier", "supplier": "supplier",
}


def _key(value: str) -> str:
    """将表头压缩成稳定键，兼容空格、下划线、大小写和 BOM 字符。"""
    return re.sub(r"[\s_\-]+", "", str(value).replace("\ufeff", "").strip().lower())


_CANONICAL_BY_KEY = {_key(key): value for key, value in HEADER_ALIASES.items()}
for _schema in TABLE_SCHEMAS.values():
    for _column in _schema:
        _CANONICAL_BY_KEY[_key(_column)] = _column


def normalize_header(header: str) -> str:
    """把单个表头映射成标准字段名；未知表头只做清理，不静默丢弃。"""
    cleaned = str(header).replace("\ufeff", "").strip()
    return _CANONICAL_BY_KEY.get(_key(cleaned), cleaned)


def normalize_headers(headers: list[str]) -> list[str]:
    """批量归一表头，并保持原始列顺序。"""
    return [normalize_header(header) for header in headers]


def normalize_item_code(value: object) -> str:
    """料号统一大写、去首尾空白和内部空格，确保同一物料可合并。"""
    return re.sub(r"\s+", "", str(value or "").strip()).upper()


@dataclass(frozen=True)
class PendingAlias:
    """无法自动识别的别名，进入待确认队列而不是直接覆盖主数据。"""

    tenant_id: str
    source_table: str
    raw_value: str
    normalized_value: str
    reason: str


class PendingAliasQueue:
    """G2 内存队列；后续接入 PostgreSQL 后替换为持久化队列。"""

    def __init__(self) -> None:
        self._items: list[PendingAlias] = []

    def add(self, item: PendingAlias) -> None:
        """追加待确认项，按原始值去重。"""
        if not any(existing.raw_value == item.raw_value and existing.source_table == item.source_table for existing in self._items):
            self._items.append(item)

    def list(self, tenant_id: str) -> list[dict[str, str]]:
        """返回指定租户的待确认项，避免跨租户泄露。"""
        return [
            {
                "source_table": item.source_table,
                "raw_value": item.raw_value,
                "normalized_value": item.normalized_value,
                "reason": item.reason,
            }
            for item in self._items
            if item.tenant_id == tenant_id
        ]
