from __future__ import annotations

from datetime import UTC, datetime

from collector.models import RemoteSource
from collector.sources import candidate_hash, clean_text, parse_feed, parse_news_sitemap


def test_feed_parsing_produces_metadata_only_candidate() -> None:
    source = RemoteSource(id="example", name="Example", url="https://example.com/feed.xml")
    xml = b"""<?xml version='1.0'?>
    <rss version='2.0'><channel><title>Example</title><item>
      <title>Headline</title><link>https://example.com/a</link>
      <description><![CDATA[<p>Short <b>summary</b></p>]]></description>
      <pubDate>Sat, 31 Oct 2026 12:00:00 GMT</pubDate>
    </item></channel></rss>"""
    items = parse_feed(xml, source, discovered_at=datetime(2026, 10, 31, tzinfo=UTC))
    assert len(items) == 1
    item = items[0]
    assert str(item.url) == "https://example.com/a"
    assert item.title == "Headline"
    assert item.snippet == "Short summary"
    assert item.candidate_hash == candidate_hash("example", "https://example.com/a")
    assert not hasattr(item, "content")


def test_news_sitemap_parsing() -> None:
    source = RemoteSource(
        id="sitemap",
        name="Sitemap",
        type="news_sitemap",
        url="https://example.com/news.xml",
    )
    xml = b"""<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'
            xmlns:news='http://www.google.com/schemas/sitemap-news/0.9'>
      <url><loc>https://example.com/story</loc><news:news>
        <news:publication_date>2026-10-31T13:00:00Z</news:publication_date>
        <news:title>Story title</news:title>
      </news:news></url>
    </urlset>"""
    items = parse_news_sitemap(xml, source)
    assert len(items) == 1
    assert items[0].title == "Story title"
    assert str(items[0].canonical_url) == "https://example.com/story"


def test_clean_text_removes_markup() -> None:
    assert clean_text("<p>Hello&nbsp; <b>world</b></p>") == "Hello world"



def test_news_un_feed_url_is_canonicalized_without_losing_original() -> None:
    source = RemoteSource(
        id="un-news-es",
        name="Noticias ONU Español",
        url="https://news.un.org/feed/subscribe/es/news/all/rss.xml",
    )
    xml = b"""<rss version='2.0'><channel><title>UN</title><item>
      <title>ONU test</title>
      <link>https://news.un.org/feed/view/es/story/2026/10/1542109</link>
      <description>Resumen</description>
    </item></channel></rss>"""
    item = parse_feed(xml, source)[0]
    assert str(item.url) == "https://news.un.org/feed/view/es/story/2026/10/1542109"
    assert str(item.canonical_url) == "https://news.un.org/es/story/2026/10/1542109"
    assert item.candidate_hash == candidate_hash(
        "un-news-es", "https://news.un.org/es/story/2026/10/1542109"
    )
