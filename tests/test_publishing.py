from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from main import publish_selected_news
from publishing.telegram import (
    IMAGE_DOWNLOAD_USER_AGENT,
    MAX_IMAGE_SIZE_BYTES,
    ImageDownloadError,
    TelegramSendResult,
    TemporaryImage,
    download_image_temp,
    send_telegram_photo,
)


def news(image_url=None):
    return {
        "title": "Python release",
        "url": "https://example.test/story",
        "source": "Example",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "description": "Python software release",
        "article_text": "Python software release body",
        "image_url": image_url,
        "matched_topics": ["python"],
        "event_category": "python",
    }


def fail_if_called(*args, **kwargs):
    raise AssertionError("external function must not be called")


def test_dry_run_never_publishes_or_changes_history():
    history = []
    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        history,
        True,
        "single",
        send_post=fail_if_called,
        send_photo=fail_if_called,
        download_image=fail_if_called,
        add_history=fail_if_called,
    )

    assert changed is False
    assert history == []


def test_history_changes_once_after_confirmed_text_success():
    history = []
    additions = []

    def add(item, target, settings):
        additions.append(item["url"])
        target.append({"url": item["url"]})

    changed = publish_selected_news(
        [news()],
        history,
        False,
        "single",
        send_post=lambda text: TelegramSendResult(True),
        add_history=add,
    )

    assert changed is True
    assert additions == ["https://example.test/story"]
    assert len(history) == 1


def test_successful_remote_photo_does_not_call_text_fallback():
    history = []
    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        history,
        False,
        "single",
        send_post=fail_if_called,
        send_photo=lambda *args, **kwargs: TelegramSendResult(True),
    )

    assert changed is True
    assert len(history) == 1


def test_confirmed_remote_fetch_error_uses_temporary_file(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(b"image")
    calls = []
    downloads = []
    source_config = {
        "name": "Example",
        "headers": {"User-Agent": "Source Browser"},
        "retries": 2,
    }

    def send_photo(photo, caption, **kwargs):
        calls.append(type(photo).__name__)

        if isinstance(photo, str):
            return TelegramSendResult(
                False,
                "failed to get HTTP URL content",
                remote_fetch_failed=True,
            )

        return TelegramSendResult(True)

    def download_image(url, source_config=None):
        downloads.append((url, source_config))
        return TemporaryImage(image_path, "image/jpeg", 5)

    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        [],
        False,
        "single",
        send_post=fail_if_called,
        send_photo=send_photo,
        download_image=download_image,
        sources=[source_config],
    )

    assert changed is True
    assert calls == ["str", "BufferedReader"]
    assert downloads == [("https://img.test/photo.jpg", source_config)]
    assert image_path.exists() is False


class ImageResponse:
    def __init__(self, content_type="image/jpeg", chunks=None, size=None):
        self.headers = {"Content-Type": content_type}
        if size is not None:
            self.headers["Content-Length"] = str(size)
        self.chunks = [b"image"] if chunks is None else chunks
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        return iter(self.chunks)

    def close(self):
        self.closed = True


def test_image_download_uses_source_headers(monkeypatch):
    response = ImageResponse()
    request = {}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return response

    monkeypatch.setattr("publishing.telegram.requests.get", get)
    result = download_image_temp(
        "https://img.test/photo.jpg",
        source_config={
            "headers": {
                "User-Agent": "Source Browser",
                "Referer": "https://example.test/",
            },
            "retries": 0,
        },
    )

    try:
        assert request["headers"] == {
            "User-Agent": "Source Browser",
            "Referer": "https://example.test/",
        }
        assert request["stream"] is True
        assert response.closed is True
    finally:
        result.path.unlink()


def test_image_download_retries_temporary_ssl_error(monkeypatch):
    response = ImageResponse()
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs["headers"])
        if len(calls) == 1:
            raise requests.exceptions.SSLError("temporary")
        return response

    monkeypatch.setattr("publishing.telegram.requests.get", get)
    monkeypatch.setattr("publishing.telegram.time.sleep", lambda delay: None)
    result = download_image_temp(
        "https://img.test/photo.jpg",
        source_config={"retries": 1},
    )

    try:
        assert len(calls) == 2
        assert calls[0]["User-Agent"] == IMAGE_DOWNLOAD_USER_AGENT
    finally:
        result.path.unlink()


def test_image_download_raises_after_retries_are_exhausted(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise requests.ConnectionError("temporary")

    monkeypatch.setattr("publishing.telegram.requests.get", fail)
    monkeypatch.setattr("publishing.telegram.time.sleep", lambda delay: None)

    with pytest.raises(ImageDownloadError, match="ConnectionError"):
        download_image_temp(
            "https://img.test/photo.jpg",
            source_config={"retries": 2},
        )

    assert len(calls) == 3


def test_image_download_rejects_non_image_content_type(monkeypatch):
    response = ImageResponse(content_type="text/html")
    monkeypatch.setattr(
        "publishing.telegram.requests.get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(ImageDownloadError, match="invalid Content-Type"):
        download_image_temp("https://img.test/photo.jpg")

    assert response.closed is True


def test_image_download_rejects_declared_oversized_file(monkeypatch):
    response = ImageResponse(size=MAX_IMAGE_SIZE_BYTES + 1)
    monkeypatch.setattr(
        "publishing.telegram.requests.get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(ImageDownloadError, match="exceeds 10 MiB"):
        download_image_temp("https://img.test/photo.jpg")

    assert response.closed is True


def test_read_timeout_result_does_not_retry_or_fallback():
    history = []
    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        history,
        False,
        "single",
        send_post=fail_if_called,
        send_photo=lambda *args, **kwargs: TelegramSendResult(
            False, "ReadTimeout", uncertain=True
        ),
        download_image=fail_if_called,
    )

    assert changed is False
    assert history == []


def test_sender_marks_real_read_timeout_uncertain_without_retry(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise requests.ReadTimeout

    monkeypatch.setattr("publishing.telegram.requests.post", timeout)
    result = send_telegram_photo(
        "https://img.test/photo.jpg",
        "caption",
    )

    assert result.uncertain is True
    assert len(calls) == 1
