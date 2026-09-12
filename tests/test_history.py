from datetime import datetime, timezone

from storage.history import add_to_history, is_published, load_history, save_history


def news(url="https://example.test/story"):
    return {
        "title": "Python package release",
        "url": url,
        "source": "Example",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "description": "package release testing runner plugin benchmark community",
        "event_category": "python",
    }


def test_empty_history_round_trip(tmp_path):
    path = tmp_path / "published.json"
    save_history([], path)
    assert load_history(path) == []


def test_new_history_entry_contains_compact_fingerprint():
    history = []
    add_to_history(news(), history)

    assert history[0]["event_fingerprint"]["categories"] == ["python"]
    assert "article_text" not in history[0]


def test_legacy_history_without_fingerprint_remains_url_compatible():
    item = news()
    assert is_published(item, [{"url": item["url"]}]) is True
    assert is_published(item, [{"url": "https://other.test"}]) is False

