"""Unit tests for the specialties module."""

import pytest

import filters
from specialties import (
    Specialty,
    DEFAULT_SPECIALTY,
    load_specialties,
    _compile_patterns,
)


# Path to the example YAML file shipped with the project.
EXAMPLE_YAML = "specialties.yaml.example"


# ---------------------------------------------------------------------------
# DEFAULT_SPECIALTY
# ---------------------------------------------------------------------------

def test_default_specialty_name():
    assert DEFAULT_SPECIALTY.name == "AI/ML (default)"


def test_default_specialty_pattern_counts():
    assert len(DEFAULT_SPECIALTY.target_keyword_patterns) == 33
    assert len(DEFAULT_SPECIALTY.dev_keywords) == 26
    assert len(DEFAULT_SPECIALTY.disallowed_topics) == 12
    assert len(DEFAULT_SPECIALTY.disallowed_platform_patterns) == 7


def test_default_specialty_budget_and_chat_id():
    assert DEFAULT_SPECIALTY.budget_min == 10_000
    assert DEFAULT_SPECIALTY.chat_id is None


def test_default_specialty_mirrors_filters_constants():
    assert (
        DEFAULT_SPECIALTY.target_keyword_patterns
        == filters.TARGET_KEYWORD_PATTERNS
    )
    assert DEFAULT_SPECIALTY.dev_keywords == filters.DEV_KEYWORDS
    assert DEFAULT_SPECIALTY.disallowed_topics == filters.DISALLOWED_TOPICS
    assert (
        DEFAULT_SPECIALTY.disallowed_platform_patterns
        == filters.DISALLOWED_PLATFORM_PATTERNS
    )


# ---------------------------------------------------------------------------
# Specialty dataclass is frozen
# ---------------------------------------------------------------------------

def test_specialty_is_frozen_cannot_modify_name():
    with pytest.raises(Exception):
        DEFAULT_SPECIALTY.name = "hacked"


def test_specialty_is_frozen_cannot_modify_budget():
    with pytest.raises(Exception):
        DEFAULT_SPECIALTY.budget_min = 999


def test_specialty_default_field_values():
    spec = Specialty(name="Test")
    assert spec.target_keyword_patterns == ()
    assert spec.dev_keywords == ()
    assert spec.disallowed_topics == ()
    assert spec.disallowed_platform_patterns == ()
    assert spec.budget_min == 10_000
    assert spec.chat_id is None


# ---------------------------------------------------------------------------
# _compile_patterns
# ---------------------------------------------------------------------------

def test_compile_patterns_empty_list():
    assert _compile_patterns([]) == ()


def test_compile_patterns_none():
    assert _compile_patterns(None) == ()


def test_compile_patterns_valid():
    result = _compile_patterns([r"(?iu)\bbot\b", r"(?iu)\bcrm\b"])
    assert len(result) == 2
    assert all(hasattr(p, "search") for p in result)


def test_compile_patterns_returns_tuple():
    result = _compile_patterns([r"test"])
    assert isinstance(result, tuple)


# ---------------------------------------------------------------------------
# load_specialties
# ---------------------------------------------------------------------------

def test_load_specialties_nonexistent_path(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    result = load_specialties(str(missing))
    assert result == [DEFAULT_SPECIALTY]


def test_load_specialties_empty_file(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    result = load_specialties(str(empty))
    assert result == [DEFAULT_SPECIALTY]


def test_load_specialties_whitespace_only_file(tmp_path):
    f = tmp_path / "ws.yaml"
    f.write_text("   \n\n  \n", encoding="utf-8")
    result = load_specialties(str(f))
    assert result == [DEFAULT_SPECIALTY]


def test_load_specialties_valid_yaml_two_specialties(tmp_path):
    yaml_content = """
- name: "Bot Dev"
  target_keywords:
    - "(?iu)\\\\bбот\\\\b"
  dev_keywords:
    - разработка
    - создать
  disallowed_topics:
    - таргет
  disallowed_platforms:
    - "(?iu)\\\\binstagram\\\\b"
  budget_min: 10000
  chat_id: null

- name: "Web Dev"
  target_keywords:
    - "(?iu)\\\\breact\\\\b"
  dev_keywords:
    - разработка
  disallowed_topics: []
  disallowed_platforms:
    - "(?iu)\\\\bfacebook\\\\b"
  budget_min: 15000
  chat_id: -1001234567890
"""
    f = tmp_path / "specialties.yaml"
    f.write_text(yaml_content, encoding="utf-8")
    result = load_specialties(str(f))

    assert len(result) == 2
    assert result[0].name == "Bot Dev"
    assert result[1].name == "Web Dev"

    # First specialty details
    assert len(result[0].target_keyword_patterns) == 1
    assert result[0].dev_keywords == ("разработка", "создать")
    assert result[0].disallowed_topics == ("таргет",)
    assert len(result[0].disallowed_platform_patterns) == 1
    assert result[0].budget_min == 10000
    assert result[0].chat_id is None

    # Second specialty details
    assert result[1].budget_min == 15000
    assert result[1].chat_id == -1001234567890


def test_load_specialties_example_file():
    """The shipped specialties.yaml.example should load 3 named specialties."""
    result = load_specialties(EXAMPLE_YAML)
    assert len(result) == 3
    names = [s.name for s in result]
    assert names == ["AI/ML", "Web Development", "Data Science"]


def test_load_specialties_example_file_budget_mins():
    result = load_specialties(EXAMPLE_YAML)
    assert result[0].budget_min == 10000
    assert result[1].budget_min == 15000
    assert result[2].budget_min == 20000


def test_load_specialties_example_file_compiled_patterns():
    result = load_specialties(EXAMPLE_YAML)
    # All target_keywords should be compiled regex objects
    for spec in result:
        assert all(hasattr(p, "search") for p in spec.target_keyword_patterns)
        assert all(hasattr(p, "search") for p in spec.disallowed_platform_patterns)


def test_load_specialties_non_list_yaml_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("name: just a dict\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_specialties(str(f))


def test_load_specialties_yaml_null_returns_default(tmp_path):
    f = tmp_path / "null.yaml"
    f.write_text("~\n", encoding="utf-8")
    result = load_specialties(str(f))
    assert result == [DEFAULT_SPECIALTY]