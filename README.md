# NewsForge Collector

Public zero-cost fallback collector for NewsForge.

This repository runs only on standard GitHub-hosted runners (`ubuntu-latest`) and only when the local NewsForge machine is offline. It never contains editorial rules, WordPress credentials, article bodies, images, private source policy, or local synchronization credentials.

## Flow

1. Read public `/v1/status` from the NewsForge Cloud API.
2. Exit immediately when the local PC heartbeat is healthy.
3. If the PC is offline, fetch the authorized collector configuration using the collector-only HMAC secret.
4. Fetch RSS/Atom or Google News Sitemap metadata using conditional HTTP (`ETag` / `Last-Modified`) when available.
5. Send candidate metadata only to D1 through `/v1/candidates`.
6. Exit. Full extraction, editorial work, media processing and publication stay on the local NewsForge PC.

## Required GitHub configuration

Repository variable:

- `NEWSFORGE_COLLECTOR_ENABLED` = `true` only after the Worker/D1 endpoint is ready.
- `NEWSFORGE_API_URL` = deployed NewsForge Cloud API URL.

Repository secret:

- `COLLECTOR_INGEST_SECRET` = collector-only HMAC secret.

The collector never receives `LOCAL_SYNC_SECRET` or any WordPress credential.

## Cost rules

- Public repository only.
- Standard GitHub-hosted runner only.
- `timeout-minutes: 10`.
- No larger runners.
- No Actions artifacts or persistent cache.
- No Git LFS, Packages, Codespaces, paid cloud services, or AI APIs.
- Collector exits immediately when the local PC heartbeat is healthy.
- The scheduled collection job is disabled unless `NEWSFORGE_COLLECTOR_ENABLED == true`.

## Logs

The collector prints structured JSON lines with short codes such as `GHA-000`, `GHA-001`, `COL-000`, and `COL-001`. See `docs/ERRORS.md`.

## Tests

Local development uses Python 3.12. Run:

```text
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy collector
```
