"""Celery 导出任务占位：生产环境把 xlsx 生成移出 web 进程。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.workers.celery_app import celery_app


@celery_app.task(name="plan.export_xlsx")
def export_xlsx(rows: list[dict[str, Any]], output_path: str, sheet_name: str = "report") -> str:
    """将行数据写成 xlsx 并返回文件路径。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)
    return str(path)
