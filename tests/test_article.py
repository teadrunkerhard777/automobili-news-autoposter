import pytest
import requests

from article.fetcher import (
    REQUEST_HEADERS,
    RETRY_DELAY_SECONDS,
    clean_article_text,
    extract_article_image_url,
    extract_article_text,
    fetch_article_html,
)


class ArticleResponse:
    text = "<article><p>Fetched body</p></article>"

    def raise_for_status(self):
        return None


def test_fetch_article_html_old_call_uses_default_headers(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return ArticleResponse()

    monkeypatch.setattr("article.fetcher.requests.get", get)

    html = fetch_article_html("https://example.test/story")

    assert html == ArticleResponse.text
    assert len(calls) == 1
    assert calls[0][1]["headers"] == REQUEST_HEADERS


def test_fetch_article_html_merges_source_headers(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return ArticleResponse()

    monkeypatch.setattr("article.fetcher.requests.get", get)
    source_config = {
        "headers": {
            "User-Agent": "Browser UA",
            "Accept-Language": "ru-RU",
        },
        "retries": 0,
    }

    fetch_article_html("https://example.test/story", source_config)

    assert calls[0][1]["headers"] == {
        **REQUEST_HEADERS,
        "User-Agent": "Browser UA",
        "Accept-Language": "ru-RU",
    }


def test_fetch_article_html_retries_temporary_ssl_error(monkeypatch):
    attempts = []
    sleeps = []

    def get(url, **kwargs):
        attempts.append((url, kwargs))
        if len(attempts) == 1:
            raise requests.exceptions.SSLError("temporary")
        return ArticleResponse()

    monkeypatch.setattr("article.fetcher.requests.get", get)
    monkeypatch.setattr("article.fetcher.time.sleep", sleeps.append)

    html = fetch_article_html(
        "https://example.test/story",
        {"retries": 1},
    )

    assert html == ArticleResponse.text
    assert len(attempts) == 2
    assert sleeps == [RETRY_DELAY_SECONDS]


def test_fetch_article_html_uses_backoff_for_multiple_ssl_errors(monkeypatch):
    attempts = []
    sleeps = []
    source_config = {
        "headers": {
            "User-Agent": "Browser UA",
            "Accept-Language": "ru-RU",
        },
        "retries": 3,
    }

    def get(url, **kwargs):
        attempts.append((url, kwargs))
        if len(attempts) < 4:
            raise requests.exceptions.SSLError("temporary")
        return ArticleResponse()

    monkeypatch.setattr("article.fetcher.requests.get", get)
    monkeypatch.setattr("article.fetcher.time.sleep", sleeps.append)

    html = fetch_article_html(
        "https://example.test/story",
        source_config,
    )

    assert html == ArticleResponse.text
    assert len(attempts) == 4
    assert sleeps == [
        RETRY_DELAY_SECONDS,
        RETRY_DELAY_SECONDS * 2,
        RETRY_DELAY_SECONDS * 3,
    ]
    assert all(
        kwargs["headers"] == {
            **REQUEST_HEADERS,
            **source_config["headers"],
        }
        for _, kwargs in attempts
    )


def test_fetch_article_html_raises_last_error_after_retries(monkeypatch):
    attempts = []
    sleeps = []

    def get(url, **kwargs):
        attempts.append((url, kwargs))
        raise requests.exceptions.SSLError(f"attempt {len(attempts)}")

    monkeypatch.setattr("article.fetcher.requests.get", get)
    monkeypatch.setattr("article.fetcher.time.sleep", sleeps.append)

    with pytest.raises(requests.exceptions.SSLError, match="attempt 3"):
        fetch_article_html(
            "https://example.test/story",
            {"retries": 2},
        )

    assert len(attempts) == 3
    assert sleeps == [RETRY_DELAY_SECONDS, RETRY_DELAY_SECONDS * 2]


def test_fetch_article_html_old_call_does_not_retry(monkeypatch):
    attempts = []

    def get(url, **kwargs):
        attempts.append((url, kwargs))
        raise requests.exceptions.ConnectionError("failed")

    monkeypatch.setattr("article.fetcher.requests.get", get)

    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_article_html("https://example.test/story")

    assert len(attempts) == 1


def test_generic_article_extraction_prefers_article_container():
    html = """
    <p>Navigation paragraph</p>
    <article><p>Useful first paragraph.</p><p>Useful second paragraph.</p></article>
    <footer><p>Footer paragraph</p></footer>
    """

    text = extract_article_text(html)

    assert "Useful first" in text
    assert "Navigation" not in text
    assert "Footer" not in text


def test_source_specific_extractor_is_isolated():
    html = "<article><p>Generic body</p></article><div class='special'>Special body</div>"

    def special(soup):
        return soup.select_one(".special").get_text(strip=True)

    registry = {"Special Source": special}

    assert extract_article_text(html, "Special Source", registry) == "Special body"
    assert extract_article_text(html, "Other Source", registry) == "Generic body"


def test_source_stop_marker_does_not_affect_other_sources():
    text = "Useful paragraph\n\nNewsletter signup\n\nFooter"
    markers = {"Special Source": ("newsletter signup",)}

    assert clean_article_text(text, "Special Source", markers) == "Useful paragraph"
    assert "Footer" in clean_article_text(text, "Other Source", markers)


def test_image_metadata_prefers_open_graph_and_resolves_relative_url():
    html = """
    <meta property='og:image' content='/images/main.jpg'>
    <meta name='twitter:image' content='https://cdn.test/twitter.jpg'>
    """

    assert extract_article_image_url(html, "https://news.test/story") == "https://news.test/images/main.jpg"


def test_image_metadata_falls_back_to_twitter():
    html = "<meta name='twitter:image' content='https://cdn.test/image.jpg'>"
    assert extract_article_image_url(html, "https://news.test") == "https://cdn.test/image.jpg"
