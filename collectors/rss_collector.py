import feedparser

from collectors.normalizer import normalize_item


def collect_rss(source):
    """Collect one RSS feed into the shared news_item format."""

    feed = feedparser.parse(source["url"])

    if feed.bozo:
        print(f"RSS warning ({source['name']}): {feed.bozo_exception}")

    items = [
        normalize_item(
            {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published_at": entry.get("published", ""),
                "description": entry.get("summary", ""),
            },
            source["name"],
        )
        for entry in feed.entries
    ]

    limit = max(0, int(source.get("limit", 40)))
    return items[:limit]
