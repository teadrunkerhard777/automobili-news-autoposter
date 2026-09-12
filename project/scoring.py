"""Ranking rules for the auto and motorcycle channel."""


TOPIC_SCORES = {
    "safety_recalls": 7, "motorcycles": 5, "market": 5, "industry": 4,
    "new_models": 4, "technology": 3, "ownership": 3, "motorsport": 2,
}

MAJOR_MOTORSPORT_SIGNALS = (
    "победил", "выиграл", "одержал победу", "стал чемпионом",
    "стала чемпионом", "завоевал титул", "завоевала титул",
    "занял подиум", "заняла подиум", "авария", "дисквалифиц",
    "оштрафован", "оштрафована", "отменили", "отменен", "отменён",
    "календарь", "подписал контракт", "подписала контракт",
    "официально объяв", "установил рекорд", "установила рекорд",
    "завершил карьер", "завершила карьер", "дебютирует",
)

IMPORTANCE_BONUSES = {
    "official": (2, ("официально", "объявил", "подтвердил")),
    "russia": (2, ("в россии", "россиян", "российск")),
    "recall": (2, ("отзывает", "отзывн", "опасн", "дефект")),
    "production": (1, ("производств", "конвейер", "завод", "сборк")),
}

LOW_VALUE_PENALTIES = {
    "rumor": (5, (
        "слух", "может представить", "предположительно",
        "дилер рассказал о перспективах", "эксперт рассказал о перспективах",
        "по мнению дилера", "по мнению эксперта", "способен стать",
        "может стать", "прогнозирует", "ожидается у дилеров",
    )),
    "auction": (2, ("выставили на продажу", "продадут на аукционе")),
    "ranking": (2, ("топ-", "назвали лучшие", "назвали худшие")),
    "celebrity": (4, ("знаменитост", "певец", "певица", "блогер")),
}


def calculate_score(news_item):
    """Rank relevant stories by usefulness and event importance."""

    title = str(news_item.get("title", "")).casefold()
    text = f"{title} {news_item.get('description', '')}".casefold()
    topics = news_item.get("matched_topics", [])

    if topics == ["motorsport"]:
        # Feed descriptions often mention official bodies, champions, cars,
        # and technical terms as background. Only the headline event decides
        # whether a racing story is important enough for this mixed channel.
        return (
            6
            if any(signal in title for signal in MAJOR_MOTORSPORT_SIGNALS)
            else 2
        )

    score = sum(TOPIC_SCORES.get(topic, 0) for topic in topics)
    score += sum(points for points, keywords in IMPORTANCE_BONUSES.values() if any(keyword in text for keyword in keywords))
    score -= sum(points for points, keywords in LOW_VALUE_PENALTIES.values() if any(keyword in text for keyword in keywords))
    if "motorsport" in topics and any(signal in title for signal in MAJOR_MOTORSPORT_SIGNALS):
        score += 4
    return max(0, score)
