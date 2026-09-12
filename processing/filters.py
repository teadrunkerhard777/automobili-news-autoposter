from datetime import datetime, timedelta, timezone


def filter_by_date(news_items, lookback_days, now=None):
    """Keep timezone-aware items inside the configured lookback window."""

    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=lookback_days)
    fresh = []

    for item in news_items:
        published_at = item.get("published_at")

        if published_at is None:
            continue

        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        if published_at.astimezone(timezone.utc) >= cutoff:
            fresh.append(item)

    return fresh


def filter_relevant(news_items, is_relevant):
    """Apply project-owned relevance logic without knowing its theme."""

    return [item for item in news_items if is_relevant(item)]


def add_scores(news_items, calculate_score):
    """Attach project-owned scores to the same news_item dictionaries."""

    for item in news_items:
        item["score"] = calculate_score(item)

    return news_items


def filter_by_minimum_score(news_items, minimum_score):
    return [
        item for item in news_items
        if item.get("score", 0) >= minimum_score
    ]


def sort_by_score(news_items):
    """Stable descending ranking keeps collector order for score ties."""

    return sorted(
        news_items,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

