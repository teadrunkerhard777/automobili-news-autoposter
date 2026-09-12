import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from collectors.normalizer import normalize_item


REQUEST_TIMEOUT = 15
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 AutoposterTemplate/1.0"}
DEFAULT_RETRIES = 3
RETRY_DELAY_SECONDS = 0.5


def collect_html(source):
    """Collect cards using declarative CSS selectors from source config."""

    headers = {**REQUEST_HEADERS, **(source.get("headers") or {})}
    retries = max(0, int(source.get("retries", DEFAULT_RETRIES)))

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                source["url"],
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            break
        except requests.RequestException as error:
            if attempt == retries:
                print(
                    f"HTML warning ({source['name']}): "
                    f"{type(error).__name__}"
                )
                return []

            # A short fixed delay is enough for transient collector failures.
            time.sleep(RETRY_DELAY_SECONDS)

    items = []

    for card in soup.select(source["item_selector"]):
        title_node = card.select_one(source["title_selector"])
        # Some card selectors point to the anchor instead of containing one.
        if source.get("link_from_item"):
            link_node = card
        else:
            link_node = card.select_one(source["link_selector"])

        if title_node is None or link_node is None:
            continue

        date_node = card.select_one(source.get("date_selector", "time"))
        description_node = card.select_one(
            source.get("description_selector", "p")
        )
        date_value = None

        if date_node is not None:
            date_value = date_node.get("datetime") or date_node.get_text(
                " ", strip=True
            )

        href = link_node.get("href", "")
        if source.get("link_from_item") and not href:
            continue

        item = normalize_item(
            {
                "title": title_node.get_text(" ", strip=True),
                "url": urljoin(source.get("base_url", source["url"]), href),
                "published_at": date_value,
                "description": (
                    description_node.get_text(" ", strip=True)
                    if description_node is not None
                    else ""
                ),
            },
            source["name"],
        )

        if item["title"] and item["url"]:
            items.append(item)

    limit = max(0, int(source.get("limit", 40)))
    return items[:limit]
