from fastapi.testclient import TestClient

from app.core.db import init_db, seed_demo_users
from app.main import app


def test_auth_login_me_and_wrong_password():
    """登录返回 JWT，me 能识别身份，错误密码 401。"""
    init_db()
    seed_demo_users()
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"account": "sales01", "password": "demo123"})
        assert login.status_code == 200
        payload = login.json()["data"]
        assert payload["user"]["role"] == "sales"
        token = payload["access_token"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["account"] == "sales01"
        bad = client.post("/api/auth/login", json={"account": "sales01", "password": "wrong"})
        assert bad.status_code == 401

