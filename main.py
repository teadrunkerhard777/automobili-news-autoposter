"""One understandable collection-to-publication pipeline."""

from bs4 import FeatureNotFound
from bs4.exceptions import ParserRejectedMarkup
from requests import RequestException

from article.fetcher import (
    clean_article_text,
    extract_article_image_url,
    extract_article_text,
    fetch_article_html,
)
from collectors.html_collector import collect_html
from collectors.rss_collector import collect_rss
from collectors.static_collector import collect_static
from config import (
    DRY_RUN,
    DIVERSITY_SETTINGS,
    EVENT_DEDUP_SETTINGS,
    MAX_NEWS_PER_RUN,
    MIN_PUBLICATION_SCORE,
    NEWS_LOOKBACK_DAYS,
    POST_MODE,
    SOURCES,
)
from core.environment import configure_ssl
from core.run_lock import AlreadyRunningError, single_instance_lock
from processing.deduplicator import remove_duplicates
from processing.diversity import select_diverse
from processing.filters import (
    add_scores,
    filter_by_date,
    filter_by_minimum_score,
    filter_relevant,
    sort_by_score,
)
from project.filters import is_relevant
from project.formatter import format_photo_caption, format_post
from project.scoring import calculate_score
from project.sources import SOURCE_EXTRACTORS, SOURCE_STOP_MARKERS
from publishing.telegram import (
    ImageDownloadError,
    download_image_temp,
    send_telegram_photo,
    send_telegram_post,
)
from storage.history import (
    add_to_history,
    is_published,
    load_history,
    save_history,
)


COLLECTORS = {
    "rss": collect_rss,
    "html": collect_html,
    "static": collect_static,
}


def collect_enabled_news(sources=SOURCES):
    """Collect enabled sources while isolating unsupported types."""

    active = [source for source in sources if source.get("enabled", True)]
    all_news = []
    print(f"Enabled sources: {len(active)}")

    for source in active:
        collector = COLLECTORS.get(source.get("type"))

        if collector is None:
            print(f"Source warning ({source.get('name')}): unknown type")
            continue

        items = collector(source)
        print(f"Source: {source['name']} — {len(items)} items")
        all_news.extend(items)

    return all_news


def load_article_data(news_items, sources=None):
    """Fetch each page once, then derive text and image from the same HTML."""

    source_configs = _source_configs_by_name(sources)

    for item in news_items:
        if "article_text" in item and "image_url" in item:
            continue

        item.setdefault("article_text", "")
        item.setdefault("image_url", None)

        try:
            source_config = source_configs.get(item.get("source"))
            html = fetch_article_html(
                item["url"],
                source_config=source_config,
            )
            extracted = extract_article_text(
                html,
                source=item.get("source"),
                source_extractors=SOURCE_EXTRACTORS,
            )
            item["article_text"] = clean_article_text(
                extracted,
                source=item.get("source"),
                source_stop_markers=SOURCE_STOP_MARKERS,
            )
            item["image_url"] = extract_article_image_url(html, item["url"])
        except (RequestException, FeatureNotFound, ParserRejectedMarkup) as error:
            print(
                f"Article warning ({item.get('source')}): "
                f"{type(error).__name__}"
            )


def publish_selected_news(
    selected_news,
    history,
    dry_run,
    post_mode,
    send_post=send_telegram_post,
    send_photo=send_telegram_photo,
    download_image=download_image_temp,
    add_history=add_to_history,
    event_settings=EVENT_DEDUP_SETTINGS,
    sources=None,
):
    """Publish each selected item once and update history on confirmation."""

    history_changed = False
    source_configs = _source_configs_by_name(sources)

    for item in selected_news:
        post = format_post(item)
        caption = format_photo_caption(item)
        image_url = item.get("image_url")

        if dry_run:
            print("[DRY RUN] Telegram was not called")
            print(f"Image URL: {image_url or 'NOT FOUND'}")
            print(caption if image_url else post)
            continue

        if post_mode != "single":
            print(f"Unsupported POST_MODE: {post_mode}")
            continue

        succeeded = False
        uncertain = False

        if image_url:
            photo_result = send_photo(image_url, caption)
            succeeded = bool(photo_result)
            uncertain = getattr(photo_result, "uncertain", False)

            if (
                not succeeded
                and not uncertain
                and getattr(photo_result, "remote_fetch_failed", False)
            ):
                temporary_image = None

                try:
                    source_config = source_configs.get(item.get("source"))
                    temporary_image = download_image(
                        image_url,
                        source_config=source_config,
                    )

                    with temporary_image.path.open("rb") as image_file:
                        file_result = send_photo(
                            image_file,
                            caption,
                            filename=temporary_image.path.name,
                            mime_type=temporary_image.mime_type,
                        )

                    succeeded = bool(file_result)
                    uncertain = getattr(file_result, "uncertain", False)
                except (ImageDownloadError, OSError) as error:
                    print(f"Photo fallback warning: {type(error).__name__}")
                finally:
                    if temporary_image and temporary_image.path.exists():
                        temporary_image.path.unlink()

        if not succeeded and not uncertain:
            text_result = send_post(post)
            succeeded = bool(text_result)
            uncertain = getattr(text_result, "uncertain", False)

        # Uncertain delivery may already exist in Telegram: never duplicate it.
        if succeeded:
            add_history(item, history, event_settings)
            history_changed = True

    return history_changed


def _source_configs_by_name(sources=None):
    """Index source HTTP settings by the source name stored on each item."""

    return {
        source.get("name"): source
        for source in (SOURCES if sources is None else sources)
        if source.get("name")
    }


def run():
    configure_ssl()
    all_news = collect_enabled_news()
    fresh_news = filter_by_date(all_news, NEWS_LOOKBACK_DAYS)
    relevant_news = filter_relevant(fresh_news, is_relevant)
    add_scores(relevant_news, calculate_score)
    scored_news = filter_by_minimum_score(
        relevant_news,
        MIN_PUBLICATION_SCORE,
    )
    ranked_news = sort_by_score(scored_news)

    # Generic event fingerprints use article facts, so loading precedes dedup.
    load_article_data(ranked_news)
    unique_news = remove_duplicates(
        ranked_news,
        EVENT_DEDUP_SETTINGS,
        debug=DRY_RUN,
    )
    history = load_history()

    if DRY_RUN:
        new_news = unique_news.copy()
    else:
        new_news = [
            item for item in unique_news
            if not is_published(item, history, EVENT_DEDUP_SETTINGS)
        ]

    selected_news = select_diverse(
        new_news,
        MAX_NEWS_PER_RUN,
        DIVERSITY_SETTINGS,
    )
    print(f"Collected: {len(all_news)}")
    print(f"Fresh: {len(fresh_news)}")
    print(f"Relevant: {len(relevant_news)}")
    print(f"Minimum score: {len(scored_news)}")
    print(f"Unique: {len(unique_news)}")
    print(f"New: {len(new_news)}")
    print(f"Selected: {len(selected_news)}")

    history_changed = publish_selected_news(
        selected_news,
        history,
        DRY_RUN,
        POST_MODE,
    )

    if not DRY_RUN and history_changed:
        save_history(history)

    return selected_news


if __name__ == "__main__":
    try:
        with single_instance_lock("auto-moto-autoposter.lock"):
            run()
    except AlreadyRunningError:
        print("Autoposter is already running; this run was stopped.")
