from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class RemoteSource(BaseModel):
    id: str
    name: str
    type: str = "rss"
    url: HttpUrl
    priority: int = 50
    language: str = "es"
    country: str | None = None
    publisher_group: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    content_mode: str = Field(default="full", pattern=r"^(full|metadata_only)$")
    categories: list[str] = Field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    last_fetch: int | None = None


class CandidatePayload(BaseModel):
    candidate_hash: str
    source_id: str
    url: HttpUrl
    canonical_url: HttpUrl
    title: str
    snippet: str = ""
    published_at: datetime | None = None
    discovered_at: datetime


class SourceFetchState(BaseModel):
    source_id: str
    etag: str | None = None
    last_modified: str | None = None
    last_fetch: int
