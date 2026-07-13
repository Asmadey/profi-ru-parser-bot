from __future__ import annotations

from typing import Any, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from specialties import Specialty


TARGET_KEYWORD_PATTERNS = (
    re.compile(r"(?iu)\bбот\b"),
    re.compile(r"(?iu)\bбота\b"),
    re.compile(r"(?iu)\bботы\b"),
    re.compile(r"(?iu)\bботов\b"),
    re.compile(r"(?iu)\bботом\b"),
    re.compile(r"(?iu)\bботу\b"),
    re.compile(r"(?iu)\bчат[- ]?бот\b"),
    re.compile(r"(?iu)\bчат[- ]?бота\b"),
    re.compile(r"(?iu)\bchat[- ]?bot\b"),
    re.compile(r"(?iu)\bbot\b"),
    re.compile(r"(?iu)\bbots\b"),

    re.compile(r"(?iu)\bcrm\b"),
    re.compile(r"(?iu)\bcrm[- ]?систем\w*\b"),
    re.compile(r"(?iu)\bцрм\b"),
    re.compile(r"(?iu)\bцрм[- ]?систем\w*\b"),
    re.compile(r"(?iu)\bсрм\b"),
    re.compile(r"(?iu)\bсрм[- ]?систем\w*\b"),
    re.compile(r"(?iu)\bси[- ]?ар[- ]?эм\b"),

    re.compile(r"(?iu)\bпарсер\w*\b"),
    re.compile(r"(?iu)\bпарсинг\w*\b"),
    re.compile(r"(?iu)\bпарсить\b"),
    re.compile(r"(?iu)\bпарсить\w*\b"),
    re.compile(r"(?iu)\bспарс\w*\b"),
    re.compile(r"(?iu)\bраспарс\w*\b"),
    re.compile(r"(?iu)\bparser\w*\b"),
    re.compile(r"(?iu)\bparsing\b"),
    re.compile(r"(?iu)\bparse\b"),

    re.compile(r"(?iu)\bавтоматизац\w*\b"),
    re.compile(r"(?iu)\bавтоматизир\w*\b"),
    re.compile(r"(?iu)\bавтоматическ\w*\b"),
    re.compile(r"(?iu)\bautomation\b"),
    re.compile(r"(?iu)\bautomate\b"),
    re.compile(r"(?iu)\bautomated\b"),
)

DEV_KEYWORDS = (
    "разработка",
    "разработать",
    "разработчик",
    "создать",
    "создание",
    "сделать",
    "написать",
    "реализовать",
    "доработать",
    "настроить",
    "настройка",
    "внедрить",
    "внедрение",
    "интегрировать",
    "интеграция",
    "нужен",
    "нужна",
    "нужно",
    "нужны",
    "требуется",
    "требуются",
    "необходимо",
    "надо",
    "ищу",
    "заказать",
    "хочу",
)

DISALLOWED_TOPICS = (
    "таргет",
    "таргетинг",
    "таргетированная реклама",
    "контекстная реклама",
    "директ",
    "smm",
    "смм",
    "продвижение",
    "рекламная кампания",
    "специалист по рекламе",
    "настройка рекламы",
    "ведение рекламы",
)

DISALLOWED_PLATFORM_PATTERNS = (
    re.compile(r"(?iu)\binstagram\b"),
    re.compile(r"(?iu)\bинстаграм\b"),
    re.compile(r"(?iu)\binsta\b"),
    re.compile(r"(?iu)\bwhatsapp\b"),
    re.compile(r"(?iu)\bватсап\b"),
    re.compile(r"(?iu)\bfacebook\b"),
    re.compile(r"(?iu)\bdiscord\b"),
)

BUDGET_PATTERNS = (
    re.compile(r"(?iu)(?:бюджет|budget|стоимость|цена|price)\s*[:\-]?\s*(?:от|до)?\s*(\d[\d\s]{0,12})"),
    re.compile(r"(?iu)(\d[\d\s]{3,12})\s*(?:₽|руб\.?|р\b|rub\b)"),
)


def _to_text(data: Any) -> str:
    if data is None:
        return ""

    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        parts: list[str] = []

        for key in (
            "title",
            "text",
            "description",
            "details",
            "snippet",
            "category",
            "budget",
            "price",
            "amount",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
            elif isinstance(value, (int, float)):
                parts.append(str(value))

        if not parts:
            for value in data.values():
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
                elif isinstance(value, (int, float)):
                    parts.append(str(value))

        return "\n".join(parts)

    if isinstance(data, (list, tuple, set)):
        return "\n".join(_to_text(x) for x in data)

    return str(data)


def _normalize_text(text: str) -> str:
    text = (text or "").lower().replace("ё", "е").replace("\xa0", " ")
    return " ".join(text.split())


def _contains_target_keyword(text: str) -> bool:
    for rx in TARGET_KEYWORD_PATTERNS:
        if rx.search(text):
            return True
    return False


def _contains_dev_intent(text: str) -> bool:
    return any(keyword in text for keyword in DEV_KEYWORDS)


def _contains_disallowed_topics(text: str) -> bool:
    return any(keyword in text for keyword in DISALLOWED_TOPICS)


def _contains_disallowed_platforms(text: str) -> bool:
    for rx in DISALLOWED_PLATFORM_PATTERNS:
        if rx.search(text):
            return True
    return False


def _extract_budget_value(text: str) -> int | None:
    for rx in BUDGET_PATTERNS:
        match = rx.search(text)
        if not match:
            continue

        raw_value = match.group(1)
        digits = re.sub(r"[^\d]", "", raw_value)
        if not digits:
            continue

        try:
            value = int(digits)
        except ValueError:
            continue

        if value > 0:
            return value

    return None


def _budget_matches(text: str, budget_min: int = 10_000) -> bool:
    budget = _extract_budget_value(text)
    if budget is None:
        return True
    return budget >= budget_min


def order_matches_filter(data: Any, budget_min: int = 10_000) -> bool:
    """Backwards-compatible wrapper around :func:`order_matches_specialty`.

    Uses :data:`specialties.DEFAULT_SPECIALTY` (which mirrors the original
    hardcoded patterns) so existing callers see identical behaviour.

    When *budget_min* differs from the default specialty's budget_min,
    the override is applied directly to the budget check so the public
    API remains unchanged.
    """
    from specialties import DEFAULT_SPECIALTY

    text = _normalize_text(_to_text(data))

    if not text:
        return False

    if not _contains_target_keyword(text):
        return False

    if not _contains_dev_intent(text):
        return False

    if _contains_disallowed_topics(text):
        return False

    if _contains_disallowed_platforms(text):
        return False

    if not _budget_matches(text, budget_min):
        return False

    return True


# ---------------------------------------------------------------------------
# Specialty-aware filtering (multi-specialty support)
# ---------------------------------------------------------------------------

def _contains_target_keyword_for(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    for rx in patterns:
        if rx.search(text):
            return True
    return False


def _contains_dev_intent_for(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _contains_disallowed_topics_for(text: str, topics: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in topics)


def _contains_disallowed_platforms_for(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    for rx in patterns:
        if rx.search(text):
            return True
    return False


def order_matches_specialty(data: Any, specialty: "Specialty") -> bool:
    """Check whether *data* matches a single :class:`Specialty`.

    Applies the same logic as :func:`order_matches_filter` but uses the
    patterns and thresholds defined on *specialty* rather than the
    module-level constants.
    """
    text = _normalize_text(_to_text(data))

    if not text:
        return False

    if not _contains_target_keyword_for(text, specialty.target_keyword_patterns):
        return False

    if not _contains_dev_intent_for(text, specialty.dev_keywords):
        return False

    if _contains_disallowed_topics_for(text, specialty.disallowed_topics):
        return False

    if _contains_disallowed_platforms_for(text, specialty.disallowed_platform_patterns):
        return False

    if not _budget_matches(text, specialty.budget_min):
        return False

    return True


def match_specialties(data: Any, specialties: list["Specialty"]) -> list["Specialty"]:
    """Return all specialties from *specialties* that match *data*.

    This enables multi-specialty routing: an order can match more than
    one specialty (e.g. an order mentioning both ML and React would match
    both the "AI/ML" and "Web Development" specialties), and the caller
    can route notifications to each matched specialty's ``chat_id``.
    """
    return [spec for spec in specialties if order_matches_specialty(data, spec)]