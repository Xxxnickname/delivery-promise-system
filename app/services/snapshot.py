"""计算快照与两次快照相减。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.errors import ApiError, ErrorCode
from app.models.domain import OrderPromise


@dataclass
class Snapshot:
    """一次计算的只读快照，payload 为订单承诺字典列表。"""

    snapshot_id: str
    calc_version: str
    created_at: datetime
    items: list[dict[str, Any]] = field(default_factory=list)


class SnapshotStore:
    """G3 内存快照仓库；写入时保存 calc_version，支持按订单对齐比较。"""

    def __init__(self, persist: bool = False) -> None:
        self._snapshots: dict[str, Snapshot] = {}
        self.persist = persist

    def create(self, promises: list[OrderPromise], calc_version: str) -> Snapshot:
        """保存一次计算快照，返回 snapshot_id。"""
        snapshot_id = f"snap_{datetime.now():%Y%m%d%H%M%S%f}_{uuid.uuid4().hex[:8]}"
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            calc_version=calc_version,
            created_at=datetime.now(),
            items=[promise.to_dict() for promise in promises],
        )
        self._snapshots[snapshot_id] = snapshot
        if self.persist:
            from app.core.db import save_snapshot
            save_snapshot(snapshot)
        return snapshot

    def get(self, snapshot_id: str) -> Snapshot:
        """读取快照；不存在返回 1002。"""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None and self.persist:
            from app.core.db import load_snapshot
            snapshot = load_snapshot(snapshot_id)
            if snapshot is not None:
                self._snapshots[snapshot_id] = snapshot
        if snapshot is None:
            raise ApiError(ErrorCode.NOT_FOUND, "快照不存在", status_code=404, data={"snapshot_id": snapshot_id})
        return snapshot

    def compare(self, from_id: str, to_id: str) -> dict[str, Any]:
        """按 order_no 对齐两次快照，输出变化/延后/提前与差异明细。"""
        before = {item["order_no"]: item for item in self.get(from_id).items}
        after = {item["order_no"]: item for item in self.get(to_id).items}
        items: list[dict[str, Any]] = []
        delayed = advanced = 0
        for order_no in sorted(set(before) | set(after)):
            old = before.get(order_no)
            new = after.get(order_no)
            if old is None or new is None:
                continue
            old_date = old.get("kit_date")
            new_date = new.get("kit_date")
            if not old_date or not new_date or old_date == new_date:
                continue
            delta = (datetime.fromisoformat(new_date).date() - datetime.fromisoformat(old_date).date()).days
            if delta > 0:
                delayed += 1
            else:
                advanced += 1
            items.append({"order_no": order_no, "customer": new.get("customer", ""), "from": old_date, "to": new_date, "delta_days": delta})
        positive = [item["delta_days"] for item in items if item["delta_days"] > 0]
        return {
            "from_snapshot": {"id": from_id, "calc_version": self.get(from_id).calc_version},
            "to_snapshot": {"id": to_id, "calc_version": self.get(to_id).calc_version},
            "summary": {"changed": len(items), "delayed": delayed, "advanced": advanced, "max_delay_days": max(positive) if positive else 0},
            "items": items,
        }


snapshot_store = SnapshotStore(persist=True)





