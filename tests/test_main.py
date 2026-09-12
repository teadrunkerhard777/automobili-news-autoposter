import pytest

import main
from main import load_article_data


def test_one_html_request_uses_source_config_for_text_and_image(monkeypatch):
    calls = []
    html = """
    <article><p>Article body</p></article>
    <meta property='og:image' content='/photo.jpg'>
    """

    def fetch(url, source_config=None):
        calls.append((url, source_config))
        return html

    monkeypatch.setattr("main.fetch_article_html", fetch)
    source_config = {
        "name": "Example",
        "type": "html",
        "headers": {"User-Agent": "Browser UA"},
        "retries": 2,
    }
    item = {
        "title": "Story",
        "url": "https://example.test/story",
        "source": "Example",
    }

    load_article_data([item], sources=[source_config])

    assert calls == [("https://example.test/story", source_config)]
    assert item["article_text"] == "Article body"
    assert item["image_url"] == "https://example.test/photo.jpg"


def test_preloaded_article_data_skips_http(monkeypatch):
    monkeypatch.setattr("main.fetch_article_html", lambda url: pytest.fail("unexpected request"))
    item = {
        "url": "https://example.test/story",
        "article_text": "Already loaded",
        "image_url": None,
    }

    load_article_data([item])


def test_run_applies_diversity_after_event_dedup(monkeypatch):
    first = {"title": "First", "url": "https://example.test/first"}
    second = {"title": "Second", "url": "https://example.test/second"}
    ranked = [first, second]
    settings = {"enabled": True, "min_shared_tokens": 4}
    stages = []
    diversity_call = {}

    monkeypatch.setattr(main, "configure_ssl", lambda: None)
    monkeypatch.setattr(main, "collect_enabled_news", lambda: ranked)
    monkeypatch.setattr(main, "filter_by_date", lambda items, days: items)
    monkeypatch.setattr(main, "filter_relevant", lambda items, rule: items)
    monkeypatch.setattr(main, "add_scores", lambda items, scorer: None)
    monkeypatch.setattr(
        main,
        "filter_by_minimum_score",
        lambda items, minimum: items,
    )
    monkeypatch.setattr(main, "sort_by_score", lambda items: items)
    monkeypatch.setattr(main, "load_article_data", lambda items: None)

    def deduplicate(items, event_settings, debug=False):
        stages.append("dedup")
        return items

    def diversify(items, limit, diversity_settings):
        stages.append("diversity")
        diversity_call.update(
            items=items,
            limit=limit,
            settings=diversity_settings,
        )
        return [second]

    monkeypatch.setattr(main, "remove_duplicates", deduplicate)
    monkeypatch.setattr(main, "select_diverse", diversify)
    monkeypatch.setattr(main, "load_history", lambda: [])
    monkeypatch.setattr(main, "publish_selected_news", lambda *args: False)
    monkeypatch.setattr(main, "DRY_RUN", True)
    monkeypatch.setattr(main, "MAX_NEWS_PER_RUN", 2)
    monkeypatch.setattr(main, "DIVERSITY_SETTINGS", settings)

    selected = main.run()

    assert stages == ["dedup", "diversity"]
    assert diversity_call == {
        "items": ranked,
        "limit": 2,
        "settings": settings,
    }
    assert selected == [second]
