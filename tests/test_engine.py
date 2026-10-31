from __future__ import annotations

import json

import httpx

from collector.engine import collect_once


def test_collector_exits_when_pc_online() -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/status"
        return httpx.Response(200, json={"ok": True, "pc_online": True})

    def source_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"source fetch should not happen: {request.url}")

    stats = collect_once(
        api_url="https://api.example.com",
        collector_secret="secret",
        api_transport=httpx.MockTransport(api_handler),
        source_transport=httpx.MockTransport(source_handler),
    )
    assert stats.pc_online is True
    assert stats.sources == 0


def test_offline_collector_fetches_and_ingests() -> None:
    ingested: dict[str, object] = {}

    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/status":
            return httpx.Response(200, json={"ok": True, "pc_online": False})
        if request.url.path == "/v1/collector-config":
            assert request.headers.get("x-newsforge-key-id") == "collector"
            assert request.headers.get("x-newsforge-signature")
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "sources": [
                        {
                            "id": "example",
                            "name": "Example",
                            "type": "rss",
                            "url": "https://source.example/feed.xml",
                            "priority": 50,
                            "language": "es",
                            "categories": [],
                        }
                    ],
                },
            )
        if request.url.path == "/v1/candidates":
            assert request.headers.get("x-newsforge-key-id") == "collector"
            body = json.loads(request.content.decode("utf-8"))
            ingested.update(body)
            return httpx.Response(
                200,
                json={"ok": True, "inserted": len(body["candidates"]), "duplicates": 0},
            )
        raise AssertionError(f"unexpected API request: {request.url}")

    def source_handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://source.example/feed.xml")
        xml = b"""<rss version='2.0'><channel><title>Example</title><item>
        <title>Headline</title><link>https://source.example/story</link>
        <description>Summary</description></item></channel></rss>"""
        return httpx.Response(
            200,
            content=xml,
            headers={"etag": "etag-123", "last-modified": "Sat, 31 Oct 2026 12:00:00 GMT"},
        )

    stats = collect_once(
        api_url="https://api.example.com",
        collector_secret="secret",
        api_transport=httpx.MockTransport(api_handler),
        source_transport=httpx.MockTransport(source_handler),
    )
    assert stats.pc_online is False
    assert stats.sources == 1
    assert stats.fetched == 1
    assert stats.candidates == 1
    assert stats.inserted == 1
    assert len(ingested["candidates"]) == 1
    assert ingested["source_states"][0]["etag"] == "etag-123"


def test_conditional_fetch_honors_304() -> None:
    calls = {"ingest": 0}

    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/status":
            return httpx.Response(200, json={"pc_online": False})
        if request.url.path == "/v1/collector-config":
            return httpx.Response(
                200,
                json={
                    "sources": [
                        {
                            "id": "example",
                            "name": "Example",
                            "type": "rss",
                            "url": "https://source.example/feed.xml",
                            "etag": "old-etag",
                            "last_modified": "yesterday",
                            "categories": [],
                        }
                    ]
                },
            )
        if request.url.path == "/v1/candidates":
            calls["ingest"] += 1
            body = json.loads(request.content.decode())
            assert body["candidates"] == []
            assert body["source_states"][0]["etag"] == "old-etag"
            return httpx.Response(200, json={"inserted": 0, "duplicates": 0})
        raise AssertionError(str(request.url))

    def source_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["if-none-match"] == "old-etag"
        assert request.headers["if-modified-since"] == "yesterday"
        return httpx.Response(304)

    stats = collect_once(
        api_url="https://api.example.com",
        collector_secret="secret",
        api_transport=httpx.MockTransport(api_handler),
        source_transport=httpx.MockTransport(source_handler),
    )
    assert stats.not_modified == 1
    assert stats.candidates == 0
    assert calls["ingest"] == 1


def test_cloud_api_failure_emits_syn_code(capsys) -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"code": "CFW-001", "message": "down"})

    import pytest

    with pytest.raises(httpx.HTTPStatusError):
        collect_once(
            api_url="https://api.example.com",
            collector_secret="secret",
            api_transport=httpx.MockTransport(api_handler),
        )
    output = capsys.readouterr().out
    assert '"code":"SYN-001"' in output
