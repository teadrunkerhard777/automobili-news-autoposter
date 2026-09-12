from datetime import datetime, timedelta, timezone

from processing.deduplicator import (
    compare_event_fingerprints,
    remove_duplicates,
)
from project.settings import EVENT_DEDUP_SETTINGS


NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


def make_item(source, title, body, category="release", hours=0, url=None):
    return {
        "source": source,
        "title": title,
        "url": url or f"https://{source}.test/{hours}",
        "published_at": NOW + timedelta(hours=hours),
        "article_text": body,
        "event_category": category,
        "event_locations": [],
        "score": 3,
    }


def test_regular_url_and_title_deduplication():
    first = make_item("a", "Python project ships version 4", "one", url="https://same")
    same_url = make_item("b", "Different title", "two", url="https://same")
    same_title = make_item("c", "Python project ships version 4", "three")

    assert remove_duplicates([first, same_url, same_title]) == [first]


def test_cross_source_event_duplicate_is_merged():
    facts = "python maintainers release faster runner plugin benchmark community package"
    first = make_item("a", "New Python runner released", facts)
    second = make_item("b", "Community ships runner update", facts, hours=2)

    details = compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)

    assert details["is_duplicate"] is True
    assert len(remove_duplicates([first, second], EVENT_DEDUP_SETTINGS)) == 1


def test_close_but_different_events_are_not_merged():
    first = make_item(
        "a", "Python formatter update", "formatter syntax output terminal colors"
    )
    second = make_item(
        "b", "Python database update", "database index storage query optimizer", hours=2
    )

    assert compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)["is_duplicate"] is False


def test_different_categories_are_not_merged_even_with_same_text():
    body = "shared detailed tokens alpha beta gamma delta epsilon zeta"
    first = make_item("a", "Tool release", body, category="release")
    second = make_item("b", "Tool advisory", body, category="security", hours=1)

    assert compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)["is_duplicate"] is False


def test_optional_location_can_support_event_match():
    body = "maintainers publish package benchmark runner plugin"
    first = make_item("a", "Tool update", body)
    second = make_item("b", "Package update", body, hours=1)
    first["event_locations"] = ["Berlin"]
    second["event_locations"] = ["Berlin"]

    assert compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)["is_duplicate"] is True

