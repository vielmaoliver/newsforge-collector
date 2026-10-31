from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from collector.api import CloudApiClient
from collector.logging import emit
from collector.models import CandidatePayload, RemoteSource, SourceFetchState
from collector.sources import fetch_timestamp, parse_feed, parse_news_sitemap


@dataclass(slots=True)
class CollectorStats:
    pc_online: bool = False
    sources: int = 0
    fetched: int = 0
    not_modified: int = 0
    candidates: int = 0
    inserted: int = 0
    duplicates: int = 0
    errors: int = 0


def _source_headers(source: RemoteSource) -> dict[str, str]:
    headers: dict[str, str] = {}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified
    return headers


def _parse_source(content: bytes, source: RemoteSource, *, discovered_at: datetime) -> list[CandidatePayload]:
    if source.type in {"rss", "atom"}:
        return parse_feed(content, source, discovered_at=discovered_at)
    if source.type == "news_sitemap":
        return parse_news_sitemap(content, source, discovered_at=discovered_at)
    raise ValueError(f"unsupported source type: {source.type}")


def _chunks(items: list[CandidatePayload], size: int = 500) -> list[list[CandidatePayload]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def collect_once(
    *,
    api_url: str,
    collector_secret: str,
    api_transport: httpx.BaseTransport | None = None,
    source_transport: httpx.BaseTransport | None = None,
) -> CollectorStats:
    stats = CollectorStats()
    api = CloudApiClient(
        api_url,
        collector_secret=collector_secret,
        transport=api_transport,
    )
    try:
        try:
            status = api.public_status().payload
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            emit("ERROR", "SYN-001", f"Cloud API status failed: {type(exc).__name__}: {exc}")
            raise
        stats.pc_online = bool(status.get("pc_online"))
        if stats.pc_online:
            emit("INFO", "GHA-000", "Local NewsForge PC is online; fallback collector exits")
            return stats

        try:
            config_payload = api.collector_config().payload
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            emit("ERROR", "SYN-001", f"Collector config sync failed: {type(exc).__name__}: {exc}")
            raise
        raw_sources = config_payload.get("sources", [])
        if not isinstance(raw_sources, list):
            raise TypeError("collector config sources must be a list")
        sources = [RemoteSource.model_validate(item) for item in raw_sources]
        stats.sources = len(sources)

        candidates: list[CandidatePayload] = []
        states: list[SourceFetchState] = []
        with httpx.Client(
            timeout=25.0,
            follow_redirects=True,
            transport=source_transport,
            headers={"User-Agent": "NewsForgeCollector/0.1 (+public fallback metadata collector)"},
        ) as source_client:
            for source in sources:
                fetch_at = fetch_timestamp()
                try:
                    response = source_client.get(str(source.url), headers=_source_headers(source))
                    if response.status_code == 304:
                        stats.not_modified += 1
                        states.append(
                            SourceFetchState(
                                source_id=source.id,
                                etag=source.etag,
                                last_modified=source.last_modified,
                                last_fetch=fetch_at,
                            )
                        )
                        continue
                    response.raise_for_status()
                    discovered = datetime.now(UTC)
                    parsed = _parse_source(response.content, source, discovered_at=discovered)
                    candidates.extend(parsed)
                    stats.fetched += 1
                    states.append(
                        SourceFetchState(
                            source_id=source.id,
                            etag=response.headers.get("etag") or source.etag,
                            last_modified=response.headers.get("last-modified") or source.last_modified,
                            last_fetch=fetch_at,
                        )
                    )
                    emit(
                        "INFO",
                        "COL-000",
                        "Source metadata collected",
                        source_id=source.id,
                        candidates=len(parsed),
                    )
                except (httpx.HTTPError, ValueError) as exc:
                    stats.errors += 1
                    emit(
                        "WARNING",
                        "COL-001",
                        f"Source collection failed: {type(exc).__name__}: {exc}",
                        source_id=source.id,
                    )

        stats.candidates = len(candidates)
        batches = _chunks(candidates) or [[]]
        for index, batch in enumerate(batches):
            payload: dict[str, Any] = {
                "candidates": [item.model_dump(mode="json") for item in batch],
                "source_states": [item.model_dump(mode="json") for item in states]
                if index == len(batches) - 1
                else [],
            }
            try:
                result = api.ingest(payload).payload
            except (httpx.HTTPError, TypeError, ValueError) as exc:
                emit("ERROR", "SYN-001", f"Candidate ingest failed: {type(exc).__name__}: {exc}")
                raise
            stats.inserted += int(result.get("inserted") or 0)
            stats.duplicates += int(result.get("duplicates") or 0)

        emit(
            "INFO",
            "GHA-000",
            "Fallback collection completed",
            **asdict(stats),
        )
        return stats
    finally:
        api.close()
