import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 15
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 AutoposterTemplate/1.0"}
DEFAULT_RETRIES = 3
RETRY_DELAY_SECONDS = 0.5
SERVICE_PREFIXES = (
    "photo:", "video:", "read also", "advertisement", "sponsored",
)


def fetch_article_html(url, source_config=None):
    """Fetch one article page with finite timeout and HTTP validation."""

    config = source_config or {}
    headers = {**REQUEST_HEADERS, **(config.get("headers") or {})}
    retries = (
        max(0, int(config.get("retries", DEFAULT_RETRIES)))
        if source_config is not None
        else 0
    )

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            if attempt == retries:
                raise

            # Give repeated transient failures progressively more recovery time.
            time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))


def extract_article_text(html, source=None, source_extractors=None):
    """Use a source-specific extractor or the conservative generic body."""

    soup = BeautifulSoup(html, "html.parser")
    extractor = (source_extractors or {}).get(source)

    if extractor is not None:
        return extractor(soup)

    body = soup.select_one("article") or soup.select_one("main") or soup
    paragraphs = [
        " ".join(node.get_text(" ", strip=True).split())
        for node in body.find_all("p")
    ]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def clean_article_text(text, source=None, source_stop_markers=None):
    """Remove generic service paragraphs and isolated source footers."""

    stop_markers = tuple(
        marker.casefold()
        for marker in (source_stop_markers or {}).get(source, ())
    )
    cleaned = []

    for raw_paragraph in (text or "").splitlines():
        paragraph = " ".join(raw_paragraph.split())

        if not paragraph:
            continue

        normalized = paragraph.casefold()

        if stop_markers and normalized.startswith(stop_markers):
            break

        if normalized.startswith(SERVICE_PREFIXES):
            continue

        cleaned.append(paragraph)

    return "\n\n".join(cleaned)


def extract_article_image_url(html, page_url):
    """Return og:image, then twitter:image, without downloading it."""

    soup = BeautifulSoup(html, "html.parser")
    selectors = (
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
    )

    for selector, attribute in selectors:
        node = soup.select_one(selector)
        value = node.get(attribute, "").strip() if node else ""

        if value:
            return urljoin(page_url, value)

    return None
