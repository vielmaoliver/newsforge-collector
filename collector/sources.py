from __future__ import annotations

import hashlib
import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import feedparser

from collector.models import CandidatePayload, RemoteSource

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def canonicalize_feed_url(url: str) -> str:
    split = urlsplit(url)
    if split.hostname == "news.un.org" and split.path.startswith("/feed/view/"):
        path = split.path.removeprefix("/feed/view")
        return urlunsplit((split.scheme, split.netloc, path, split.query, ""))
    return url


def clean_text(value: str, *, max_length: int = 4000) -> str:
    text = html.unescape(_TAG_RE.sub(" ", value or ""))
    text = _WS_RE.sub(" ", text).strip()
    return text[:max_length]


def candidate_hash(source_id: str, canonical_url: str) -> str:
    return hashlib.sha256(f"{source_id}|{canonical_url}".encode()).hexdigest()


def _feed_datetime(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(parsed.tm_year, parsed.tm_mon, parsed.tm_mday, parsed.tm_hour, parsed.tm_min, parsed.tm_sec, tzinfo=UTC)
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                value = parsedate_to_datetime(str(raw))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=UTC)
                return value.astimezone(UTC)
            except (TypeError, ValueError):
                continue
    return None


def parse_feed(content: bytes, source: RemoteSource, *, discovered_at: datetime | None = None) -> list[CandidatePayload]:
    discovered = discovered_at or datetime.now(UTC)
    feed = feedparser.parse(content)
    results: list[CandidatePayload] = []
    for raw in feed.entries:
        entry = dict(raw)
        title = clean_text(str(entry.get("title") or ""), max_length=600)
        url = str(entry.get("link") or "").strip()
        if not title or not url.startswith(("https://", "http://")):
            continue
        snippet = clean_text(str(entry.get("summary") or entry.get("description") or ""))
        canonical_url = canonicalize_feed_url(url)
        results.append(
            CandidatePayload.model_validate(
                {
                    "candidate_hash": candidate_hash(source.id, canonical_url),
                    "source_id": source.id,
                    "url": url,
                    "canonical_url": canonical_url,
                    "title": title,
                    "snippet": snippet,
                    "published_at": _feed_datetime(entry),
                    "discovered_at": discovered,
                }
            )
        )
    return results


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def parse_news_sitemap(content: bytes, source: RemoteSource, *, discovered_at: datetime | None = None) -> list[CandidatePayload]:
    discovered = discovered_at or datetime.now(UTC)
    root = ET.fromstring(content)
    ns = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
    }
    results: list[CandidatePayload] = []
    for node in root.findall("sm:url", ns):
        loc = (node.findtext("sm:loc", default="", namespaces=ns) or "").strip()
        title = clean_text(node.findtext("news:news/news:title", default="", namespaces=ns), max_length=600)
        published = node.findtext("news:news/news:publication_date", default="", namespaces=ns)
        if not loc.startswith(("https://", "http://")) or not title:
            continue
        results.append(
            CandidatePayload.model_validate(
                {
                    "candidate_hash": candidate_hash(source.id, loc),
                    "source_id": source.id,
                    "url": loc,
                    "canonical_url": loc,
                    "title": title,
                    "snippet": "",
                    "published_at": _parse_iso_datetime(published),
                    "discovered_at": discovered,
                }
            )
        )
    return results


def fetch_timestamp() -> int:
    return int(time.time())
