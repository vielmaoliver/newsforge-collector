# NewsForge Collector

Public zero-cost fallback collector for NewsForge.

This repository will run only on standard GitHub-hosted runners (`ubuntu-latest`) and only when the local NewsForge machine is offline. It must never contain editorial rules, publication credentials, article content, or private configuration.

## Cost rules

- Public repository only.
- Standard GitHub-hosted runners only.
- No larger runners.
- No artifacts or persistent cache unless explicitly reviewed.
- No Git LFS, Packages, Codespaces, paid cloud services, or AI APIs.
- Collector exits immediately when the local PC heartbeat is healthy.
