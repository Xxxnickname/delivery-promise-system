"""运行配置：端口、目录、数据库与模型参数集中从环境变量读取。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples" / "03"


def _env_int(name: str, default: int) -> int:
    """读取整数环境变量；非法值回退默认值，避免启动时静默使用错误端口。"""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """应用运行参数：端口、目录、数据库、鉴权与模型配置。"""

    app_name: str = "订单交期测算与缺料预警"
    app_env: str = os.getenv("APP_ENV", "development")
    app_port: int = _env_int("APP_PORT", 8003)
    db_dsn: str = os.getenv("DB_DSN", "postgresql://plan:plan@postgres:5432/plan")
    database_url: str = os.getenv("DATABASE_URL") or (os.getenv("DB_DSN", "postgresql://plan:plan@postgres:5432/plan") if os.getenv("APP_ENV", "development") == "production" else "sqlite:///./plan.db")
    auth_secret: str = os.getenv("AUTH_SECRET", "dev-only-change-me-please-use-32-bytes-min")
    access_token_minutes: int = _env_int("ACCESS_TOKEN_MINUTES", 60)
    auth_required: bool = os.getenv("AUTH_REQUIRED", "false").lower() in {"1", "true", "yes"}
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    model_provider: str = os.getenv("MODEL_PROVIDER", "deepseek")
    model_base_url: str = os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    model_name: str = os.getenv("MODEL_NAME", "deepseek-flash")
    llm_enabled: bool = os.getenv("LLM_ENABLED", "false").lower() in {"1", "true", "yes"}
    model_timeout_seconds: int = _env_int("MODEL_TIMEOUT_SECONDS", 20)
    model_api_key: str = os.getenv("MODEL_API_KEY", "")
    max_upload_mb: int = _env_int("MAX_UPLOAD_MB", 20)
    max_bom_depth: int = _env_int("MAX_BOM_DEPTH", 5)
    production_lead_days: int = _env_int("PRODUCTION_LEAD_DAYS", 3)
    export_max_rows: int = _env_int("EXPORT_MAX_ROWS", 50000)
    timezone: str = "Asia/Shanghai"
    static_dir: Path = STATIC_DIR
    samples_dir: Path = SAMPLES_DIR


settings = Settings()







