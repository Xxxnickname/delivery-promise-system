from pathlib import Path

from app.services.parse_tables import parse_table


def test_fr_004_chinese_headers_and_item_code_normalization():
    """FR-004：中文表头与带空格料号必须归一，不得因写法差异新增物料。"""
    table = parse_table("bom", Path("samples/03/bom.csv").read_bytes())
    assert table.ok
    assert table.headers[:3] == ["parent_code", "child_code", "qty_per"]
    assert any(record["child_code"] == "RM-005" for record in table.records)


def test_fr_004_unknown_item_alias_enters_pending_queue():
    """FR-004：待确认别名按租户隔离并去重。"""
    from app.services.alias import PendingAlias, PendingAliasQueue

    queue = PendingAliasQueue()
    item = PendingAlias("tenant-a", "orders", "伺服驱动", "伺服驱动", "未匹配标准料号")
    queue.add(item)
    queue.add(item)
    assert len(queue.list("tenant-a")) == 1
    assert queue.list("tenant-b") == []
