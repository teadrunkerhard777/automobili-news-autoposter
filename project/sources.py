"""Free sources for the auto, motorcycle, and motorsport channel."""

from datetime import datetime, timedelta, timezone


now = datetime.now(timezone.utc)


def extract_autostat_article(soup):
    """Extract only the editorial body, excluding login and site furniture."""

    body = soup.select_one("div.text.inner_content")
    if body is None:
        return ""

    paragraphs = [
        " ".join(node.get_text(" ", strip=True).split())
        for node in body.select("p")
    ]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)

SOURCES = [
    {
        "name": "Auto Moto local fixture", "type": "static", "enabled": False,
        "items": [
            {
                "title": "Производитель официально представил новый кроссовер",
                "url": "https://example.invalid/auto/new-crossover",
                "published_at": now - timedelta(hours=2),
                "description": "Новая модель получила гибридный двигатель и выйдет на российский рынок в этом году.",
                "article_text": "Компания раскрыла характеристики силовой установки, оснащение и сроки начала продаж нового кроссовера.",
                "image_url": None,
            },
            {
                "title": "BMW представила новую линейку мотоциклов",
                "url": "https://example.invalid/moto/bmw-lineup",
                "published_at": now - timedelta(hours=3),
                "description": "Обновлённые мотоциклы получили новую электронику и переработанную подвеску.",
                "article_text": "Производитель рассказал о технических изменениях и сроках выхода моделей.",
                "image_url": None,
            },
            {
                "title": "Пилот выиграл Гран-при и возглавил чемпионат Формулы-1",
                "url": "https://example.invalid/motorsport/grand-prix",
                "published_at": now - timedelta(hours=4),
                "description": "Победа изменила положение лидеров сезона.",
                "article_text": "Гонщик выиграл этап и вышел на первое место.",
                "image_url": None,
            },
            {
                "title": "Музыкант показал редкую машину из своей коллекции",
                "url": "https://example.invalid/entertainment/celebrity-car",
                "published_at": now - timedelta(hours=1),
                "description": "Певец рассказал подписчикам о покупке.",
                "article_text": "Публикация посвящена жизни знаменитости.",
                "image_url": None,
            },
        ],
    },
    {
        "name": "Drom.ru Новости", "type": "rss",
        "url": "https://www.drom.ru/export/xml/news.rss", "enabled": True,
        "limit": 20, "source_kind": "automotive_media", "language": "ru",
    },
    {
        "name": "АВТОСТАТ", "type": "rss",
        "url": "https://www.autostat.ru/news/rss/", "enabled": True,
        "limit": 30, "source_kind": "automotive_market_media",
        "language": "ru",
    },
    {
        "name": "Autosport.com.ru", "type": "rss",
        "url": "https://autosport.com.ru/rss/news.xml", "enabled": True,
        "limit": 20, "source_kind": "motorsport_media", "language": "ru",
    },
]

SOURCE_EXTRACTORS = {
    "АВТОСТАТ": extract_autostat_article,
}
SOURCE_STOP_MARKERS = {
    "Drom.ru Новости": ("Читайте также:",),
    "АВТОСТАТ": ("Фото:", "Теги:", "также подписывайтесь"),
    "Autosport.com.ru": ("Читайте также:",),
}
