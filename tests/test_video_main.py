from datetime import datetime, timezone

from project.video_settings import VIDEO_CAPTIONS
from publishing.telegram import TelegramSendResult, TemporaryVideo
from video_main import (
    choose_video_caption,
    add_video_to_history,
    choose_search_query,
    choose_source_order,
    format_video_caption,
    publish_video,
    select_unpublished_video,
    video_slot_already_published,
    video_slot_key,
)


def video():
    return {
        "title": "Автомобильное настроение",
        "url": "https://www.pexels.com/video/42/",
        "source": "Pexels",
        "source_label": "Pexels",
        "video_url": "https://video.test/42.mp4",
        "media_id": "pexels:42",
        "pexels_id": 42,
    }


def test_captions_are_positive_varied_and_unique():
    assert len(VIDEO_CAPTIONS) == 30
    assert len(set(VIDEO_CAPTIONS)) == len(VIDEO_CAPTIONS)


def test_caption_does_not_repeat_until_all_have_been_used():
    item = video()
    first = choose_video_caption(item, [])
    history = [{"video_caption": first}]

    assert choose_video_caption(item, history) != first


def test_day_and_evening_rotate_query_and_source():
    day = datetime(2026, 9, 16, 8, tzinfo=timezone.utc)
    evening = datetime(2026, 9, 16, 15, tzinfo=timezone.utc)

    assert choose_search_query(day) != choose_search_query(evening)
    assert choose_source_order(day)[0] != choose_source_order(evening)[0]


def test_video_slot_key_separates_day_and_evening():
    day = datetime(2026, 9, 26, 8, tzinfo=timezone.utc)
    evening = datetime(2026, 9, 26, 16, tzinfo=timezone.utc)

    assert video_slot_key(day) == "2026-09-26:day"
    assert video_slot_key(evening) == "2026-09-26:evening"


def test_published_video_slot_blocks_duplicate_run():
    now = datetime(2026, 9, 26, 8, tzinfo=timezone.utc)
    history = [{"video_slot": "2026-09-26:day"}]

    assert video_slot_already_published(history, now) is True


def test_selection_skips_already_published_url():
    fresh = {**video(), "url": "https://www.pexels.com/video/43/"}
    assert select_unpublished_video(
        [video(), fresh], [{"url": video()["url"]}]
    ) == fresh


def test_caption_is_short_positive_and_credits_source():
    caption = format_video_caption(video())

    assert len(caption) < 300
    assert caption.endswith(
        '<a href="https://www.pexels.com/video/42/">Pexels</a>'
    )


def test_dry_run_removes_video_without_calling_telegram(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")
    changed = publish_video(
        video(), [], True,
        download_video=lambda *args: TemporaryVideo(path, "video/mp4", 5),
        send_video=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Telegram must not be called")
        ),
    )

    assert changed is False
    assert path.exists() is False


def test_confirmed_send_adds_video_history(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")
    history = []
    changed = publish_video(
        video(), history, False,
        download_video=lambda *args: TemporaryVideo(path, "video/mp4", 5),
        send_video=lambda *args, **kwargs: TelegramSendResult(True),
    )

    assert changed is True
    assert history[0]["media_id"] == "pexels:42"
    assert "event_fingerprint" not in history[0]


def test_add_video_history_keeps_source_ids():
    history = []
    now = datetime(2026, 9, 26, 8, tzinfo=timezone.utc)
    add_video_to_history(video(), history, now)
    assert history[0]["pexels_id"] == 42
    assert history[0]["video_slot"] == "2026-09-26:day"
