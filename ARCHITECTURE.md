# Architecture

## Reusable core

The reusable layer is ordinary Python modules:

- `collectors/` converts RSS, declarative HTML, or local demo items into one shape;
- `processing/` handles date filtering, score application, ranking, and dedup;
- `article/` fetches one HTML page and derives text plus image URL;
- `generation/` contains theme-neutral text-length helpers;
- `publishing/` sends Telegram text/photos safely;
- `storage/` stores confirmed publications and compact event fingerprints;
- `core/` configures TLS and prevents concurrent local runs.

No core module imports topic keywords, channel hashtags, or a domain category.

## Project-specific layer

Everything a new channel owner normally changes lives in `project/`:

- `sources.py`: sources and source-specific article extraction registry;
- `filters.py`: `is_relevant()` and `event_category` assignment;
- `scoring.py`: `calculate_score()`;
- `formatter.py`: text message and photo caption;
- `settings.py`: limits and event-dedup thresholds.

## Control flow

```text
enabled sources
-> shared news_item normalization
-> date filter
-> project is_relevant
-> project score and generic ranking
-> one article fetch for text + image
-> URL/title/event dedup
-> history or DRY_RUN bypass
-> MAX_NEWS_PER_RUN
-> project formatter
-> Telegram publisher or DRY_RUN output
-> confirmed-success history update
```

Article loading precedes event dedup because the event fingerprint uses article
facts. A preloaded local/static item skips the HTTP request.

## Extension points

The template intentionally uses functions and dictionaries rather than abstract
classes. Projects extend behavior by editing `project/`, declaring an HTML
source, or registering one source extractor. Core changes should be rare.

## History

`storage/published.json` starts as `[]`. New entries contain URL, title,
publication time, source, and a compact event fingerprint. Old URL-only entries
remain valid. DRY_RUN never saves history; production saves once only after at
least one confirmed publication.

## Publishing

The photo chain mirrors the proven LiveCrime behavior:

```text
remote URL sendPhoto
-> only a confirmed Telegram remote-fetch error
-> validated temporary download
-> multipart sendPhoto
-> confirmed failure
-> sendMessage
```

ConnectTimeout may retry because connection was not established. ReadTimeout and
general ConnectionError are uncertain: no retry, no fallback, and no history
update, because Telegram may already have created the message.

## Event dedup

The project supplies `event_category`; core never supplies a topic. Generic core
compares category, meaningful tokens, time window, and optional locations.
Location strengthens a match but is not mandatory. Without it, a denser token
match is required. Thresholds live in `project/settings.py`.

## Source-specific extraction

Generic extraction prefers `<article>`, then `<main>`, then page paragraphs. A
problem source can register a BeautifulSoup extractor in `SOURCE_EXTRACTORS` or
verified footer markers in `SOURCE_STOP_MARKERS`. Those rules are keyed by exact
source name and cannot alter unrelated sites.

## LiveCrime mapping

| LiveCrime component | Template component | Reusable? | Notes |
|---|---|---:|---|
| `main.py` orchestration | `main.py` | Adapted | Theme calls come from `project/`. |
| RSS collector | `collectors/rss_collector.py` | Yes | Same shared item contract. |
| Site adapters | Declarative HTML + project registry | Partly | Crime-source selectors were not copied. |
| Normalizer | `collectors/normalizer.py` | Yes | Simplified and kept source-neutral. |
| Date filtering/ranking | `processing/filters.py` | Yes | Relevance and score are injected functions. |
| Hard crime whitelist | `project/filters.py` example | No | Replaced by neutral technology example. |
| Crime scoring | `project/scoring.py` example | No | Core only applies returned score. |
| Crime hashtags/post | `project/formatter.py` example | No | Channel presentation belongs to project. |
| URL/title dedup | `processing/deduplicator.py` | Yes | Conservative title threshold retained. |
| Crime event families | `event_category` from project | Adapted | No homicide/suicide constants in core. |
| Article fetch/image meta | `article/fetcher.py` | Yes | One HTML response for text and image. |
| AGN/VN/Media cleanup | project extractor registry | Mechanism only | Source-specific rules were not copied. |
| Telegram publisher | `publishing/telegram.py` | Yes | Confirmed/uncertain semantics retained. |
| Publication history | `storage/history.py` | Yes | Empty data file; legacy URL support. |
| Run lock/TLS | `core/` | Yes | Neutral lock name and certifi setup. |
| GitHub workflow | `.github/workflows/autoposter.yml` | Adapted | Manual only; no repository-specific URL. |

The unsafe-to-generalize parts were LiveCrime's editorial whitelist, Russian
crime stems, severe-outcome combinations, crime score weights, hashtags,
geography regexes, enabled media list, and verified site DOM selectors. They
encode one channel's policy or one site's current HTML and therefore belong in a
concrete project, not reusable core.

