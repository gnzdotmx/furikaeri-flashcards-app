"""Tests for app.cards.types."""

import uuid

import pytest

from app.cards.types import CARD_ID_NAMESPACE, CardSpec, CardType, json_dumps, stable_card_id


def test_stable_card_id_is_deterministic() -> None:
    a = stable_card_id("deck", "grammar", "N5", "だ")
    b = stable_card_id("deck", "grammar", "N5", "だ")
    assert a == b


def test_stable_card_id_different_parts_differ() -> None:
    a = stable_card_id("deck", "grammar", "N5", "だ")
    b = stable_card_id("deck", "grammar", "N5", "です")
    assert a != b


def test_stable_card_id_is_uuid5_string() -> None:
    out = stable_card_id("a", "b")
    parsed = uuid.UUID(out)
    assert parsed.version == 5
    assert out == str(parsed)


def test_stable_card_id_uses_namespace() -> None:
    name = "deck|grammar|N5|x"
    expected = str(uuid.uuid5(CARD_ID_NAMESPACE, name))
    assert stable_card_id("deck", "grammar", "N5", "x") == expected


def test_stable_card_id_single_part() -> None:
    out = stable_card_id("only")
    assert out == str(uuid.uuid5(CARD_ID_NAMESPACE, "only"))


def test_card_spec_has_required_fields() -> None:
    spec = CardSpec(
        card_id="id",
        card_type=CardType.GRAMMAR_MEANING_RECOGNITION,
        tags=["a"],
        front={"expression": "だ"},
        back={"meaning": "to be"},
    )
    assert spec.card_id == "id"
    assert spec.card_type == CardType.GRAMMAR_MEANING_RECOGNITION
    assert spec.tags == ["a"]
    assert spec.front == {"expression": "だ"}
    assert spec.back == {"meaning": "to be"}


def test_card_spec_is_frozen() -> None:
    spec = CardSpec(
        card_id="id",
        card_type="t",
        tags=[],
        front={},
        back={},
    )
    with pytest.raises(AttributeError):
        spec.card_id = "other"  # type: ignore[misc]


def test_card_type_constants() -> None:
    assert CardType.GRAMMAR_MEANING_RECOGNITION == "grammar_meaning_recognition"
    assert CardType.KANJI_READING_RECALL == "kanji_reading_recall"
    assert CardType.VOCAB_LISTENING == "vocab_listening"


def test_card_type_all_constants_defined() -> None:
    """Cover all CardType constants so the class body is fully executed."""
    assert CardType.GRAMMAR_MEANING_RECOGNITION == "grammar_meaning_recognition"
    assert CardType.GRAMMAR_STRUCTURE_PRODUCTION == "grammar_structure_production"
    assert CardType.GRAMMAR_CLOZE == "grammar_cloze"
    assert CardType.KANJI_READING_RECALL == "kanji_reading_recall"
    assert CardType.KANJI_MEANING_RECALL == "kanji_meaning_recall"
    assert CardType.KANJI_USAGE == "kanji_usage"
    assert CardType.VOCAB_MEANING_RECALL == "vocab_meaning_recall"
    assert CardType.VOCAB_READING_RECALL == "vocab_reading_recall"
    assert CardType.VOCAB_LISTENING == "vocab_listening"


def test_json_dumps_preserves_unicode() -> None:
    out = json_dumps({"word": "日", "reading": "ひ"})
    assert "日" in out
    assert "ひ" in out
    assert out == '{"word":"日","reading":"ひ"}'


def test_json_dumps_compact_separators() -> None:
    out = json_dumps({"a": 1, "b": 2})
    assert " " not in out
    assert out == '{"a":1,"b":2}'


def test_json_dumps_list() -> None:
    out = json_dumps([1, 2, "x"])
    assert out == '[1,2,"x"]'


def test_json_dumps_empty_containers() -> None:
    assert json_dumps({}) == "{}"
    assert json_dumps([]) == "[]"


def test_json_dumps_nested() -> None:
    out = json_dumps({"key": [1, {"nested": "v"}]})
    assert out == '{"key":[1,{"nested":"v"}]}'


def test_card_spec_equality() -> None:
    a = CardSpec(
        card_id="id",
        card_type=CardType.VOCAB_MEANING_RECALL,
        tags=[],
        front={},
        back={},
    )
    b = CardSpec(card_id="id", card_type=CardType.VOCAB_MEANING_RECALL, tags=[], front={}, back={})
    assert a == b


def test_card_spec_repr() -> None:
    spec = CardSpec(
        card_id="x",
        card_type=CardType.KANJI_USAGE,
        tags=["t"],
        front={"f": 1},
        back={"b": 2},
    )
    r = repr(spec)
    assert "CardSpec" in r
    assert "x" in r


def test_stable_card_id_three_parts() -> None:
    out = stable_card_id("a", "b", "c")
    assert out == str(uuid.uuid5(CARD_ID_NAMESPACE, "a|b|c"))
