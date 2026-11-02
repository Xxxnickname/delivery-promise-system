"""检查 DeepSeek/OpenAI-compatible 表头映射是否可用。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.services.llm_extract import suggest_header_mapping


def main() -> int:
    """只输出状态和映射结果，不输出任何 Key。"""
    result = suggest_header_mapping(["奇怪订单号列", "物料编码", "数量", "客户交期"], "orders", use_llm=True)
    safe = {
        "provider": settings.model_provider,
        "model": settings.model_name,
        "base_url": settings.model_base_url,
        "enabled": settings.llm_enabled,
        "api_key_configured": bool(settings.model_api_key),
        "source": result.get("source"),
        "mapping": result.get("mapping"),
        "note": result.get("note"),
    }
    print(json.dumps(safe, ensure_ascii=False, indent=2))
    return 0 if result.get("llm_enabled") else 1


if __name__ == "__main__":
    raise SystemExit(main())
