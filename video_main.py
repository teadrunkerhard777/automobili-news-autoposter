"""Collect and publish one positive licensed automotive stock video."""

import html
import os
from datetime import datetime, timezone

from collectors.pexels_video_collector import PexelsVideoError, collect_pexels_videos
from collectors.pixabay_video_collector import PixabayVideoError, collect_pixabay_videos
from config import DRY_RUN
from core.environment import configure_ssl
from core.run_lock import AlreadyRunningError, single_instance_lock
from project.video_settings import (
    VIDEO_CAPTIONS,
    VIDEO_MAX_DURATION_SECONDS,
    VIDEO_MAX_SIZE_BYTES,
    VIDEO_ORIENTATION,
    VIDEO_RESULTS_PER_RUN,
    VIDEO_SEARCH_QUERIES,
    VIDEO_SOURCES,
    VIDEO_TIMEZONE,
)
from publishing.telegram import VideoDownloadError, download_video_temp, send_telegram_video
from storage.history import load_history, save_history


def choose_search_query(now=None):
    current = now or datetime.now(timezone.utc)
    local = current.astimezone(VIDEO_TIMEZONE)
    slot = 0 if local.hour < 17 else 1
    index = (local.date().toordinal() * 2 + slot) % len(VIDEO_SEARCH_QUERIES)
    return VIDEO_SEARCH_QUERIES[index]


def choose_source_order(now=None):
    current = now or datetime.now(timezone.utc)
    local = current.astimezone(VIDEO_TIMEZONE)
    slot = 0 if local.hour < 17 else 1
    preferred = (local.date().toordinal() * 2 + slot) % len(VIDEO_SOURCES)
    return VIDEO_SOURCES[preferred:] + VIDEO_SOURCES[:preferred]


def format_video_caption(item):
    media_id = str(item.get("media_id") or "0")
    caption = VIDEO_CAPTIONS[sum(media_id.encode("utf-8")) % len(VIDEO_CAPTIONS)]
    page_url = html.escape(str(item["url"]), quote=True)
    source = html.escape(str(item.get("source_label") or item["source"]))
    return f'{caption}\n\n<a href="{page_url}">{source}</a>'


def select_unpublished_video(candidates, history):
    published_urls = {
        _normalize_media_url(entry.get("url")) for entry in history
        if _normalize_media_url(entry.get("url"))
    }
    return next((
        item for item in candidates
        if _normalize_media_url(item.get("url")) not in published_urls
    ), None)


def _normalize_media_url(value):
    return str(value or "").strip().rstrip("/").casefold()


def add_video_to_history(item, history):
    history.append({
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "published_at": None,
        "source": item.get("source"),
        "media_id": item.get("media_id"),
        "pexels_id": item.get("pexels_id"),
        "pixabay_id": item.get("pixabay_id"),
    })


def collect_source_videos(source, query):
    if source == "Pexels":
        return collect_pexels_videos(
            os.getenv("PEXELS_API_KEY", "").strip(), query,
            VIDEO_ORIENTATION, VIDEO_RESULTS_PER_RUN,
            VIDEO_MAX_DURATION_SECONDS, VIDEO_MAX_SIZE_BYTES,
        )
    if source == "Pixabay":
        return collect_pixabay_videos(
            os.getenv("PIXABAY_API_KEY", "").strip(), query,
            VIDEO_RESULTS_PER_RUN, VIDEO_MAX_DURATION_SECONDS,
            VIDEO_MAX_SIZE_BYTES,
        )
    return []


def publish_video(item, history, dry_run, download_video=download_video_temp, send_video=send_telegram_video):
    temporary_video = None
    try:
        temporary_video = download_video(item["video_url"], VIDEO_MAX_SIZE_BYTES)
        caption = format_video_caption(item)
        if dry_run:
            print("[DRY RUN] Telegram was not called")
            print(f"Video validated: {temporary_video.mime_type}, {temporary_video.size_bytes} bytes")
            print(caption)
            return False
        with temporary_video.path.open("rb") as video_file:
            result = send_video(
                video_file, caption, filename=temporary_video.path.name,
                mime_type=temporary_video.mime_type,
            )
        if result:
            add_video_to_history(item, history)
            return True
        return False
    except (VideoDownloadError, OSError) as error:
        print(f"Video warning: {type(error).__name__}")
        return False
    finally:
        if temporary_video and temporary_video.path.exists():
            temporary_video.path.unlink()


def run(now=None):
    configure_ssl()
    query = choose_search_query(now)
    history = load_history()
    print(f"Video query: {query}")
    selected = None
    for source in choose_source_order(now):
        try:
            candidates = collect_source_videos(source, query)
        except (PexelsVideoError, PixabayVideoError) as error:
            print(f"Video source warning ({source}): {error}")
            continue
        print(f"Suitable videos ({source}): {len(candidates)}")
        selected = select_unpublished_video(candidates, history)
        if selected is not None:
            break
    if selected is None:
        print("No unpublished video is available; publication skipped.")
        return None
    print(f"Selected {selected.get('source')} video: {selected.get('media_id')}")
    changed = publish_video(selected, history, DRY_RUN)
    if not DRY_RUN and changed:
        save_history(history)
    return selected


if __name__ == "__main__":
    try:
        with single_instance_lock("auto-video-autoposter.lock"):
            run()
    except AlreadyRunningError:
        print("Autoposter is already running; this run was stopped.")
