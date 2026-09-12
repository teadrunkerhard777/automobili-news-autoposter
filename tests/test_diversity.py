from processing.deduplicator import meaningful_tokens, remove_duplicates
from processing.diversity import select_diverse
from project.settings import DIVERSITY_SETTINGS


def make_item(title, body, category, source="example", description=""):
    slug = title.casefold().replace(" ", "-")
    return {
        "title": title,
        "description": description,
        "article_text": body,
        "event_category": category,
        "matched_topics": [category],
        "source": source,
        "url": f"https://{source}.test/{slug}",
    }


def similar_cluster():
    first = make_item(
        "Executive publishes accusations",
        "founder partner contract payment lawsuit dispute private messages",
        "business",
    )
    second = make_item(
        "Contract response follows",
        "partner founder contract lawsuit dispute payments message response",
        "business",
    )
    return first, second


def distinct_items():
    return [
        make_item(
            "Space telescope captures a distant galaxy",
            "astronomers observe stars orbit light cosmic image",
            "science",
        ),
        make_item(
            "Central bank changes its interest rate",
            "economy inflation lending monetary policy markets",
            "finance",
        ),
        make_item(
            "Football coach leaves the city club",
            "team season players stadium training championship",
            "sports",
        ),
    ]


def continuing_story_cluster():
    return [
        make_item(
            "Rowan accuses Casey in their contract conflict",
            "Financial records and private messages are examined in detail.",
            "business",
            description="Rowan and Casey continue their public contract dispute.",
        ),
        make_item(
            "Morgan joins the Rowan and Casey contract conflict",
            "A new interview focuses on a cancelled tour and management changes.",
            "business",
            description="Morgan comments on the Rowan Casey public dispute.",
        ),
        make_item(
            "Casey answers Rowan with a contract accusation",
            "Lawyers discuss evidence and a separate agreement between the teams.",
            "business",
            description="Casey denies Rowan claims in the continuing public dispute.",
        ),
    ]


def test_diverse_topics_preserve_ranked_order():
    items = distinct_items()

    assert select_diverse(items, 2, DIVERSITY_SETTINGS) == items[:2]


def test_very_similar_stories_are_not_selected_together():
    first, second = similar_cluster()

    assert select_diverse(
        [first, second],
        2,
        DIVERSITY_SETTINGS,
    ) == [first]


def test_next_diverse_candidate_replaces_skipped_story():
    first, similar = similar_cluster()
    diverse = distinct_items()[0]

    assert select_diverse(
        [first, similar, diverse],
        2,
        DIVERSITY_SETTINGS,
    ) == [first, diverse]


def test_core_fingerprint_limits_a_continuing_story_cluster():
    cluster = continuing_story_cluster()
    independent = distinct_items()[:2]

    assert remove_duplicates(cluster) == cluster
    assert select_diverse(
        [*cluster, *independent],
        3,
        DIVERSITY_SETTINGS,
    ) == [cluster[0], *independent]


def test_three_generic_shared_words_do_not_block_independent_stories():
    first = make_item(
        "Singer court news follows a contract appeal",
        "The label disputes royalty calculations in a commercial case.",
        "business",
    )
    second = make_item(
        "Singer court news accompanies a charity concert",
        "The performer raises funds for a regional children's hospital.",
        "culture",
    )

    assert select_diverse(
        [first, second],
        2,
        DIVERSITY_SETTINGS,
    ) == [first, second]


def test_five_shared_core_tokens_match_despite_low_overlap():
    shared = "actor contract dispute interview response"
    first = make_item(
        f"{shared} agency payment archive lawyer producer private records "
        "meeting studio finance letter witness manager history document office "
        "royalty negotiation",
        "Accounting documents outline royalty calculations.",
        "business",
    )
    second = make_item(
        f"{shared} festival director audience schedule concert camera "
        "travel venue rehearsal ticket sponsor weekend statement performance "
        "costume lighting broadcast backstage",
        "Tour rehearsals begin before regional performances.",
        "culture",
    )
    first_core = meaningful_tokens(first["title"], DIVERSITY_SETTINGS)
    second_core = meaningful_tokens(second["title"], DIVERSITY_SETTINGS)
    shared_core = first_core & second_core

    assert len(shared_core) == 5
    assert len(shared_core) / min(len(first_core), len(second_core)) < 0.30
    assert len(shared_core) / len(first_core | second_core) < 0.14

    assert select_diverse(
        [first, second],
        2,
        DIVERSITY_SETTINGS,
    ) == [first]


def test_existing_core_overlap_rule_still_blocks_four_shared_tokens():
    first = make_item(
        "alpha bravo charlie delta echo foxtrot",
        "Unique background material for the first report.",
        "business",
    )
    second = make_item(
        "alpha bravo charlie delta golf hotel",
        "Different background material for the second report.",
        "culture",
    )

    assert select_diverse(
        [first, second],
        2,
        DIVERSITY_SETTINGS,
    ) == [first]


def test_selection_returns_all_available_distinct_candidates():
    items = distinct_items()[:2]

    assert select_diverse(items, 5, DIVERSITY_SETTINGS) == items


def test_limit_one_preserves_top_ranked_item():
    items = distinct_items()

    assert select_diverse(items, 1, DIVERSITY_SETTINGS) == [items[0]]


def test_disabled_or_missing_settings_preserve_top_n():
    first, similar = similar_cluster()
    items = [first, similar]

    assert select_diverse(items, 2, {"enabled": False}) == items
    assert select_diverse(items, 2, None) == items


def test_event_dedup_and_diversity_are_separate_stages():
    first, similar = similar_cluster()

    assert remove_duplicates([first, similar]) == [first, similar]
    assert select_diverse(
        [first, similar],
        2,
        DIVERSITY_SETTINGS,
    ) == [first]
