"""四张 CSV 的严格解析与行列级错误收集。

设计原则：
1. 表头先经过规则别名归一；
2. 必填列缺失直接返回行 1 错误；
3. 每个字段错误包含行号/列/原值/原因；
4. 有错误的行不进入有效记录，但不会静默丢失。
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pandas as pd

from app.core.config import settings
from app.core.decimal_utils import D
from app.models.domain import ImportErrorRow, ParsedTable
from app.services.alias import REQUIRED_COLUMNS, TABLE_SCHEMAS, normalize_headers, normalize_item_code


def _is_blank(value: object) -> bool:
    """统一判断空单元格，避免空格被当作有效值。"""
    return value is None or str(value).strip() == ""


def _decimal_field(
    raw: dict[str, str], column: str, row_no: int, errors: list[ImportErrorRow], *, minimum: Decimal | None = None,
    required: bool = True,
) -> Decimal | None:
    """解析 Decimal 字段；非法值生成可定位错误，不返回 0 冒充。"""
    value = raw.get(column, "")
    if _is_blank(value):
        if required:
            errors.append(ImportErrorRow(row_no, column, "", "必填字段为空"))
        return None
    try:
        parsed = D(value)
    except ValueError:
        errors.append(ImportErrorRow(row_no, column, value, "不是合法数字"))
        return None
    if minimum is not None and parsed < minimum:
        errors.append(ImportErrorRow(row_no, column, value, f"必须大于等于 {minimum}"))
        return None
    return parsed


def _date_field(raw: dict[str, str], column: str, row_no: int, errors: list[ImportErrorRow]) -> date | None:
    """严格校验 YYYY-MM-DD；不允许 Pandas 自动猜测日期。"""
    value = raw.get(column, "")
    if _is_blank(value):
        errors.append(ImportErrorRow(row_no, column, "", "必填字段为空"))
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(ImportErrorRow(row_no, column, value, "日期非法，要求 YYYY-MM-DD"))
        return None


def _required_text(raw: dict[str, str], column: str, row_no: int, errors: list[ImportErrorRow]) -> str:
    """校验必填文本并返回去空白后的值。"""
    value = raw.get(column, "").strip()
    if not value:
        errors.append(ImportErrorRow(row_no, column, "", "必填字段为空"))
    return value


def _validate_row(table_type: str, raw: dict[str, str], row_no: int) -> tuple[dict[str, object] | None, list[ImportErrorRow]]:
    """验证单行并转换成强类型记录；任何字段错误都会让该行不进入有效数据。"""
    errors: list[ImportErrorRow] = []
    record: dict[str, object] = {}

    if table_type == "orders":
        record["order_no"] = _required_text(raw, "order_no", row_no, errors)
        record["item_code"] = normalize_item_code(_required_text(raw, "item_code", row_no, errors))
        record["qty"] = _decimal_field(raw, "qty", row_no, errors, minimum=Decimal("0.000001"))
        record["due_date"] = _date_field(raw, "due_date", row_no, errors)
        record["customer"] = raw.get("customer", "").strip()

    elif table_type == "bom":
        record["parent_code"] = normalize_item_code(_required_text(raw, "parent_code", row_no, errors))
        record["child_code"] = normalize_item_code(_required_text(raw, "child_code", row_no, errors))
        record["qty_per"] = _decimal_field(raw, "qty_per", row_no, errors, minimum=Decimal("0.000001"))
        record["scrap_rate"] = _decimal_field(raw, "scrap_rate", row_no, errors, minimum=Decimal("0"), required=False) or Decimal("0")
        record["substitute_group"] = raw.get("substitute_group", "").strip() or None
        level_raw = raw.get("level", "").strip()
        if level_raw:
            try:
                level = int(level_raw)
                if level < 1 or level > 5:
                    errors.append(ImportErrorRow(row_no, "level", level_raw, "BOM 层级必须为 1-5"))
                record["level"] = level
            except ValueError:
                errors.append(ImportErrorRow(row_no, "level", level_raw, "层级必须是整数"))
        else:
            record["level"] = None

    elif table_type == "inventory":
        record["item_code"] = normalize_item_code(_required_text(raw, "item_code", row_no, errors))
        record["on_hand"] = _decimal_field(raw, "on_hand", row_no, errors, minimum=Decimal("0"))
        record["allocated"] = _decimal_field(raw, "allocated", row_no, errors, minimum=Decimal("0"))
        record["warehouse"] = raw.get("warehouse", "").strip()
        if isinstance(record.get("on_hand"), Decimal) and isinstance(record.get("allocated"), Decimal):
            if record["allocated"] > record["on_hand"]:
                errors.append(ImportErrorRow(row_no, "allocated", raw.get("allocated", ""), "已分配不能大于现有库存"))

    elif table_type == "in_transit":
        record["item_code"] = normalize_item_code(_required_text(raw, "item_code", row_no, errors))
        record["qty"] = _decimal_field(raw, "qty", row_no, errors, minimum=Decimal("0.000001"))
        record["eta_date"] = _date_field(raw, "eta_date", row_no, errors)
        record["batch_no"] = raw.get("batch_no", "").strip()
        record["supplier"] = raw.get("supplier", "").strip()

    return (None if errors else record), errors


def parse_table(table_type: str, content: bytes) -> ParsedTable:
    """解析单张 CSV，返回有效记录和所有错误行。"""
    if table_type not in TABLE_SCHEMAS:
        return ParsedTable(table_type=table_type, errors=[ImportErrorRow(1, "type", table_type, "不支持的表类型")])

    try:
        frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError, OSError) as exc:
        return ParsedTable(table_type=table_type, errors=[ImportErrorRow(1, "file", "", f"CSV 读取失败：{exc}")])

    original_headers = [str(column).strip() for column in frame.columns]
    headers = normalize_headers(original_headers)
    missing = [column for column in REQUIRED_COLUMNS[table_type] if column not in headers]

    # 规则无法覆盖时才调用模型，减少网络依赖；模型只能建议表头映射。
    if missing and settings.llm_enabled:
        from app.services.llm_extract import suggest_header_mapping

        suggestion = suggest_header_mapping(original_headers, table_type, use_llm=True)
        mapping = suggestion.get("mapping", {})
        headers = [mapping.get(original, normalized) for original, normalized in zip(original_headers, headers)]
        missing = [column for column in REQUIRED_COLUMNS[table_type] if column not in headers]

    if len(headers) != len(set(headers)):
        return ParsedTable(table_type=table_type, headers=headers, errors=[ImportErrorRow(1, "header", ",".join(original_headers), "归一后存在重复列")])
    frame.columns = headers
    if missing:
        errors = [ImportErrorRow(1, column, "", "缺少必填列") for column in missing]
        return ParsedTable(table_type=table_type, headers=headers, errors=errors)

    if frame.empty:
        return ParsedTable(table_type=table_type, headers=headers, errors=[ImportErrorRow(2, "file", "", "文件没有数据行")])

    records: list[dict[str, object]] = []
    errors: list[ImportErrorRow] = []
    for index, row in frame.iterrows():
        raw = {column: str(row[column]).strip() for column in headers}
        if all(not value for value in raw.values()):
            continue
        record, row_errors = _validate_row(table_type, raw, int(index) + 2)
        if row_errors:
            errors.extend(row_errors)
        elif record is not None:
            records.append(record)

    return ParsedTable(table_type=table_type, headers=headers, records=records, errors=errors)


def parse_bundle(files: dict[str, bytes]) -> dict[str, ParsedTable]:
    """解析四表文件字典；缺失表类型由调用方补齐空表并转为错误。"""
    return {table_type: parse_table(table_type, content) for table_type, content in files.items()}




