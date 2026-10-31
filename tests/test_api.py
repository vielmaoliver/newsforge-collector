from __future__ import annotations

from collector.api import CloudApiClient


def test_hmac_signature_matches_worker_contract() -> None:
    signature = CloudApiClient.build_signature(
        secret="secret",
        method="POST",
        path_and_query="/v1/candidates",
        timestamp="1700000000",
        nonce="abcdefghijklmnop",
        body='{"a":1}',
    )
    assert signature == "56c8496d55a676f544afa5668877ef15d2eb89c64e71d6224fc4610a3d1bf9e6"
