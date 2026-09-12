from datetime import datetime, timedelta, timezone

from collectors.normalizer import normalize_date


def test_normalize_date_preserves_datetime():
    value = datetime(2026, 8, 25, 10, 52, 47, tzinfo=timezone.utc)

    assert normalize_date(value) is value


def test_normalize_date_parses_rfc_date():
    result = normalize_date("Tue, 25 Aug 2026 10:52:47 +0000")

    assert result == datetime(2026, 8, 25, 10, 52, 47, tzinfo=timezone.utc)


def test_normalize_date_parses_iso_utc_date():
    result = normalize_date("2026-08-25T10:52:47Z")

    assert result == datetime(2026, 8, 25, 10, 52, 47, tzinfo=timezone.utc)


def test_normalize_date_parses_iso_utc_date_with_milliseconds():
    result = normalize_date("2026-08-25T10:52:47.035Z")

    assert result == datetime(
        2026,
        8,
        25,
        10,
        52,
        47,
        35000,
        tzinfo=timezone.utc,
    )


def test_normalize_date_parses_iso_date_with_offset():
    result = normalize_date("2026-08-25T13:52:47+03:00")

    assert result == datetime(
        2026,
        8,
        25,
        13,
        52,
        47,
        tzinfo=timezone(timedelta(hours=3)),
    )


def test_normalize_date_rejects_invalid_value():
    assert normalize_date("not-a-date") is None
