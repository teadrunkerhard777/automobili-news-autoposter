import json
from pathlib import Path

from processing.deduplicator import (
    build_event_fingerprint,
    compare_event_fingerprints,
)


HISTORY_FILE = Path("storage/published.json")


def load_history(path=HISTORY_FILE):
    path = Path(path)

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history, path=HISTORY_FILE):
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)


def is_published(news_item, history, event_settings=None):
    for entry in history:
        if entry.get("url") == news_item.get("url"):
            return True

        # Legacy entries without fingerprints remain URL-only.
        if not isinstance(entry.get("event_fingerprint"), dict):
            continue

        if compare_event_fingerprints(news_item, entry, event_settings)["is_duplicate"]:
            return True

    return False


def add_to_history(news_item, history, event_settings=None):
    published_at = news_item.get("published_at")
    history.append({
        "title": news_item.get("title", ""),
        "url": news_item.get("url", ""),
        "published_at": published_at.isoformat() if published_at else None,
        "source": news_item.get("source"),
        "event_fingerprint": build_event_fingerprint(news_item, event_settings),
    })
    return history

