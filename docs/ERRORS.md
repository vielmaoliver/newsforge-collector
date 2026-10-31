# Collector event codes

The public collector writes one-line JSON events to stdout so GitHub Actions logs remain machine-readable.

| Code | Level | Meaning |
|---|---|---|
| `GHA-000` | INFO | Collector started, skipped because PC is online, or completed normally |
| `GHA-001` | ERROR | Collector run failed |
| `COL-000` | INFO | One source was fetched and parsed successfully |
| `COL-001` | WARNING | One source failed; the run may continue with other sources |
| `CFG-001` | ERROR | Required environment configuration is missing |
| `SYN-001` | ERROR | Cloud API synchronization failed |
| `WEB-001` | WARNING | Network request failed |

Cloud API responses may additionally expose `CFW-*`, `D1-*`, and `SEC-*` codes. Those are produced by the private NewsForge Cloud API and are never redefined by the public collector.
