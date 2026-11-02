"""服务端 xlsx 导出任务：同一用户同时只允许一个任务。"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.errors import ApiError, ErrorCode


@dataclass
class ExportTask:
    """导出任务状态；progress 用于前端轮询展示。"""

    task_id: str
    user_id: str
    kind: str
    status: str = "PENDING"
    progress: int = 0
    file_path: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "download_url": f"/api/export/{self.task_id}/download" if self.file_path else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(timespec="seconds"),
        }


class ExportService:
    """线程池导出服务；生产环境可无缝替换为 Celery worker。"""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, ExportTask] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="plan-export")

    def _write_xlsx(self, task: ExportTask, rows: list[dict[str, Any]], sheet_name: str) -> None:
        """在后台线程中生成 xlsx，避免阻塞请求线程。"""
        try:
            task.status = "RUNNING"
            task.progress = 30
            path = self.output_dir / f"{task.task_id}.xlsx"
            frame = pd.DataFrame(rows)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                frame.to_excel(writer, sheet_name=sheet_name, index=False)
            task.progress = 100
            task.status = "SUCCESS"
            task.file_path = str(path)
        except Exception as exc:  # pragma: no cover - 兜底状态，测试覆盖成功路径
            task.status = "FAILED"
            task.error = str(exc)

    def create(self, user_id: str, kind: str, rows: list[dict[str, Any]], sheet_name: str = "report") -> ExportTask:
        """创建导出任务；同一用户有未完成任务时返回 429。"""
        with self._lock:
            if any(task.user_id == user_id and task.status in {"PENDING", "RUNNING"} for task in self._tasks.values()):
                raise ApiError(429, "同一用户同时只允许一个导出任务", status_code=429)
            task_id = f"exp_{datetime.now():%Y%m%d%H%M%S%f}"
            task = ExportTask(task_id=task_id, user_id=user_id, kind=kind)
            self._tasks[task_id] = task
        self._executor.submit(self._write_xlsx, task, rows, sheet_name)
        return task

    def get(self, task_id: str) -> ExportTask:
        """读取任务状态；不存在返回 1002。"""
        task = self._tasks.get(task_id)
        if task is None:
            raise ApiError(ErrorCode.NOT_FOUND, "导出任务不存在", status_code=404, data={"task_id": task_id})
        return task


from app.core.config import BASE_DIR

export_service = ExportService(BASE_DIR / "reports" / "exports")
