"""Unit tests for the filters module."""

import pytest

import filters
from filters import (
    TARGET_KEYWORD_PATTERNS,
    DEV_KEYWORDS,
    DISALLOWED_TOPICS,
    DISALLOWED_PLATFORM_PATTERNS,
    BUDGET_PATTERNS,
    _to_text,
    _normalize_text,
    _contains_target_keyword,
    _contains_dev_intent,
    _contains_disallowed_topics,
    _contains_disallowed_platforms,
    _extract_budget_value,
    _budget_matches,
    order_matches_filter,
    order_matches_specialty,
    match_specialties,
)
from specialties import DEFAULT_SPECIALTY


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_target_keyword_patterns_is_tuple_of_compiled_regex():
    assert isinstance(TARGET_KEYWORD_PATTERNS, tuple)
    assert all(hasattr(p, "search") for p in TARGET_KEYWORD_PATTERNS)
    assert len(TARGET_KEYWORD_PATTERNS) == 33


def test_dev_keywords_is_tuple_of_strings():
    assert isinstance(DEV_KEYWORDS, tuple)
    assert all(isinstance(k, str) for k in DEV_KEYWORDS)
    assert len(DEV_KEYWORDS) == 26


def test_disallowed_topics_is_tuple_of_strings():
    assert isinstance(DISALLOWED_TOPICS, tuple)
    assert all(isinstance(k, str) for k in DISALLOWED_TOPICS)
    assert len(DISALLOWED_TOPICS) == 12


def test_disallowed_platform_patterns_is_tuple_of_compiled_regex():
    assert isinstance(DISALLOWED_PLATFORM_PATTERNS, tuple)
    assert all(hasattr(p, "search") for p in DISALLOWED_PLATFORM_PATTERNS)
    assert len(DISALLOWED_PLATFORM_PATTERNS) == 7


def test_budget_patterns_is_tuple_of_compiled_regex():
    assert isinstance(BUDGET_PATTERNS, tuple)
    assert all(hasattr(p, "search") for p in BUDGET_PATTERNS)
    assert len(BUDGET_PATTERNS) == 2


# ---------------------------------------------------------------------------
# _to_text
# ---------------------------------------------------------------------------

def test_to_text_dict_with_title_and_description():
    data = {"title": "Hello", "description": "World"}
    assert _to_text(data) == "Hello\nWorld"


def test_to_text_string():
    assert _to_text("hello") == "hello"


def test_to_text_list():
    assert _to_text(["a", "b"]) == "a\nb"


def test_to_text_none():
    assert _to_text(None) == ""


def test_to_text_empty_dict():
    assert _to_text({}) == ""


# ---------------------------------------------------------------------------
# _normalize_text
# ---------------------------------------------------------------------------

def test_normalize_text_lowercase():
    assert _normalize_text("HELLO") == "hello"


def test_normalize_text_yo_to_e():
    assert _normalize_text("Ёлка") == "елка"


def test_normalize_text_nbsp_to_space():
    assert _normalize_text("a\xa0b") == "a b"


def test_normalize_text_collapses_multiple_spaces():
    assert _normalize_text("a   b\tc") == "a b c"


# ---------------------------------------------------------------------------
# _contains_target_keyword
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "нужен бот",
    "нужен чат-бот",
    "CRM система",
    "парсер данных",
    "автоматизация",
])
def test_contains_target_keyword_positive(text):
    assert _contains_target_keyword(text) is True


@pytest.mark.parametrize("text", ["репетитор", "урок"])
def test_contains_target_keyword_negative(text):
    assert _contains_target_keyword(text) is False


# ---------------------------------------------------------------------------
# _contains_dev_intent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["разработка", "создать бота"])
def test_contains_dev_intent_positive(text):
    assert _contains_dev_intent(text) is True


def test_contains_dev_intent_negative():
    assert _contains_dev_intent("бот существует") is False


# ---------------------------------------------------------------------------
# _contains_disallowed_topics
# ---------------------------------------------------------------------------

def test_contains_disallowed_topics_targetet():
    assert _contains_disallowed_topics("таргет") is True


def test_contains_disallowed_topics_smm_lowercase():
    assert _contains_disallowed_topics("smm") is True


def test_contains_disallowed_topics_context_ads():
    assert _contains_disallowed_topics("контекстная реклама") is True


def test_contains_disallowed_topics_negative():
    assert _contains_disallowed_topics("разработка бота") is False


# ---------------------------------------------------------------------------
# _contains_disallowed_platforms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["instagram", "WhatsApp", "discord"])
def test_contains_disallowed_platforms_positive(text):
    assert _contains_disallowed_platforms(text) is True


def test_contains_disallowed_platforms_negative():
    assert _contains_disallowed_platforms("telegram бот") is False


# ---------------------------------------------------------------------------
# _extract_budget_value
# ---------------------------------------------------------------------------

def test_extract_budget_value_budget_keyword():
    assert _extract_budget_value("бюджет: 15000") == 15000


def test_extract_budget_value_ot_rub():
    assert _extract_budget_value("от 5000 ₽") == 5000


def test_extract_budget_value_rub_suffix():
    assert _extract_budget_value("20000 руб.") == 20000


def test_extract_budget_value_no_budget():
    assert _extract_budget_value("нет бюджета") is None


def test_extract_budget_value_price_keyword():
    assert _extract_budget_value("цена: 8000") == 8000


# ---------------------------------------------------------------------------
# _budget_matches
# ---------------------------------------------------------------------------

def test_budget_matches_above_threshold():
    assert _budget_matches("бюджет: 15000") is True


def test_budget_matches_below_threshold():
    assert _budget_matches("бюджет: 5000") is False


def test_budget_matches_no_budget():
    assert _budget_matches("нет бюджета") is True


def test_budget_matches_custom_threshold():
    assert _budget_matches("бюджет: 12000", budget_min=12000) is True
    assert _budget_matches("бюджет: 11999", budget_min=12000) is False


# ---------------------------------------------------------------------------
# order_matches_filter
# ---------------------------------------------------------------------------

def test_order_matches_filter_full_positive():
    data = {
        "title": "Нужен бот для автоматизации",
        "description": "разработка чат-бота, бюджет: 15000",
    }
    assert order_matches_filter(data) is True


def test_order_matches_filter_missing_keyword():
    data = {
        "title": "Нужен помощник",
        "description": "разработка, бюджет: 15000",
    }
    assert order_matches_filter(data) is False


def test_order_matches_filter_disallowed_topic():
    data = {
        "title": "Нужен бот для таргета",
        "description": "разработка, бюджет: 15000",
    }
    assert order_matches_filter(data) is False


def test_order_matches_filter_disallowed_platform():
    data = {
        "title": "Нужен бот для instagram",
        "description": "разработка, бюджет: 15000",
    }
    assert order_matches_filter(data) is False


def test_order_matches_filter_budget_too_low():
    data = {
        "title": "Нужен бот для автоматизации",
        "description": "разработка, бюджет: 5000",
    }
    assert order_matches_filter(data) is False


def test_order_matches_filter_empty_data():
    assert order_matches_filter({}) is False
    assert order_matches_filter("") is False


# ---------------------------------------------------------------------------
# order_matches_specialty with DEFAULT_SPECIALTY
# ---------------------------------------------------------------------------

def test_order_matches_specialty_positive_with_default():
    data = {
        "title": "Нужен бот для автоматизации",
        "description": "разработка чат-бота, бюджет: 15000",
    }
    assert order_matches_specialty(data, DEFAULT_SPECIALTY) is True


def test_order_matches_specialty_missing_keyword_with_default():
    data = {
        "title": "Нужен помощник",
        "description": "разработка, бюджет: 15000",
    }
    assert order_matches_specialty(data, DEFAULT_SPECIALTY) is False


def test_order_matches_specialty_disallowed_topic_with_default():
    data = {
        "title": "Нужен бот для таргета",
        "description": "разработка, бюджет: 15000",
    }
    assert order_matches_specialty(data, DEFAULT_SPECIALTY) is False


def test_order_matches_specialty_budget_too_low_with_default():
    data = {
        "title": "Нужен бот для автоматизации",
        "description": "разработка, бюджет: 5000",
    }
    assert order_matches_specialty(data, DEFAULT_SPECIALTY) is False


# ---------------------------------------------------------------------------
# match_specialties
# ---------------------------------------------------------------------------

def test_match_specialties_matching_default():
    data = {
        "title": "Нужен бот для автоматизации",
        "description": "разработка чат-бота, бюджет: 15000",
    }
    matched = match_specialties(data, [DEFAULT_SPECIALTY])
    assert len(matched) == 1
    assert matched[0].name == DEFAULT_SPECIALTY.name


def test_match_specialties_no_match():
    data = {"title": "Нужен помощник", "description": "разработка"}
    matched = match_specialties(data, [DEFAULT_SPECIALTY])
    assert matched == []


def test_match_specialties_multiple_specialties():
    """An order can match more than one specialty."""
    import re
    from specialties import Specialty

    bot_spec = Specialty(
        name="Bot Dev",
        target_keyword_patterns=(re.compile(r"(?iu)\bбот\b"),),
        dev_keywords=("разработка",),
        disallowed_topics=(),
        disallowed_platform_patterns=(),
        budget_min=10000,
    )
    parser_spec = Specialty(
        name="Parser Dev",
        target_keyword_patterns=(re.compile(r"(?iu)\bпарсер\w*\b"),),
        dev_keywords=("разработка",),
        disallowed_topics=(),
        disallowed_platform_patterns=(),
        budget_min=10000,
    )
    # Order mentioning both "бот" and "парсер"
    data = {
        "title": "Нужен бот и парсер",
        "description": "разработка, бюджет: 15000",
    }
    matched = match_specialties(data, [bot_spec, parser_spec])
    names = {s.name for s in matched}
    assert names == {"Bot Dev", "Parser Dev"}


def test_match_specialties_empty_specialties_list():
    data = {"title": "Нужен бот", "description": "разработка"}
    assert match_specialties(data, []) == []