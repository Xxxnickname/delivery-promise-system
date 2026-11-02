"""PostgreSQL 初始化表结构（0001_init）。

G2 的本地测试使用内存服务，不在测试中连接 PostgreSQL；此迁移用于后续
容器环境和 G3 持久化接入。执行方式：由迁移工具逐条执行 STATEMENTS。
"""
from __future__ import annotations

from typing import Any


STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS items (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      item_code VARCHAR(64) NOT NULL,
      item_name VARCHAR(200) NOT NULL DEFAULT '',
      item_type VARCHAR(20) NOT NULL DEFAULT 'raw',
      unit VARCHAR(20) NOT NULL DEFAULT '',
      level SMALLINT,
      UNIQUE (tenant_id, item_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bom_edges (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      parent_code VARCHAR(64) NOT NULL,
      child_code VARCHAR(64) NOT NULL,
      qty_per NUMERIC(18,6) NOT NULL CHECK (qty_per > 0),
      scrap_rate NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (scrap_rate >= 0),
      substitute_group VARCHAR(64),
      level SMALLINT CHECK (level BETWEEN 1 AND 5)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      item_code VARCHAR(64) NOT NULL,
      on_hand NUMERIC(18,6) NOT NULL CHECK (on_hand >= 0),
      allocated NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (allocated >= 0),
      warehouse VARCHAR(64) NOT NULL DEFAULT '',
      UNIQUE (tenant_id, item_code, warehouse)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS in_transit (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      item_code VARCHAR(64) NOT NULL,
      qty NUMERIC(18,6) NOT NULL CHECK (qty > 0),
      eta_date DATE NOT NULL,
      batch_no VARCHAR(64) NOT NULL DEFAULT '',
      supplier VARCHAR(200) NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      order_no VARCHAR(64) NOT NULL,
      customer VARCHAR(200) NOT NULL DEFAULT '',
      due_date DATE NOT NULL,
      status VARCHAR(32) NOT NULL DEFAULT 'active',
      UNIQUE (tenant_id, order_no)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_lines (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      order_no VARCHAR(64) NOT NULL,
      item_code VARCHAR(64) NOT NULL,
      qty NUMERIC(18,6) NOT NULL CHECK (qty > 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calc_snapshots (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      snapshot_id VARCHAR(64) NOT NULL,
      calc_version VARCHAR(64) NOT NULL,
      payload JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (tenant_id, snapshot_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS import_batches (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      batch_id VARCHAR(64) NOT NULL,
      file_hash VARCHAR(64) NOT NULL,
      mode VARCHAR(32) NOT NULL,
      status VARCHAR(32) NOT NULL,
      ok_rows INTEGER NOT NULL DEFAULT 0,
      failed_rows INTEGER NOT NULL DEFAULT 0,
      imported_rows INTEGER NOT NULL DEFAULT 0,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (tenant_id, batch_id),
      UNIQUE (tenant_id, file_hash, mode)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL,
      actor VARCHAR(64) NOT NULL DEFAULT '',
      action VARCHAR(64) NOT NULL,
      target VARCHAR(200) NOT NULL DEFAULT '',
      detail JSONB NOT NULL DEFAULT '{}'::jsonb,
      trace_id VARCHAR(64) NOT NULL DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
]


EXTRA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS users (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL DEFAULT 'demo',
      account VARCHAR(64) NOT NULL,
      name VARCHAR(100) NOT NULL,
      role VARCHAR(20) NOT NULL,
      department VARCHAR(100) NOT NULL DEFAULT '',
      status VARCHAR(20) NOT NULL DEFAULT '启用',
      password_hash VARCHAR(256) NOT NULL,
      customer_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (tenant_id, account)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS import_batches_v2 (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL DEFAULT 'demo',
      batch_id VARCHAR(100) NOT NULL,
      file_hash VARCHAR(64) NOT NULL,
      mode VARCHAR(40) NOT NULL,
      status VARCHAR(40) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      UNIQUE (tenant_id, batch_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calc_snapshots_v2 (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL DEFAULT 'demo',
      snapshot_id VARCHAR(100) NOT NULL,
      calc_version VARCHAR(64) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      items JSONB NOT NULL DEFAULT '[]'::jsonb,
      UNIQUE (tenant_id, snapshot_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs_v2 (
      id BIGSERIAL PRIMARY KEY,
      tenant_id VARCHAR(64) NOT NULL DEFAULT 'demo',
      actor VARCHAR(64) NOT NULL DEFAULT '',
      action VARCHAR(64) NOT NULL,
      target VARCHAR(200) NOT NULL DEFAULT '',
      detail JSONB NOT NULL DEFAULT '{}'::jsonb,
      trace_id VARCHAR(64) NOT NULL DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
]

def run(connection: Any) -> None:
    """在给定数据库连接上逐条执行建表语句。"""
    with connection.cursor() as cursor:
        for statement in [*STATEMENTS, *EXTRA_STATEMENTS]:
            cursor.execute(statement)
    connection.commit()

