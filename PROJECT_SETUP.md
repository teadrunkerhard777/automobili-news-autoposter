# How to create a new autoposter from this template

The first safe local version should take about 15–30 minutes. Keep the local
static source enabled until project rules and output are covered by tests.

## 1. Create a standalone project

Copy the template without carrying over its Git history, then initialize a new
repository:

```bash
cp -R autoposter-template my-autoposter
cd my-autoposter
rm -rf .git
git init
```

Update the title in `README.md`, the workflow `name` and concurrency group in
`.github/workflows/autoposter.yml`, and the lock name passed in `main.py` if
several autoposters can run on the same machine.

## 2. Create the Python environment

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run Python tools as modules from this environment. In particular, use
`python -m pytest`, not the standalone `pytest` command, so tests use the same
interpreter and installed packages as the application:

```bash
python -m pytest
```

## 3. Configure the project layer first

Channel-specific behavior belongs in `project/`. Usually edit these files in
this order:

1. `project/sources.py` — feeds, HTML pages, and extraction hooks;
2. `project/filters.py` — relevance and event categories;
3. `project/scoring.py` — ranking among relevant items;
4. `project/formatter.py` — Telegram text and photo captions;
5. `project/settings.py` — freshness, limits, score threshold, event dedup, and
   batch diversity.

Reusable collection, processing, article, publishing, and storage behavior
lives outside `project/`. Change core infrastructure only after reproducing a
generic limitation that cannot be expressed in the project layer.

## 4. Add an RSS source

Add source dictionaries to `SOURCES` in `project/sources.py`. RSS sources need
only a stable feed URL:

```python
{
    "name": "Vendor news RSS",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "enabled": True,
}
```

Use direct article URLs and feeds with reliable publication dates.

## 5. Add a declarative HTML source

HTML category pages are configured with CSS selectors:

```python
{
    "name": "Example news page",
    "type": "html",
    "url": "https://example.com/news",
    "base_url": "https://example.com",
    "item_selector": "article.card",
    "title_selector": "h2 a",
    "link_selector": "h2 a",
    "date_selector": "time[datetime]",
    "description_selector": "p.summary",
    "enabled": True,
    "limit": 20,
    "headers": {
        "User-Agent": "Mozilla/5.0 ExampleAutoposter/1.0",
    },
    "retries": 3,
}
```

`headers` are merged with the collector defaults; source values take priority.
`retries` is the number of retries after the initial request for temporary
`requests.RequestException` failures. The same source headers and retry count
are reused when the corresponding article page is fetched. The connection is
made by exact equality between `news_item["source"]` and source `name`.

Some pages use the selected card itself as the link:

```html
<a href="/news/example">
    <div class="title">Headline</div>
    <time datetime="2026-08-25T10:52:47.035Z"></time>
</a>
```

Describe that structure without a `link_selector`:

```python
{
    "name": "Linked card news",
    "type": "html",
    "url": "https://example.com/news",
    "base_url": "https://example.com",
    "item_selector": 'a[href^="/news/"]',
    "title_selector": ".title",
    "link_from_item": True,
    "date_selector": "time[datetime]",
    "enabled": True,
}
```

With `link_from_item=True`, the item must have `href`; invalid cards are safely
skipped. Relative links are resolved against `base_url` with `urljoin`.

Do not bypass CAPTCHA or anti-bot protection. Prefer free RSS or maintainable,
declarative HTML pages.

## 6. Publication dates

The normalizer accepts timezone-aware `datetime` values, RSS/RFC dates, and
timezone-aware ISO 8601 values, including:

```text
2026-08-25T10:52:47Z
2026-08-25T10:52:47.035Z
2026-08-25T13:52:47+03:00
```

`Z` is interpreted as UTC. Invalid and timezone-naive ISO strings normalize to
`None`, because freshness filtering needs a reliable timezone-aware value.

## 7. Define relevance and event data

Edit `project/filters.py`. `is_relevant(news_item)` must return a boolean and
should attach the project data used by event deduplication:

```python
def is_relevant(news_item):
    text = f"{news_item['title']} {news_item['description']}".casefold()
    accepted = "release" in text
    news_item["matched_topics"] = ["release"] if accepted else []
    news_item["event_category"] = "release" if accepted else None
    news_item["event_locations"] = []  # Optional event signal.
    return accepted
```

Core does not decide what a channel considers relevant.

## 8. Define scoring

Edit `project/scoring.py`. Return an integer; generic processing attaches it and
sorts candidates:

```python
def calculate_score(news_item):
    return 5 if "major" in news_item["title"].casefold() else 1
```

Scoring ranks relevant items. It must not bypass the relevance filter.

## 9. Configure article extraction when needed

Generic extraction reads paragraphs from `article` or `main` and extracts the
first available `og:image` or `twitter:image`. When a verified site needs a
reliable body selector, add a small function in `project/sources.py` and
register it under the exact source name:

```python
def extract_vendor_article(soup):
    body = soup.select_one("article .body")
    if body is None:
        return ""
    return "\n\n".join(
        paragraph.get_text(" ", strip=True)
        for paragraph in body.select("p")
    )


SOURCE_EXTRACTORS = {
    "Vendor news RSS": extract_vendor_article,
}
```

Use `SOURCE_STOP_MARKERS` for a verified source footer. Matching is
case-insensitive, starts at the beginning of a paragraph, and stops the article
at the first marker:

```python
SOURCE_STOP_MARKERS = {
    "Vendor news RSS": ("Read also:", "More from this source:"),
}
```

Do not turn one site's footer defect into aggressive global cleanup.

## 10. Format and inspect posts

Edit `project/formatter.py` and keep both interfaces:

- `format_post(news_item)` for `sendMessage`;
- `format_photo_caption(news_item)` for `sendPhoto`.

Escape title, source, body, and URL for Telegram HTML. Keep text and photo
captions inside their Telegram limits and preserve the source link. Add focused
tests for long text, HTML characters, missing article text, and image/no-image
items.

During DRY_RUN, inspect the final caption and the printed `image_url`. Confirm
that article text comes from the intended body, the image is the intended
`og:image`/`twitter:image`, and source footer blocks are absent.

## 11. Tune event deduplication and diversity

Edit `project/settings.py`:

- `NEWS_LOOKBACK_DAYS` controls freshness;
- `MAX_NEWS_PER_RUN` limits one publication batch;
- `MIN_PUBLICATION_SCORE` sets the project score threshold;
- `EVENT_DEDUP_SETTINGS` answers whether two items describe the same event;
- `DIVERSITY_SETTINGS` keeps one batch from containing too many related stories.

The pipeline order is:

```text
ranking
→ article loading
→ event deduplication
→ history filtering
→ diversity selection
→ selected news
```

Event dedup uses a conservative event fingerprint. Diversity is a separate,
softer editorial stage: it first compares a compact core fingerprint from title
and description, including an optional dense shared-token match, and then falls
back to a broader fingerprint containing article text, event category, and
matched topics. Tune thresholds and language-specific `stop_words` /
`noise_prefixes` in the project; do not add project vocabulary to generic code.

If diversity settings are absent or `enabled` is false, selection preserves the
ordinary ranked top-N behavior.

## 12. Run safely in DRY_RUN

Copy `.env.example` to `.env` and leave safe mode enabled:

```text
AUTOPOSTER_DRY_RUN=true
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Then run:

```bash
AUTOPOSTER_DRY_RUN=true python main.py
```

Inspect collected, fresh, relevant, minimum-score, unique, new, and selected
counts. Verify the selected order, captions, and image URLs. DRY_RUN must not
call Telegram or modify `storage/published.json`.

Before any authorized live test, rerun:

```bash
python -m pytest
```

## 13. Configure Telegram and automation

Create a bot through Telegram's official BotFather, add it to the target
channel, and grant only the permissions needed to post. Put the token and chat
ID in the local `.env`; never commit or paste them into source code.

For GitHub Actions, create `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` repository
secrets. Review `.github/workflows/autoposter.yml`: it runs tests, runs the
autoposter, and commits only `storage/published.json` after confirmed
publication. Keep `workflow_dispatch`, `cancel-in-progress: false`, and
history-only staging.

The template intentionally has no GitHub `schedule` block. If needed, use one
trusted external scheduler to call `workflow_dispatch`, start conservatively,
and verify workflow concurrency first.

## Lessons from the first real project

The first child project collected Russian and CIS celebrity news from two
independent sources: roughly 300 StarHit RSS items and 14 Super declarative HTML
items in the validation run. It exercised collection, normalization, project
filters and scoring, article and image extraction, cross-source event dedup,
batch diversity, formatting, DRY_RUN, and unit tests through one pipeline.

That production-like validation led to these generic template improvements:

- source-specific headers and finite retries for HTML listings;
- linked HTML cards through `link_from_item=True`;
- timezone-aware ISO 8601 normalization, including `Z` and milliseconds;
- reuse of source HTTP settings while fetching article pages;
- separate event dedup and batch-diversity stages;
- compact core and broad full-context diversity fingerprints;
- a dense core match for related stories with longer summaries.

The two sources were processed without project-specific changes in `core/`.
Cross-source event dedup found a shared story, article image extraction produced
a usable URL, and DRY_RUN produced a ready Telegram caption without publishing.

## Known limitations and future improvements

- Story-cluster cooldown across separate runs is not implemented. With
  `MAX_NEWS_PER_RUN = 1`, related follow-ups can still be selected on later
  runs. This is a future improvement, not a v1.0 blocker.
- A source-specific parser may still be necessary when a site cannot be
  described reliably with RSS or declarative HTML selectors.
- The formatter is extractive: it does not correct source typos and does not
  generate an LLM summary.

## v1.0 readiness

The template has passed its first production-like validation: the complete
pipeline worked with RSS and declarative HTML sources, the discovered generic
limitations were fixed without project-specific core hacks, and the automated
test suite covers the resulting behavior. It is therefore a **v1.0 candidate**.
No Git tag is created by this setup process; tagging remains an explicit release
decision.
