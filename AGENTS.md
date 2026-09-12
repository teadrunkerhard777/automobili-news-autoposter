# Autoposter Template Agent Instructions

## Mission

- This repository is a reusable Python template for small Telegram autoposters.
- Keep it understandable: prefer plain functions and dictionaries over frameworks.
- Reusable infrastructure lives outside `project/`.
- **Project-specific rules live in `project/`.**
- Do not move topic keywords, source policy, scoring weights, or channel formatting into core.
- Use free sources and libraries; do not add paid or AI APIs as required dependencies.

## Safety defaults

- `AUTOPOSTER_DRY_RUN` defaults to `true`.
- DRY_RUN may collect, filter, rank, extract, deduplicate, format, and print.
- DRY_RUN must not call Telegram or write publication history.
- Never perform a real Telegram send unless the task explicitly requires it.
- Do not treat a test request or diagnostic run as permission to publish.
- Preserve `storage/published.json` unless the task explicitly authorizes history changes.
- Never expose Telegram tokens, chat IDs, Bot API URLs containing tokens, or `.env` contents.

## Change rules

- Study existing code and documentation before editing.
- Check Git status and preserve user-owned changes.
- Make the smallest change that solves the task.
- Keep the shared `news_item` fields and pipeline order stable.
- Keep title, URL, article text, image, score, and history attached to one item.
- Catch specific exceptions; never use a bare `except:`.
- Isolate failure to one source, article, image, or post where possible.
- Do not add a dependency-injection container, plugin marketplace, database, async rewrite, or web dashboard.

## Project layer

- Change sources and extractor registrations in `project/sources.py`.
- Change relevance and event categories in `project/filters.py`.
- Change ranking weights in `project/scoring.py`.
- Change Telegram presentation in `project/formatter.py`.
- Change limits and event thresholds in `project/settings.py`.
- Scoring ranks relevant stories; it must not bypass the project relevance gate.
- Event categories must be meaningful within the project and must not be invented by core.

## Source and extraction rules

- RSS and HTML collectors must return the shared item shape.
- Use direct article URLs and reliable timezone-aware dates.
- Use `None` rather than inventing missing dates or images.
- Do not bypass CAPTCHA or anti-bot protection.
- Fetch an article once and extract text plus image from the same HTML response.
- Prefer generic extraction until a real source defect is reproduced.
- Register source-specific extraction by exact source name.
- A source-specific fix must not alter unrelated sources.
- Do not use global aggressive cleanup to fix one site's footer.

## Publishing and history

- Keep one selected item equal to at most one Telegram message.
- Preserve remote URL photo, confirmed remote-fetch fallback, multipart upload, and text fallback order.
- Retry only a known pre-connection timeout.
- ReadTimeout and ambiguous ConnectionError are uncertain outcomes: no retry, no fallback, no history update.
- Add history only after confirmed Telegram success.
- Save history once after the publication loop and only when it changed.
- Keep legacy URL-only history entries compatible.
- Temporary image files belong in the system temp directory and must always be removed.

## Tests and verification

- Add focused regression tests for behavior changes.
- Tests must not use real network services or Telegram.
- Run focused tests while editing and `python -m pytest` before handoff.
- Run end-to-end diagnostics only with effective DRY_RUN enabled.
- Hash or diff `storage/published.json` before and after an end-to-end run.
- Run `git diff --check` and inspect the complete final diff.
- Confirm no `.env`, secret, cache, temporary image, or unrelated file is tracked.
- If external verification is unavailable, report the limitation rather than inventing a result.

## Git

- Do not reset, amend, force-push, or discard user work without explicit authorization.
- Stage only task files; never use broad staging when history is the only intended change.
- Use the commit subject requested by the task.
- Commit after the task is complete and verified.
- Do not push or create a remote repository unless explicitly requested.

## Final report

Include files changed, relevant settings, tests and pass count, DRY_RUN result,
Telegram activity, history state, commit hash, and final working-tree state.
Call out assumptions, unavailable external checks, and project-specific choices.
