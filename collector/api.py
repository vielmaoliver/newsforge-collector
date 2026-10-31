from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class ApiResponse:
    status_code: int
    payload: dict[str, Any]


class CloudApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        collector_secret: str,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.collector_secret = collector_secret
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
            headers={"User-Agent": "NewsForgeCollector/0.1"},
        )

    def close(self) -> None:
        self.client.close()

    @staticmethod
    def _body_hash(body: str) -> str:
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @classmethod
    def build_signature(
        cls,
        *,
        secret: str,
        method: str,
        path_and_query: str,
        timestamp: str,
        nonce: str,
        body: str,
    ) -> str:
        canonical = "\n".join(
            [
                method.upper(),
                path_and_query,
                timestamp,
                nonce,
                cls._body_hash(body),
            ]
        )
        return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def _signed_headers(self, method: str, path_and_query: str, body: str) -> dict[str, str]:
        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(18)
        signature = self.build_signature(
            secret=self.collector_secret,
            method=method,
            path_and_query=path_and_query,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
        )
        return {
            "content-type": "application/json",
            "x-newsforge-key-id": "collector",
            "x-newsforge-timestamp": timestamp,
            "x-newsforge-nonce": nonce,
            "x-newsforge-signature": signature,
        }

    def public_status(self) -> ApiResponse:
        response = self.client.get(f"{self.base_url}/v1/status")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("status response must be an object")
        return ApiResponse(response.status_code, payload)

    def collector_config(self) -> ApiResponse:
        path = "/v1/collector-config"
        response = self.client.get(
            f"{self.base_url}{path}",
            headers=self._signed_headers("GET", path, ""),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("collector config response must be an object")
        return ApiResponse(response.status_code, payload)

    def ingest(self, payload: dict[str, Any]) -> ApiResponse:
        path = "/v1/candidates"
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        response = self.client.post(
            f"{self.base_url}{path}",
            content=body.encode("utf-8"),
            headers=self._signed_headers("POST", path, body),
        )
        response.raise_for_status()
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise TypeError("ingest response must be an object")
        return ApiResponse(response.status_code, parsed)
