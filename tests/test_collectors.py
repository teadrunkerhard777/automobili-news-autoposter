from types import SimpleNamespace

import requests

from collectors.html_collector import (
    DEFAULT_RETRIES,
    REQUEST_HEADERS,
    RETRY_DELAY_SECONDS,
    collect_html,
)
from collectors.rss_collector import collect_rss


class Response:
    default_content = b"""
    <article class='card'>
      <h2><a href='/story'>Story title</a></h2>
      <time datetime='Wed, 01 Jan 2026 10:00:00 +0000'></time>
      <p class='summary'>Useful <b>summary</b></p>
    </article>
    """

    def __init__(self, content=None):
        self.content = self.default_content if content is None else content

    def raise_for_status(self):
        return None


def html_source(**overrides):
    source = {
        "name": "HTML Example",
        "url": "https://example.test/news",
        "base_url": "https://example.test",
        "item_selector": "article.card",
        "title_selector": "h2 a",
        "link_selector": "h2 a",
        "date_selector": "time",
        "description_selector": ".summary",
    }
    source.update(overrides)
    return source


def linked_html_source(**overrides):
    source = html_source(
        item_selector="a.card",
        title_selector=".title",
        link_from_item=True,
    )
    source.pop("link_selector")
    source.update(overrides)
    return source


def test_declarative_html_collector_builds_shared_contract(monkeypatch):
    monkeypatch.setattr(
        "collectors.html_collector.requests.get",
        lambda *args, **kwargs: Response(),
    )

    items = collect_html(html_source())

    assert items[0]["title"] == "Story title"
    assert items[0]["url"] == "https://example.test/story"
    assert items[0]["description"] == "Useful summary"
    assert items[0]["published_at"].tzinfo is not None


def test_html_collector_uses_linked_item_as_link(monkeypatch):
    response = Response(
        b"""
        <a class='card' href='/news/example'>
          <div class='title'>Linked card title</div>
          <time datetime='Wed, 01 Jan 2026 10:00:00 +0000'></time>
        </a>
        """
    )
    monkeypatch.setattr(
        "collectors.html_collector.requests.get",
        lambda *args, **kwargs: response,
    )

    items = collect_html(linked_html_source())

    assert items[0]["title"] == "Linked card title"
    assert items[0]["url"] == "https://example.test/news/example"


def test_linked_item_href_uses_configured_base_url(monkeypatch):
    response = Response(
        b"""
        <a class='card' href='story'>
          <div class='title'>Relative linked card</div>
        </a>
        """
    )
    monkeypatch.setattr(
        "collectors.html_collector.requests.get",
        lambda *args, **kwargs: response,
    )
    source = linked_html_source(base_url="https://example.test/section/")

    items = collect_html(source)

    assert items[0]["url"] == "https://example.test/section/story"


def test_linked_item_without_href_is_skipped(monkeypatch):
    response = Response(
        b"""
        <a class='card'>
          <div class='title'>Card without href</div>
        </a>
        """
    )
    monkeypatch.setattr(
        "collectors.html_collector.requests.get",
        lambda *args, **kwargs: response,
    )

    assert collect_html(linked_html_source()) == []


def test_html_collector_uses_default_headers(monkeypatch):
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr("collectors.html_collector.requests.get", get)

    collect_html(html_source())

    assert calls[0]["headers"] == REQUEST_HEADERS


def test_html_collector_merges_source_headers(monkeypatch):
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr("collectors.html_collector.requests.get", get)
    source = html_source(headers={"Accept-Language": "ru-RU"})

    collect_html(source)

    assert calls[0]["headers"] == {
        **REQUEST_HEADERS,
        "Accept-Language": "ru-RU",
    }


def test_source_headers_override_default_values(monkeypatch):
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr("collectors.html_collector.requests.get", get)
    source = html_source(headers={"User-Agent": "Browser UA"})

    collect_html(source)

    assert calls[0]["headers"]["User-Agent"] == "Browser UA"
    assert REQUEST_HEADERS["User-Agent"] != "Browser UA"


def test_html_collector_succeeds_after_temporary_request_error(monkeypatch):
    attempts = []
    sleeps = []

    def get(*args, **kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise requests.exceptions.SSLError("temporary")
        return Response()

    monkeypatch.setattr("collectors.html_collector.requests.get", get)
    monkeypatch.setattr("collectors.html_collector.time.sleep", sleeps.append)

    items = collect_html(html_source(retries=1))

    assert items[0]["title"] == "Story title"
    assert len(attempts) == 2
    assert sleeps == [RETRY_DELAY_SECONDS]


def test_html_collector_returns_empty_after_retries(monkeypatch):
    attempts = []
    sleeps = []

    def get(*args, **kwargs):
        attempts.append(kwargs)
        raise requests.exceptions.ConnectionError("temporary")

    monkeypatch.setattr("collectors.html_collector.requests.get", get)
    monkeypatch.setattr("collectors.html_collector.time.sleep", sleeps.append)

    items = collect_html(html_source())

    assert items == []
    assert len(attempts) == DEFAULT_RETRIES + 1
    assert sleeps == [RETRY_DELAY_SECONDS] * DEFAULT_RETRIES


def test_rss_collector_respects_source_limit(monkeypatch):
    entries = [
        {
            "title": f"Story {number}",
            "link": f"https://example.test/{number}",
            "published": "Wed, 01 Jan 2026 10:00:00 +0000",
            "summary": "Summary",
        }
        for number in range(5)
    ]
    feed = SimpleNamespace(bozo=False, entries=entries)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: feed,
    )

    items = collect_rss({
        "name": "RSS Example",
        "url": "https://example.test/rss",
        "limit": 2,
    })

    assert [item["title"] for item in items] == ["Story 0", "Story 1"]
