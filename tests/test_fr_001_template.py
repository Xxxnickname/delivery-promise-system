from app.services.import_batch import ImportService


def test_fr_001_template_headers_for_four_tables():
    """FR-001：四类模板都必须有标准表头和示例行。"""
    service = ImportService()
    for table_type, first_header in {
        "orders": "order_no",
        "bom": "parent_code",
        "inventory": "item_code",
        "in_transit": "item_code",
    }.items():
        content = service.template(table_type)
        assert content.startswith("\ufeff")
        lines = content.strip().splitlines()
        assert len(lines) == 2
        assert lines[0].lstrip("\ufeff").split(",")[0] == first_header


