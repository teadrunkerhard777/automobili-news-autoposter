"""Telegram presentation for the auto and motorcycle channel."""

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from generation.text import fit_text_to_html_limit


MESSAGE_LIMIT = 4000
PHOTO_CAPTION_LIMIT = 1000
SUMMARY_PARAGRAPH_LIMIT = 3
CHANNEL_TIMEZONE = ZoneInfo("Asia/Yekaterinburg")
RUSSIAN_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

CATEGORY_PRESENTATION = {
    "safety_recalls": ("⚠️", "безопасность", "#Безопасность"),
    "motorcycles": ("🏍", "мото", "#Мото"),
    "motorsport": ("🏁", "автоспорт", "#Автоспорт"),
    "new_models": ("🚘", "новинки", "#Новинки"),
    "market": ("🚗", "авторынок", "#Авторынок"),
    "industry": ("🏭", "автопром", "#Автопром"),
    "technology": ("⚙️", "технологии", "#Технологии"),
    "ownership": ("🔧", "автосоветы", "#Автосоветы"),
}

HEADLINE_EMOJI_RULES = (
    (("мотоцикл", "байк", "скутер"), ("🏍️", "💨", "🛣️")),
    (("цен", "стоим", "рубл", "скидк"), ("💰", "🏷️", "💸")),
    (("продаж", "рынок", "спрос"), ("📈", "🚗", "🤝", "🛒")),
    (("представ", "показал", "показала", "премьера", "дебют"), ("🚘", "✨", "🆕")),
    (("завод", "производ", "сборк", "конвейер"), ("🏭", "🔩", "🛠️")),
    (("электромоб", "гибрид", "батаре", "двигател", "мотор"), ("⚡", "🔋", "⚙️")),
)

CATEGORY_EMOJI_PALETTES = {
    "safety_recalls": ("⚠️", "🛡️", "🚨"),
    "motorcycles": ("🏍️", "💨", "🛣️"),
    "motorsport": ("🏁", "🏎️", "🏆"),
    "new_models": ("🚘", "✨", "🆕"),
    "market": ("🚗", "📈", "🔑", "🏷️"),
    "industry": ("🏭", "🔩", "🛠️"),
    "technology": ("⚙️", "⚡", "🔋"),
    "ownership": ("🔧", "🛞", "🧰"),
}

TECHNICAL_PREFIXES = (
    "фото:", "источник фото", "автор фото", "на фото:", "реклама",
    "читайте также", "подписывайтесь", "обсудить", "источник:",
)


def format_post(news_item):
    return _format(news_item, MESSAGE_LIMIT, complete_paragraphs=False)


def format_photo_caption(news_item):
    return _format(news_item, PHOTO_CAPTION_LIMIT, complete_paragraphs=True)


def format_video_caption(news_item):
    return _format(news_item, PHOTO_CAPTION_LIMIT, complete_paragraphs=True)


def _format(news_item, limit, complete_paragraphs):
    fallback_emoji, category_label, category_tag = CATEGORY_PRESENTATION.get(
        news_item.get("event_category"),
        ("🚗", "авто", "#Авто"),
    )
    emoji = _select_title_emoji(news_item, fallback_emoji)
    source = escape(" ".join(str(news_item.get("source") or "Источник").split()))
    url = escape(str(news_item.get("url") or ""), quote=True)
    source_line = (
        f'📰 <a href="{url}">{source}</a>: {category_label}'
        if url else f"📰 {source}: {category_label}"
    )
    footer_parts = []
    publication_date = _format_publication_date(news_item.get("published_at"))
    if publication_date:
        footer_parts.append(f"📅 {publication_date}\n{source_line}")
    else:
        footer_parts.append(source_line)
    if url:
        footer_parts.append(f'🔗 <a href="{url}">Читать источник</a>')
    footer_parts.append(category_tag)
    footer = "\n\n".join(footer_parts)

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


def _select_title_emoji(news_item, fallback):
    """Choose a stable, meaningful emoji without repeating one per category."""

    title = " ".join(str(news_item.get("title") or "").split()).casefold()
    for keywords, palette in HEADLINE_EMOJI_RULES:
        if any(keyword in title for keyword in keywords):
            return _stable_palette_choice(title, palette)

    palette = CATEGORY_EMOJI_PALETTES.get(news_item.get("event_category"))
    return _stable_palette_choice(title, palette) if palette else fallback


def _stable_palette_choice(text, palette):
    return palette[sum(ord(character) for character in text) % len(palette)]


def _format_publication_date(value):
    """Format a timezone-aware publication date for the Russian channel."""

    if not isinstance(value, datetime) or value.tzinfo is None:
        return ""

    local_date = value.astimezone(CHANNEL_TIMEZONE)
    return (
        f"{local_date.day} {RUSSIAN_MONTHS[local_date.month - 1]} "
        f"{local_date.year}"
    )


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
