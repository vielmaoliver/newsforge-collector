from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def emit(level: str, code: str, message: str, **context: Any) -> None:
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
        "code": code,
        "component": "github_collector",
        "message": message,
        **context,
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)
