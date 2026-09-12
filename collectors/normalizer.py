import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape


def normalize_date(value):
    """Return a timezone-aware datetime when the source date is reliable."""

    if isinstance(value, datetime):
        return value

    if not value:
        return None

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        pass

    # ISO sources commonly use Z instead of the explicit UTC offset.
    try:
        iso_value = value.strip()
        if iso_value.endswith("Z"):
            iso_value = f"{iso_value[:-1]}+00:00"
        parsed = datetime.fromisoformat(iso_value)
    except (AttributeError, TypeError, ValueError):
        return None

    return parsed if parsed.tzinfo is not None else None


def clean_description(description):
    """Remove simple RSS HTML and normalize whitespace."""

    if not description:
        return ""

    cleaned = re.sub(r"<[^>]+>", " ", unescape(description))
    return " ".join(cleaned.split())


def normalize_item(item, source_name):
    """Build the shared news_item contract."""

    return {
        "title": " ".join(str(item.get("title", "")).split()),
        "url": str(item.get("url", "")).strip(),
        "published_at": normalize_date(item.get("published_at")),
        "description": clean_description(item.get("description", "")),
        "source": source_name,
        **{
            key: item[key]
            for key in ("article_text", "image_url")
            if key in item
        },
    }
