import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _upload_sample():
    base = Path("samples/03")
    files = {
        "orders": ("orders.csv", (base / "orders.csv").read_bytes(), "text/csv"),
        "bom": ("bom.csv", (base / "bom.csv").read_bytes(), "text/csv"),
        "inventory": ("inventory.csv", (base / "inventory.csv").read_bytes(), "text/csv"),
        "in_transit": ("in_transit.csv", (base / "in_transit.csv").read_bytes(), "text/csv"),
    }
    response = client.post("/api/imports/bundle", files=files)
    assert response.status_code == 200
    return response.json()["data"]["batch_id"]


def test_g3_orders_simulate_snapshot_export_flow():
    """G3/G4 API 闭环：订单计算、模拟、快照、导出。"""
    batch_id = _upload_sample()
    orders = client.get("/api/orders", params={"batch_id": batch_id})
    assert orders.status_code == 200
    order_list = orders.json()["data"]["orders"]
    assert len(order_list) >= 3
    promise = client.get(f"/api/orders/{order_list[0]['order_no']}/promise", params={"batch_id": batch_id})
    assert promise.status_code == 200

    sim = client.post("/api/simulate", json={
        "batch_id": batch_id,
        "order_no": order_list[0]["order_no"],
        "mode": "insert",
        "qty": "500",
        "expect_date": "2026-11-08",
    })
    assert sim.status_code == 200
    assert sim.json()["data"]["not_persisted"] is True

    snap_a = client.post("/api/snapshots", params={"batch_id": batch_id}).json()["data"]["snapshot_id"]
    snap_b = client.post("/api/snapshots", params={"batch_id": batch_id}).json()["data"]["snapshot_id"]
    compare = client.get("/api/snapshots/compare", params={"from": snap_a, "to": snap_b})
    assert compare.status_code == 200
    assert compare.json()["data"]["summary"]["changed"] == 0

    export = client.post("/api/export", json={"kind": "kit_report", "batch_id": batch_id}, headers={"X-User-Id": "g3-export-user"})
    assert export.status_code == 200
    task = export.json()["data"]
    for _ in range(50):
        current = client.get(f"/api/export/{task['task_id']}").json()["data"]
        if current["status"] == "SUCCESS":
            break
        time.sleep(0.05)
    assert current["status"] == "SUCCESS"
    download = client.get(current["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument")
    assert download.content[:2] == b"PK"


def test_fr_015_explain_api_has_no_digits():
    """解释接口返回结构化文本，且不携带新数字。"""
    batch_id = _upload_sample()
    response = client.get("/api/orders/SO-DEMO-001/explain", params={"batch_id": batch_id})
    assert response.status_code == 200
    assert not any(char.isdigit() for char in response.json()["data"]["text"])
