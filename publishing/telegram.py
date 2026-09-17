import os
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

TELEGRAM_MAX_ATTEMPTS = 2
TELEGRAM_RETRY_DELAY_SECONDS = 2
TELEGRAM_CONNECT_TIMEOUT_SECONDS = 10
TELEGRAM_READ_TIMEOUT_SECONDS = 30
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
IMAGE_DOWNLOAD_USER_AGENT = "Mozilla/5.0 AutoposterTemplate/1.0"
IMAGE_DOWNLOAD_DEFAULT_RETRIES = 3
IMAGE_DOWNLOAD_RETRY_DELAY_SECONDS = 0.5
REMOTE_IMAGE_FETCH_ERROR_MARKERS = (
    "failed to get http url content",
    "wrong type of the web page content",
)
IMAGE_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class TelegramSendResult:
    success: bool
    error_reason: str | None = None
    attempts: int = 0
    uncertain: bool = False
    remote_fetch_failed: bool = False

    def __bool__(self):
        return self.success


@dataclass(frozen=True)
class TemporaryImage:
    path: Path
    mime_type: str
    size_bytes: int


class ImageDownloadError(Exception):
    """Expected failure while preparing a Telegram-compatible image."""


def send_telegram_post(text):
    result = _send_telegram_request(
        "sendMessage",
        {"text": text, "parse_mode": "HTML"},
    )

    if not result:
        print(f"Telegram error: {result.error_reason}")

    return result


def send_telegram_photo(photo, caption, filename=None, mime_type=None):
    """Send a remote URL or an open binary file as one photo message."""

    if not photo:
        return TelegramSendResult(False, "image is missing")

    payload = {"caption": caption, "parse_mode": "HTML"}
    files = None
    image_url = photo if isinstance(photo, str) else None

    if image_url:
        payload["photo"] = image_url
    else:
        files = {
            "photo": (
                filename or "autoposter-photo.jpg",
                photo,
                mime_type or "application/octet-stream",
            )
        }

    result = _send_telegram_request("sendPhoto", payload, files=files)

    if image_url and _is_remote_image_fetch_error(result.error_reason):
        result = replace(result, remote_fetch_failed=True)

    if not result:
        print(f"Photo error: {result.error_reason}")

        if image_url:
            print(f"Image URL: {image_url}")

    return result


def download_image_temp(image_url, source_config=None):
    """Stream a validated image to the operating-system temp directory."""

    config = source_config or {}
    headers = {
        "User-Agent": IMAGE_DOWNLOAD_USER_AGENT,
        **(config.get("headers") or {}),
    }
    retries = (
        max(0, int(config.get("retries", IMAGE_DOWNLOAD_DEFAULT_RETRIES)))
        if source_config is not None
        else 0
    )

    for attempt in range(retries + 1):
        try:
            return _download_image_once(image_url, headers)
        except requests.RequestException as error:
            if attempt == retries:
                if isinstance(error, requests.HTTPError):
                    response = error.response
                    status = (
                        response.status_code
                        if response is not None
                        else "unknown"
                    )
                    raise ImageDownloadError(f"HTTP {status}") from error

                raise ImageDownloadError(type(error).__name__) from error

            # Use the same small fixed retry delay as source-aware fetchers.
            time.sleep(IMAGE_DOWNLOAD_RETRY_DELAY_SECONDS)


def _download_image_once(image_url, headers):
    response = None
    temp_path = None
    completed = False

    try:
        response = requests.get(
            image_url,
            headers=headers,
            timeout=(
                TELEGRAM_CONNECT_TIMEOUT_SECONDS,
                TELEGRAM_READ_TIMEOUT_SECONDS,
            ),
            stream=True,
        )
        response.raise_for_status()
        mime_type = response.headers.get("Content-Type", "")
        mime_type = mime_type.split(";", 1)[0].strip().casefold()

        if not mime_type.startswith("image/"):
            raise ImageDownloadError(
                f"invalid Content-Type: {mime_type or 'missing'}"
            )

        content_length = response.headers.get("Content-Length")

        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = 0

            if declared_size > MAX_IMAGE_SIZE_BYTES:
                raise ImageDownloadError("image exceeds 10 MiB")

        suffix = IMAGE_SUFFIXES.get(mime_type, ".img")

        with tempfile.NamedTemporaryFile(
            prefix="autoposter-photo-",
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            downloaded_size = 0

            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue

                downloaded_size += len(chunk)

                if downloaded_size > MAX_IMAGE_SIZE_BYTES:
                    raise ImageDownloadError("image exceeds 10 MiB")

                temp_file.write(chunk)

        if downloaded_size == 0:
            raise ImageDownloadError("server returned an empty image")

        result = TemporaryImage(temp_path, mime_type, downloaded_size)
        completed = True
        return result
    finally:
        if response is not None:
            response.close()

        if temp_path is not None and not completed and temp_path.exists():
            temp_path.unlink()


def _send_telegram_request(method, payload, files=None):
    """Retry only known pre-connection failures to prevent duplicates."""

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        return TelegramSendResult(
            False,
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing",
        )

    api_url = f"https://api.telegram.org/bot{bot_token}/{method}"
    request_payload = {"chat_id": chat_id, **payload}

    for attempt in range(1, TELEGRAM_MAX_ATTEMPTS + 1):
        try:
            if files:
                for file_data in files.values():
                    file_data[1].seek(0)

            arguments = {
                "timeout": (
                    TELEGRAM_CONNECT_TIMEOUT_SECONDS,
                    TELEGRAM_READ_TIMEOUT_SECONDS,
                )
            }

            if files:
                arguments["data"] = request_payload
                arguments["files"] = files
            else:
                arguments["json"] = request_payload

            response = requests.post(api_url, **arguments)
            response.raise_for_status()

        except requests.ConnectTimeout:
            # ConnectTimeout occurs before connection, so one retry is safe.
            if attempt < TELEGRAM_MAX_ATTEMPTS:
                time.sleep(TELEGRAM_RETRY_DELAY_SECONDS)
                continue

            return TelegramSendResult(
                False, "ConnectTimeout", attempts=attempt
            )
        except requests.ReadTimeout:
            # Telegram may already have accepted the message.
            return TelegramSendResult(
                False, "ReadTimeout", attempts=attempt, uncertain=True
            )
        except requests.ConnectionError as error:
            return TelegramSendResult(
                False,
                type(error).__name__,
                attempts=attempt,
                uncertain=True,
            )
        except requests.HTTPError as error:
            status = error.response.status_code if error.response else "unknown"
            description = _read_api_error_description(error.response)
            reason = f"HTTP {status}"

            if description:
                reason = f"{reason}: {description}"

            return TelegramSendResult(False, reason, attempts=attempt)
        except requests.RequestException as error:
            return TelegramSendResult(
                False, type(error).__name__, attempts=attempt
            )

        break

    try:
        data = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return TelegramSendResult(False, "invalid JSON", attempts=attempt)

    if not isinstance(data, dict) or data.get("ok") is not True:
        description = data.get("description", "unexpected response") if isinstance(data, dict) else "unexpected response"
        return TelegramSendResult(
            False,
            f"Telegram API: {description}",
            attempts=attempt,
        )

    return TelegramSendResult(True, attempts=attempt)


def _read_api_error_description(response):
    if response is None:
        return None

    try:
        data = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return None

    description = data.get("description") if isinstance(data, dict) else None
    return description.strip()[:300] if isinstance(description, str) else None


def _is_remote_image_fetch_error(reason):
    normalized = (reason or "").casefold()
    return any(marker in normalized for marker in REMOTE_IMAGE_FETCH_ERROR_MARKERS)
