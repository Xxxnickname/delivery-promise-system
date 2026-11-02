from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_200_and_port_8003():
    """G2 启动门禁：/health 200，默认端口固定 8003。"""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["port"] == 8003


def test_template_endpoint_downloads_csv():
    """模板下载端点返回 CSV 和附件头。"""
    response = client.get("/api/templates/orders")
    assert response.status_code == 200
    assert "order_no" in response.text
    assert "attachment" in response.headers["content-disposition"]


def test_bundle_upload_and_expand_end_to_end():
    """四表上传后可直接展开 BOM，验证 G2 API 闭环。"""
    base = Path("samples/03")
    files = {
        "orders": ("orders.csv", (base / "orders.csv").read_bytes(), "text/csv"),
        "bom": ("bom.csv", (base / "bom.csv").read_bytes(), "text/csv"),
        "inventory": ("inventory.csv", (base / "inventory.csv").read_bytes(), "text/csv"),
        "in_transit": ("in_transit.csv", (base / "in_transit.csv").read_bytes(), "text/csv"),
    }
    response = client.post("/api/imports/bundle", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    batch_id = payload["data"]["batch_id"]
    assert payload["data"]["status"] == "COMMITTED"

    expand = client.post("/api/bom/expand", json={"batch_id": batch_id, "root_code": "FG-100", "qty": "10"})
    assert expand.status_code == 200
    data = expand.json()["data"]
    assert data["requirements"]["RM-005"] == "122.400000"
    assert data["requirements"]["RM-007"] == "50.000000"


def test_error_csv_endpoint_returns_located_errors():
    """导入失败后错误 CSV 必须包含行列原值。"""
    base = Path("samples/03")
    files = {
        "orders": ("sample_error_orders.csv", (base / "sample_error_orders.csv").read_bytes(), "text/csv"),
        "bom": ("bom.csv", (base / "bom.csv").read_bytes(), "text/csv"),
        "inventory": ("inventory.csv", (base / "inventory.csv").read_bytes(), "text/csv"),
        "in_transit": ("in_transit.csv", (base / "in_transit.csv").read_bytes(), "text/csv"),
    }
    response = client.post("/api/imports/bundle", files=files)
    batch_id = response.json()["data"]["batch_id"]
    error_response = client.get(f"/api/imports/{batch_id}/errors.csv")
    assert error_response.status_code == 200
    assert "row_no,column,value,reason" in error_response.text
    assert "due_date" in error_response.text
    assert "-5" in error_response.text
