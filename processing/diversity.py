"""Greedy editorial diversity selection for an already ranked news list."""

from processing.deduplicator import meaningful_tokens


DEFAULTS = {
    "text_limit": 1200,
    "core_min_shared_tokens": 4,
    "core_min_token_overlap": 0.30,
    "core_min_token_jaccard": 0.14,
    "core_dense_match_tokens": 5,
    "min_shared_tokens": 4,
    "min_token_overlap": 0.35,
    "min_token_jaccard": 0.16,
    "stop_words": set(),
    "noise_prefixes": (),
}


def select_diverse(news_items, limit, settings=None):
    """Keep ranked order while excluding overly similar batch candidates."""

    items = list(news_items)
    limit = max(0, int(limit))

    if limit == 0:
        return []

    # Missing or disabled settings preserve the original top-N behavior.
    if not settings or settings.get("enabled") is False:
        return items[:limit]

    values = {**DEFAULTS, **settings}
    selected = []
    selected_fingerprints = []

    for item in items:
        candidate = (
            _core_tokens(item, values),
            _full_context_tokens(item, values),
        )

        if any(
            _fingerprints_are_too_similar(candidate, existing, values)
            for existing in selected_fingerprints
        ):
            continue

        selected.append(item)
        selected_fingerprints.append(candidate)

        if len(selected) == limit:
            break

    return selected


def _core_tokens(news_item, settings):
    # Title and description keep the compact story identity from being diluted.
    text = " ".join(
        (
            str(news_item.get("title") or ""),
            str(news_item.get("description") or ""),
        )
    )
    return meaningful_tokens(text, settings)


def _full_context_tokens(news_item, settings):
    topics = news_item.get("matched_topics") or []

    if isinstance(topics, str):
        topics = [topics]

    body = " ".join(
        (
            str(news_item.get("description") or ""),
            str(news_item.get("article_text") or ""),
        )
    )
    text = " ".join(
        (
            str(news_item.get("title") or ""),
            str(body)[:settings["text_limit"]],
            str(news_item.get("event_category") or ""),
            " ".join(str(topic) for topic in topics),
        )
    )
    return meaningful_tokens(text, settings)


def _fingerprints_are_too_similar(first, second, settings):
    first_core, first_full = first
    second_core, second_full = second

    # A matching core is the primary editorial story-cluster signal.
    if _tokens_are_too_similar(
        first_core,
        second_core,
        settings["core_min_shared_tokens"],
        settings["core_min_token_overlap"],
        settings["core_min_token_jaccard"],
        settings["core_dense_match_tokens"],
    ):
        return True

    # Broader context remains a fallback for stories with different summaries.
    return _tokens_are_too_similar(
        first_full,
        second_full,
        settings["min_shared_tokens"],
        settings["min_token_overlap"],
        settings["min_token_jaccard"],
    )


def _tokens_are_too_similar(
    first,
    second,
    min_shared_tokens,
    min_token_overlap,
    min_token_jaccard,
    dense_match_tokens=None,
):
    if not first or not second:
        return False

    shared = first & second

    # Enough shared core terms identify a cluster even in longer summaries.
    if dense_match_tokens is not None and len(shared) >= dense_match_tokens:
        return True

    if len(shared) < min_shared_tokens:
        return False

    overlap = len(shared) / min(len(first), len(second))
    jaccard = len(shared) / len(first | second)
    return (
        overlap >= min_token_overlap
        or jaccard >= min_token_jaccard
    )
