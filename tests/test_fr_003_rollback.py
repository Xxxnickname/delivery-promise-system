from pathlib import Path

from app.services.import_batch import ImportService


def test_fr_003_rollback_keeps_zero_imported_rows():
    """FR-003：默认全或无，任一表失败时整批回滚且实际入库为 0。"""
    base = Path("samples/03")
    files = {
        "orders": (base / "sample_error_orders.csv").read_bytes(),
        "bom": (base / "bom.csv").read_bytes(),
        "inventory": (base / "inventory.csv").read_bytes(),
        "in_transit": (base / "in_transit.csv").read_bytes(),
    }
    batch = ImportService().import_bundle(files, mode="ALL_OR_NOTHING")
    assert batch.status == "ROLLED_BACK"
    assert batch.committed is False
    assert batch.imported_rows == 0
    assert batch.failed_rows == 2
    assert batch.to_dict()["error_file"].endswith("errors.csv")


def test_fr_003_partial_requires_explicit_confirmation():
    """FR-003：部分导入必须显式 allow_partial=True，否则拒绝。"""
    import pytest
    from app.core.errors import ApiError

    files = {"orders": b"order_no,item_code,qty,due_date\nSO-1,FG-1,1,2026-12-01\n"}
    service = ImportService()
    with pytest.raises(ApiError):
        service.import_bundle(files, mode="PARTIAL_WITH_AUDIT", allow_partial=False)


def test_fr_003_partial_import_keeps_valid_rows_with_audit():
    """FR-003：显式部分导入时保留其他表有效行，并标记 PARTIAL_IMPORTED。"""
    base = Path("samples/03")
    files = {
        "orders": (base / "sample_error_orders.csv").read_bytes(),
        "bom": (base / "bom.csv").read_bytes(),
        "inventory": (base / "inventory.csv").read_bytes(),
        "in_transit": (base / "in_transit.csv").read_bytes(),
    }
    batch = ImportService().import_bundle(files, mode="PARTIAL_WITH_AUDIT", allow_partial=True)
    assert batch.status == "PARTIAL_IMPORTED"
    assert batch.committed is True
    assert batch.failed_rows == 2
    assert batch.imported_rows == 19


def test_fr_003_same_bundle_is_idempotent():
    """FR-003：同一租户、同一模式和同一文件哈希返回同一批次。"""
    base = Path("samples/03")
    files = {
        "orders": (base / "orders.csv").read_bytes(),
        "bom": (base / "bom.csv").read_bytes(),
        "inventory": (base / "inventory.csv").read_bytes(),
        "in_transit": (base / "in_transit.csv").read_bytes(),
    }
    service = ImportService()
    first = service.import_bundle(files)
    second = service.import_bundle(files)
    assert first.batch_id == second.batch_id

