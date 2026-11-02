"""Celery 入口占位：G2 只建立队列骨架，导入/导出异步化在后续阶段接入。"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery_app = Celery("plan", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task(name="plan.ping")
def ping() -> str:
    """最小连通性任务，便于后续验证 worker 是否启动。"""
    return "pong"
