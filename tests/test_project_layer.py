from datetime import datetime, timezone

from bs4 import BeautifulSoup

from processing.filters import add_scores, filter_by_minimum_score, filter_relevant
from project.filters import is_relevant
from project.formatter import format_photo_caption, format_post
from project.scoring import calculate_score
from project.sources import extract_autostat_article


def item(title, description=""):
    return {
        "title": title,
        "description": description,
        "url": "https://example.test/item?a=1&b=2",
        "source": "Тест & источник",
        "published_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }


def test_filter_accepts_auto_moto_and_motorsport_but_rejects_celebrity_car():
    auto = item("Toyota представила новый кроссовер")
    moto = item("BMW обновила линейку мотоциклов")
    race = item("Пилот выиграл Гран-при Формулы-1")
    celebrity = item("Музыкант показал редкую машину из своей коллекции", "Певец рассказал подписчикам о покупке.")

    assert filter_relevant([auto, moto, race, celebrity], is_relevant) == [auto, moto, race]
    assert auto["event_category"] == "new_models"
    assert moto["event_category"] == "motorcycles"
    assert race["event_category"] == "motorsport"
    assert celebrity["matched_topics"] == []


def test_filter_rejects_unrelated_accident_news():
    assert not is_relevant(item("В ДТП с автомобилем погиб пешеход"))


def test_scoring_keeps_routine_racing_below_major_event():
    routine = item(
        "Льюис Хэмилтон: новая трасса интересна для пилотирования",
        "Гонщик рассказал о настройках машины перед этапом Формулы-1.",
    )
    routine["source"] = "Autosport.com.ru"
    major = item("Пилот выиграл Гран-при и возглавил чемпионат Формулы-1")
    for news in (routine, major):
        is_relevant(news)
    add_scores([routine, major], calculate_score)

    assert routine["score"] < 5
    assert major["score"] >= 5
    assert filter_by_minimum_score([routine, major], 5) == [major]


def test_autosport_source_does_not_accumulate_generic_auto_topics():
    news = item(
        "Команда показала машину на новой трассе",
        "Пилот Формулы-1 рассказал о настройках двигателя.",
    )
    news["source"] = "Autosport.com.ru"

    assert is_relevant(news)
    assert news["matched_topics"] == ["motorsport"]
    assert calculate_score(news) == 2


def test_motorsport_schedule_does_not_pass_on_background_description():
    news = item(
        "Гран При Испании Формулы 1: расписание и трансляции",
        "Официальный календарь чемпионата и технические данные машин.",
    )
    news["source"] = "Autosport.com.ru"
    is_relevant(news)

    assert calculate_score(news) == 2


def test_motorsport_quote_about_titles_is_not_treated_as_a_result():
    news = item(
        "«Не титулы и победы». Пилот назвал главное наследие карьеры в Ф1"
    )
    news["source"] = "Autosport.com.ru"
    is_relevant(news)

    assert calculate_score(news) == 2


def test_dealer_forecast_ranks_below_confirmed_market_event():
    forecast = item(
        "Дилер рассказал о перспективах гибридного кроссовера Avatr 07",
        "Ожидается у дилеров осенью и способен стать массовой моделью в России.",
    )
    confirmed = item(
        "Changan начал продажи нового дизельного пикапа в России",
        "Автомобиль поступил к дилерам по официально объявленной цене.",
    )
    for news in (forecast, confirmed):
        is_relevant(news)

    assert calculate_score(forecast) < calculate_score(confirmed)


def test_formatter_escapes_html_and_uses_editorial_tags():
    news = item("Toyota <показала> кроссовер", "Быстрее & экономичнее")
    is_relevant(news)
    post = format_post(news)

    assert "Toyota &lt;показала&gt;" in post
    assert "Быстрее &amp; экономичнее" in post
    assert "#АвтомобилиНовости #Новинки" in post
    assert "Тест &amp; источник" in post
    assert 'href="https://example.test/item?a=1&amp;b=2"' in post


def test_formatter_removes_service_paragraphs_and_prefers_article_text():
    news = item("Honda представила новый мотоцикл", "Короткое описание")
    news.update({
        "event_category": "motorcycles",
        "article_text": "Honda раскрыла характеристики.\n\nФото: пресс-служба\n\nМодель поступит в продажу весной.",
    })
    post = format_post(news)

    assert "Honda раскрыла характеристики." in post
    assert "Модель поступит в продажу весной." in post
    assert "Фото: пресс-служба" not in post
    assert "#Мото" in post


def test_photo_caption_stays_inside_safe_limit():
    news = item("BMW представила новый автомобиль", "word & " * 1000)
    is_relevant(news)
    assert len(format_photo_caption(news)) <= 1000


def test_autostat_extractor_keeps_only_article_paragraphs():
    soup = BeautifulSoup(
        """
        <div class="login"><p>Введите адрес электронной почты</p></div>
        <div class="text inner_content">
          <p>Первый абзац новости.</p>
          <p>Второй абзац новости.</p>
        </div>
        <footer><p>Адрес редакции</p></footer>
        """,
        "html.parser",
    )

    assert extract_autostat_article(soup) == (
        "Первый абзац новости.\n\nВторой абзац новости."
    )
