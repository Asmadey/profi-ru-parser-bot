"""Multi-specialty support for the Profi.ru order parser bot.

A *specialty* is a named set of filter rules (keyword patterns, dev-intent
keywords, disallowed topics/platforms, minimum budget, and an optional
chat_id for routing). Multiple specialties can be loaded from a YAML file
and applied to each parsed order, enabling routing of different categories
of orders to different Telegram chats.

Usage
-----
    from specialties import load_specialties
    from filters import match_specialties

    specialties = load_specialties("specialties.yaml")
    matched = match_specialties(order_data, specialties)
    for spec in matched:
        print(spec.name, spec.chat_id)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a runtime dependency
    yaml = None  # type: ignore[assignment]

# Import the current hardcoded patterns from filters so the default
# specialty is always in sync with them.
from filters import (
    TARGET_KEYWORD_PATTERNS,
    DEV_KEYWORDS,
    DISALLOWED_TOPICS,
    DISALLOWED_PLATFORM_PATTERNS,
)


@dataclass(frozen=True)
class Specialty:
    """A named set of filter rules for matching Profi.ru orders.

    Attributes
    ----------
    name:
        Human-readable identifier, e.g. ``"AI/ML"``.
    target_keyword_patterns:
        Tuple of compiled regex patterns. The order text must contain at
        least one match for the order to be considered.
    dev_keywords:
        Tuple of plain-string keywords indicating development intent.
    disallowed_topics:
        Tuple of plain-string keywords that, if present, reject the order
        (e.g. marketing/advertising topics).
    disallowed_platform_patterns:
        Tuple of compiled regex patterns for platforms that disqualify
        the order (e.g. Instagram, WhatsApp).
    budget_min:
        Minimum budget in rubles. Orders with an explicit budget below
        this value are rejected. If no budget is detected the order
        passes this check.
    chat_id:
        Optional Telegram chat ID for routing matched orders to a
        dedicated chat. ``None`` means "use the default chat".
    """

    name: str
    target_keyword_patterns: tuple[re.Pattern[str], ...] = ()
    dev_keywords: tuple[str, ...] = ()
    disallowed_topics: tuple[str, ...] = ()
    disallowed_platform_patterns: tuple[re.Pattern[str], ...] = ()
    budget_min: int = 10_000
    chat_id: int | None = None


# ---------------------------------------------------------------------------
# Default specialty — mirrors the original hardcoded filters.py patterns.
# ---------------------------------------------------------------------------

DEFAULT_SPECIALTY: Specialty = Specialty(
    name="AI/ML (default)",
    target_keyword_patterns=TARGET_KEYWORD_PATTERNS,
    dev_keywords=DEV_KEYWORDS,
    disallowed_topics=DISALLOWED_TOPICS,
    disallowed_platform_patterns=DISALLOWED_PLATFORM_PATTERNS,
    budget_min=10_000,
    chat_id=None,
)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

def _compile_patterns(pattern_strings: list[str] | None) -> tuple[re.Pattern[str], ...]:
    """Compile a list of regex strings into a tuple of compiled patterns."""
    if not pattern_strings:
        return ()
    return tuple(re.compile(p) for p in pattern_strings)


def _specialty_from_dict(data: dict[str, Any]) -> Specialty:
    """Build a :class:`Specialty` from a parsed YAML dict."""
    return Specialty(
        name=str(data.get("name", "unnamed")),
        target_keyword_patterns=_compile_patterns(data.get("target_keywords")),
        dev_keywords=tuple(data.get("dev_keywords") or ()),
        disallowed_topics=tuple(data.get("disallowed_topics") or ()),
        disallowed_platform_patterns=_compile_patterns(data.get("disallowed_platforms")),
        budget_min=int(data.get("budget_min", 10_000)),
        chat_id=data.get("chat_id"),
    )


def load_specialties(path: str) -> list[Specialty]:
    """Load a list of specialties from a YAML file.

    The YAML file should contain a top-level list of mappings, each with
    the following keys (see :class:`Specialty`):

    .. code-block:: yaml

        - name: AI/ML
          target_keywords:
            - "(?iu)\\bbot\\b"
          dev_keywords:
            - разработка
          disallowed_topics:
            - таргет
          disallowed_platforms:
            - "(?iu)\\binstagram\\b"
          budget_min: 10000
          chat_id: null

    If *path* does not exist or is empty, ``[DEFAULT_SPECIALTY]`` is
    returned so the bot continues to operate with the original
    hardcoded filters.
    """
    file_path = Path(path)
    if not file_path.exists():
        return [DEFAULT_SPECIALTY]

    if yaml is None:
        raise ImportError(
            "PyYAML is required to load specialty files. "
            "Install it with: pip install pyyaml"
        )

    raw = file_path.read_text(encoding="utf-8").strip()
    if not raw:
        return [DEFAULT_SPECIALTY]

    parsed = yaml.safe_load(raw)
    if parsed is None:
        return [DEFAULT_SPECIALTY]

    if not isinstance(parsed, list):
        raise ValueError(
            f"Expected a YAML list of specialties in {path!r}, "
            f"got {type(parsed).__name__}"
        )

    specialties: list[Specialty] = []
    for i, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Specialty #{i} in {path!r} is not a mapping "
                f"(got {type(entry).__name__})"
            )
        specialties.append(_specialty_from_dict(entry))

    if not specialties:
        return [DEFAULT_SPECIALTY]

    return specialties