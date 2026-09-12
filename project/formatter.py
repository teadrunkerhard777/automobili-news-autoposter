"""Telegram presentation for the auto and motorcycle channel."""

from html import escape

from generation.text import fit_text_to_html_limit


MESSAGE_LIMIT = 4000
PHOTO_CAPTION_LIMIT = 1000
SUMMARY_PARAGRAPH_LIMIT = 3
BRAND_HASHTAG = "#АвтомобилиНовости"

CATEGORY_PRESENTATION = {
    "safety_recalls": ("⚠️", "#Безопасность"),
    "motorcycles": ("🏍", "#Мото"),
    "motorsport": ("🏁", "#Автоспорт"),
    "new_models": ("🚘", "#Новинки"),
    "market": ("📊", "#Авторынок"),
    "industry": ("🏭", "#Автопром"),
    "technology": ("⚙️", "#Технологии"),
    "ownership": ("🔧", "#Автосоветы"),
}

TECHNICAL_PREFIXES = (
    "фото:", "источник фото", "автор фото", "на фото:", "реклама",
    "читайте также", "подписывайтесь", "обсудить", "источник:",
)


def format_post(news_item):
    return _format(news_item, MESSAGE_LIMIT, complete_paragraphs=False)


def format_photo_caption(news_item):
    return _format(news_item, PHOTO_CAPTION_LIMIT, complete_paragraphs=True)


def _format(news_item, limit, complete_paragraphs):
    emoji, category_tag = CATEGORY_PRESENTATION.get(news_item.get("event_category"), ("🚗", "#Авто"))
    source = escape(" ".join(str(news_item.get("source") or "Источник").split()))
    url = escape(str(news_item.get("url") or ""), quote=True)
    link = f'🔗 <a href="{url}">Читать источник</a>' if url else ""
    footer = f"{BRAND_HASHTAG} {category_tag}\n\n📰 {source}"
    if link:
        footer = f"{footer}\n{link}"

    title_budget = max(0, limit - len(footer) - len(f"{emoji} <b></b>") - 4)
    title = fit_text_to_html_limit(str(news_item.get("title") or "Без заголовка"), min(500, title_budget))
    header = f"{emoji} <b>{escape(title)}</b>"
    body_budget = max(0, limit - len(header) - len(footer) - 4)
    body = news_item.get("article_text") or news_item.get("description") or ""
    summary = _extract_summary(body, news_item.get("title", ""))
    summary = (_fit_complete_paragraphs(summary, body_budget) if complete_paragraphs else fit_text_to_html_limit(summary, body_budget))
    if summary:
        return f"{header}\n\n{escape(summary)}\n\n{footer}"
    return f"{header}\n\n{footer}"


def _extract_summary(text, title):
    """Keep the first useful source paragraphs and remove service blocks."""

    title_text = " ".join(str(title or "").split()).casefold()
    selected = []
    for raw_paragraph in str(text or "").splitlines():
        paragraph = " ".join(raw_paragraph.split())
        lowered = paragraph.casefold()
        if not paragraph or lowered == title_text or lowered.startswith(TECHNICAL_PREFIXES):
            continue
        selected.append(paragraph)
        if len(selected) == SUMMARY_PARAGRAPH_LIMIT:
            break
    return "\n\n".join(selected)


def _fit_complete_paragraphs(summary, max_escaped_length):
    selected = []
    for paragraph in summary.split("\n\n"):
        candidate = "\n\n".join((*selected, paragraph))
        if len(escape(candidate)) > max_escaped_length:
            break
        selected.append(paragraph)
    return "\n\n".join(selected)
