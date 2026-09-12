"""Auto, motorcycle, and motorsport editorial relevance rules."""

import re


TOPIC_KEYWORDS = {
    "motorcycles": ("мотоцикл", "мотоциклет", "байк", "спортбайк", "скутер", "максискутер", "эндуро", "мототехник", "мотосезон"),
    "safety_recalls": ("отзывн", "отзывает", "отозвал", "дефект", "неисправност", "угрозу безопасности", "запретили эксплуатацию", "краш-тест"),
    "new_models": ("представил", "представила", "представили", "рассекретил", "показал", "показала", "дебют", "премьера", "новое поколение", "обновленн", "обновлённ", "рестайлинг", "концепт"),
    "market": ("авторын", "продаж", "цены", "подорож", "подешев", "утильсбор", "пошлин", "импорт", "дилер", "вторичный рынок"),
    "industry": ("автозавод", "автопром", "производств", "сборк", "конвейер", "локализац", "завод", "компания", "бренд", "марка"),
    "technology": ("двигател", "мотор", "трансмис", "батаре", "аккумулятор", "электромоб", "гибрид", "водород", "автопилот", "беспилот", "зарядк", "платформ", "шасси", "подвеск", "коробк"),
    "ownership": ("техобслуж", "ремонт", "запчаст", "страхован", "осаго", "техосмотр", "пдд", "штраф", "транспортный налог", "топливо", "бензин", "дизель", "шины", "резина"),
    "motorsport": ("формула-1", "формулы-1", "formula 1", "f1", "гран-при", "ралли", "wrc", "дакар", "motogp", "moto gp", "superbike", "гонщик", "пилот", "гоночн", "автоспорт", "мотоспорт"),
}

VEHICLE_CONTEXT = (
    "авто", "машин", "автомоб", "кроссовер", "внедорожник", "седан", "хэтчбек", "универсал", "минивэн", "пикап", "купе", "родстер", "грузовик", "фургон", "мото", "байк", "скутер", "двигател",
    "lada", "ваз", "уаз", "москвич", "audi", "bmw", "mercedes", "volkswagen", "toyota", "lexus", "honda", "nissan", "mazda", "subaru", "suzuki", "mitsubishi", "hyundai", "kia", "ford", "renault", "peugeot", "citroen", "volvo", "porsche", "ferrari", "lamborghini", "tesla", "geely", "haval", "chery", "exeed", "omoda", "jaecoo", "tank", "byd", "zeekr", "voyah", "ducati", "yamaha", "kawasaki", "harley-davidson", "ktm", "aprilia",
)

EXCLUDE_PATTERNS = (
    r"\bдтп\b.*\bпогиб", r"\bпогиб.*\bдтп\b",
    r"сбил[аи]?\s+(?:пешеход|ребен|ребён)",
    r"автомобил.*звезд[ыа]",
    r"(?:машин|автомобил).*(?:певц|актер|актёр|блогер|музыкант)",
    r"(?:певц|актер|актёр|блогер|музыкант).*(?:машин|автомобил)",
)

EVENT_CATEGORY_PRIORITY = (
    "safety_recalls", "motorcycles", "motorsport", "new_models",
    "market", "industry", "technology", "ownership",
)


def is_relevant(news_item):
    """Accept a vehicle story with a concrete editorial topic signal."""

    text = f"{news_item.get('title', '')} {news_item.get('description', '')}".casefold()
    excluded = any(re.search(pattern, text) for pattern in EXCLUDE_PATTERNS)
    has_vehicle_context = any(keyword in text for keyword in VEHICLE_CONTEXT)
    matched = {
        topic for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    }

    # This feed is already narrowly scoped. Do not let generic words such as
    # "машина", "настройки", or "новая трасса" inflate racing stories.
    if news_item.get("source") == "Autosport.com.ru":
        matched = {"motorsport"}

    relevant = not excluded and bool(matched) and (has_vehicle_context or "motorsport" in matched)
    matched_topics = [topic for topic in EVENT_CATEGORY_PRIORITY if topic in matched] if relevant else []
    news_item["matched_topics"] = matched_topics
    news_item["event_category"] = matched_topics[0] if matched_topics else None
    news_item.setdefault("event_locations", [])
    return relevant
