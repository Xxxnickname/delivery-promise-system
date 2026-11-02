from pathlib import Path

from app.services.parse_tables import parse_table


def test_fr_002_invalid_date_and_qty_are_located():
    """FR-002：非法日期和负数数量必须可定位到行/列/原值。"""
    content = Path("samples/03/sample_error_orders.csv").read_bytes()
    table = parse_table("orders", content)
    assert table.ok_rows == 0
    assert len(table.errors) == 2
    by_column = {error.column: error for error in table.errors}
    assert by_column["qty"].row_no == 2
    assert by_column["qty"].value == "-5"
    assert by_column["due_date"].row_no == 3
    assert by_column["due_date"].value == "2026/02/30"


def test_empty_file_returns_file_error():
    """空文件不能抛裸 Pandas 异常，必须返回可定位错误。"""
    table = parse_table("orders", b"")
    assert table.errors[0].column == "file"
    assert "读取失败" in table.errors[0].reason
