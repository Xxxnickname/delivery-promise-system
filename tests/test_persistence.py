from pathlib import Path

from app.core.db import init_db
from app.services.import_batch import ImportService


def test_import_batch_survives_new_service_instance():
    """持久化模式下，新服务实例能从 SQLite 恢复导入批次。"""
    init_db()
    base = Path("samples/03")
    files = {key: (base / f"{key}.csv").read_bytes() for key in ("orders", "bom", "inventory", "in_transit")}
    writer = ImportService(persist=True)
    batch = writer.import_bundle(files)
    reader = ImportService(persist=True)
    restored = reader.get_batch(batch.batch_id)
    assert restored.status == batch.status
    assert restored.tables["orders"].ok_rows == batch.tables["orders"].ok_rows
    assert reader.calculate_promises(restored.batch_id)

