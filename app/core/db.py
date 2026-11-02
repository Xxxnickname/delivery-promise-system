"""SQLAlchemy 数据库层：用户、导入批次、快照与审计。"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Generator

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import BASE_DIR, settings


class Base(DeclarativeBase):
    """所有持久化表共享的声明式基类。"""


class UserRow(Base):
    """登录用户；密码只保存 PBKDF2 哈希。"""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="demo", index=True)
    account: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    department: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="启用")
    password_hash: Mapped[str] = mapped_column(String(256))
    customer_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint("tenant_id", "account", name="uq_user_tenant_account"),)


class ImportBatchRow(Base):
    """导入批次持久化；payload 保存原始 CSV 的 base64，便于重启后重新解析。"""

    __tablename__ = "import_batches_v2"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="demo", index=True)
    batch_id: Mapped[str] = mapped_column(String(100), index=True)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "batch_id", name="uq_batch_tenant_id"),)


class SnapshotRow(Base):
    """计算快照持久化；items 为按订单承诺字典列表。"""

    __tablename__ = "calc_snapshots_v2"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="demo", index=True)
    snapshot_id: Mapped[str] = mapped_column(String(100), index=True)
    calc_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("tenant_id", "snapshot_id", name="uq_snapshot_tenant_id"),)


class AuditLogRow(Base):
    """关键操作审计；detail 保存不含密钥的结构化细节。"""

    __tablename__ = "audit_logs_v2"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="demo", index=True)
    actor: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    trace_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def _engine_url(url: str) -> str:
    """兼容 Docker 的 postgresql:// DSN 与 SQLAlchemy 驱动名。"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(
    _engine_url(settings.database_url),
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """建表并写入演示用户；生产环境迁移仍由 migrations 管理。"""
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI/服务层使用的数据库会话生成器。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def seed_demo_users() -> None:
    """从 static mock 用户表初始化演示账号，统一密码为 demo123。"""
    from app.core.auth import hash_password

    mock_path = BASE_DIR / "app" / "static" / "mock" / "users.json"
    if not mock_path.exists():
        return
    payload = json.loads(mock_path.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        for item in payload.get("users", []):
            exists = session.scalar(select(UserRow).where(UserRow.tenant_id == "demo", UserRow.account == item["account"]))
            if exists:
                continue
            session.add(UserRow(
                tenant_id="demo",
                account=item["account"],
                name=item["name"],
                role=item["role"],
                department=item.get("department", ""),
                status=item.get("status", "启用"),
                password_hash=hash_password("demo123"),
                customer_scopes=item.get("customer_scopes", []),
            ))
        session.commit()


def audit(actor: str, action: str, target: str, detail: dict[str, Any] | None = None, trace_id: str = "", tenant_id: str = "demo") -> None:
    """写一条审计日志；失败不阻断主业务，但由调用方决定是否记录异常。"""
    with SessionLocal() as session:
        session.add(AuditLogRow(tenant_id=tenant_id, actor=actor, action=action, target=target, detail=detail or {}, trace_id=trace_id))
        session.commit()


def save_import_batch(batch) -> None:
    """保存导入批次及原始 CSV；使用 merge 保证重复写入幂等。"""
    payload = {"files": {key: base64.b64encode(value).decode("ascii") for key, value in batch.raw_files.items()}}
    with SessionLocal() as session:
        existing = session.scalar(select(ImportBatchRow).where(ImportBatchRow.tenant_id == batch.tenant_id, ImportBatchRow.batch_id == batch.batch_id))
        row = existing or ImportBatchRow(tenant_id=batch.tenant_id, batch_id=batch.batch_id)
        row.file_hash = batch.file_hash
        row.mode = batch.mode
        row.status = batch.status
        row.created_at = batch.created_at
        row.payload = payload
        session.add(row)
        session.commit()


def load_import_batch(batch_id: str, tenant_id: str):
    """从数据库恢复导入批次；重新解析原始 CSV，避免 JSON 丢 Decimal/date 类型。"""
    from app.models.domain import ParsedTable
    from app.services.import_batch import ImportBatch
    from app.services.parse_tables import parse_table

    with SessionLocal() as session:
        row = session.scalar(select(ImportBatchRow).where(ImportBatchRow.tenant_id == tenant_id, ImportBatchRow.batch_id == batch_id))
        if row is None:
            return None
        raw_files = {key: base64.b64decode(value) for key, value in (row.payload or {}).get("files", {}).items()}
        tables = {key: parse_table(key, value) for key, value in raw_files.items()}
        for key in ("orders", "bom", "inventory", "in_transit"):
            tables.setdefault(key, ParsedTable(table_type=key))
        return ImportBatch(
            batch_id=row.batch_id,
            tenant_id=row.tenant_id,
            mode=row.mode,
            status=row.status,
            file_hash=row.file_hash,
            created_at=row.created_at,
            tables=tables,
            committed=row.status != "ROLLED_BACK",
            raw_files=raw_files,
        )


def latest_import_batch(tenant_id: str):
    """查询最近一次已提交批次并恢复为领域对象。"""
    with SessionLocal() as session:
        row = session.scalar(
            select(ImportBatchRow)
            .where(ImportBatchRow.tenant_id == tenant_id, ImportBatchRow.status.in_(["COMMITTED", "PARTIAL_IMPORTED"]))
            .order_by(ImportBatchRow.created_at.desc())
        )
        if row is None:
            return None
        return load_import_batch(row.batch_id, tenant_id)


def save_snapshot(snapshot) -> None:
    """持久化快照；items 使用 JSON 保存。"""
    with SessionLocal() as session:
        existing = session.scalar(select(SnapshotRow).where(SnapshotRow.tenant_id == "demo", SnapshotRow.snapshot_id == snapshot.snapshot_id))
        row = existing or SnapshotRow(tenant_id="demo", snapshot_id=snapshot.snapshot_id)
        row.calc_version = snapshot.calc_version
        row.created_at = snapshot.created_at
        row.items = snapshot.items
        session.add(row)
        session.commit()


def load_snapshot(snapshot_id: str, tenant_id: str = "demo"):
    """从数据库恢复快照对象。"""
    from app.services.snapshot import Snapshot

    with SessionLocal() as session:
        row = session.scalar(select(SnapshotRow).where(SnapshotRow.tenant_id == tenant_id, SnapshotRow.snapshot_id == snapshot_id))
        if row is None:
            return None
        return Snapshot(snapshot_id=row.snapshot_id, calc_version=row.calc_version, created_at=row.created_at, items=row.items)

