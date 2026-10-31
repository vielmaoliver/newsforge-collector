from __future__ import annotations

import json
import os
from dataclasses import asdict

from pydantic import ValidationError

from collector.engine import collect_once
from collector.logging import emit


def main() -> None:
    api_url = os.environ.get("NEWSFORGE_API_URL", "").strip()
    secret = os.environ.get("COLLECTOR_INGEST_SECRET", "").strip()
    if not api_url:
        emit("ERROR", "CFG-001", "NEWSFORGE_API_URL is missing")
        raise SystemExit(2)
    if not secret:
        emit("ERROR", "CFG-001", "COLLECTOR_INGEST_SECRET is missing")
        raise SystemExit(2)

    try:
        stats = collect_once(api_url=api_url, collector_secret=secret)
    except (OSError, TypeError, ValueError, ValidationError) as exc:
        emit("ERROR", "GHA-001", f"Collector failed: {type(exc).__name__}: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        emit("ERROR", "GHA-001", f"Unhandled collector failure: {type(exc).__name__}: {exc}")
        raise SystemExit(1) from exc

    print(json.dumps(asdict(stats), indent=2, ensure_ascii=False))
    if stats.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
