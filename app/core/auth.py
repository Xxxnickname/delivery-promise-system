"""密码哈希与 JWT 会话。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings


PBKDF2_ITERATIONS = 260000


def hash_password(password: str, salt: bytes | None = None) -> str:
    """使用 PBKDF2-HMAC-SHA256 生成可验证的密码哈希。"""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2${}${}${}".format(PBKDF2_ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, encoded: str) -> bool:
    """恒定时间比较密码哈希，避免逐字节泄露。"""
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


def create_access_token(account: str, role: str, tenant_id: str = "demo") -> str:
    """签发短期 JWT，前端只保存 token，不保存密码。"""
    now = datetime.now(timezone.utc)
    payload = {"sub": account, "role": role, "tenant_id": tenant_id, "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """解码并校验 JWT；调用方负责把异常映射为 401。"""
    return jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
