"""登录、当前用户与服务端权限依赖。"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import create_access_token, decode_access_token, verify_password
from app.core.config import settings
from app.core.db import SessionLocal, UserRow
from app.core.errors import ApiError, api_ok


router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """请求级用户对象，不包含密码哈希。"""

    account: str
    name: str
    role: str
    tenant_id: str
    customer_scopes: list[str]


class LoginRequest(BaseModel):
    account: str
    password: str


def _user_payload(row: UserRow) -> dict[str, object]:
    return {
        "account": row.account,
        "name": row.name,
        "role": row.role,
        "tenant_id": row.tenant_id,
        "department": row.department,
        "customer_scopes": row.customer_scopes,
    }


async def optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser | None:
    """解析 Bearer token；开发环境允许无登录，生产环境强制登录。"""
    if credentials is None:
        if settings.auth_required:
            raise ApiError(401, "未登录", status_code=401)
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise ApiError(401, "登录已失效，请重新登录", status_code=401) from exc
    with SessionLocal() as session:
        row = session.scalar(select(UserRow).where(UserRow.tenant_id == str(payload.get("tenant_id", "demo")), UserRow.account == str(payload.get("sub", ""))))
        if row is None or row.status != "启用":
            raise ApiError(401, "账号不存在或已停用", status_code=401)
        return CurrentUser(row.account, row.name, row.role, row.tenant_id, row.customer_scopes or [])


async def require_auth(user: CurrentUser | None = Depends(optional_current_user)) -> CurrentUser | None:
    """供 APIRouter 使用的统一鉴权依赖。"""
    return user


def require_roles(*roles: str):
    """构造角色校验依赖；未登录用户只在开发模式被允许。"""
    async def dependency(user: CurrentUser | None = Depends(optional_current_user)):
        if user is None:
            return None
        if user.role not in roles and user.role != "admin":
            raise ApiError(403, "当前角色无权执行该操作", status_code=403)
        return user
    return dependency


@router.post("/login")
async def login(request: Request, payload: LoginRequest):
    """账号密码登录，返回短期 JWT。"""
    with SessionLocal() as session:
        row = session.scalar(select(UserRow).where(UserRow.tenant_id == "demo", UserRow.account == payload.account.strip()))
        if row is None or row.status != "启用" or not verify_password(payload.password, row.password_hash):
            raise ApiError(401, "账号或密码错误", status_code=401)
        token = create_access_token(row.account, row.role, row.tenant_id)
        return api_ok({"access_token": token, "token_type": "bearer", "user": _user_payload(row)}, trace_id=getattr(request.state, "trace_id", ""))


@router.get("/me")
async def me(request: Request, user: CurrentUser | None = Depends(require_auth)):
    """读取当前用户；生产模式未登录时返回 401。"""
    if user is None:
        raise ApiError(401, "未登录", status_code=401)
    return api_ok({"account": user.account, "name": user.name, "role": user.role, "tenant_id": user.tenant_id, "customer_scopes": user.customer_scopes}, trace_id=getattr(request.state, "trace_id", ""))
