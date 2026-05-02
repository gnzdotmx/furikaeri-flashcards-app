"""Tests for app.cards.factory.CardFactory."""

import pytest

from app.cards.factory import (
    CardFactory,
    _first_example,
    _first_example_line_for_display,
    _split_example,
    _tags_base,
)
from app.cards.types import CardType


@pytest.fixture
def factory() -> CardFactory:
    return CardFactory()


# --- _tags_base ---


def test_tags_base_format() -> None:
    assert _tags_base("grammar", "N5", "grammar_meaning_recognition") == [
        "source:grammar",
        "level:N5",
        "type:grammar_meaning_recognition",
    ]


# --- _first_example / _split_example (helpers used by factory) ---


def test_first_example_empty_list_returns_empty() -> None:
    assert _first_example([]) == ""


def test_first_example_none_returns_empty() -> None:
    assert _first_example(None) == ""


def test_first_example_skips_empty_strings_returns_first_non_empty() -> None:
    assert _first_example(["", "  ", "valid"]) == "valid"


def test_first_example_skips_non_strings_returns_first_string() -> None:
    assert _first_example([None, 1, "ok"]) == "ok"


def test_first_example_all_falsy_returns_empty() -> None:
    assert _first_example(["", "  "]) == ""


def test_first_example_line_for_display_skips_short_fragment() -> None:
    """Short first line (e.g. 'いる。') is skipped; next example used or empty."""
    assert _first_example_line_for_display(["いる。\n\nOpposition parties."]) == ""
    assert _first_example_line_for_display(["いた。\n\nEnglish."]) == ""


def test_first_example_line_for_display_uses_second_example_when_first_fragment() -> None:
    """When first example's first line is too short, use second example's first line."""
    examples = [
        "いる。\n\nOpposition political parties are meeting.",
        "鍵が開かない。\n\nI am trying to unlock.",
    ]
    assert _first_example_line_for_display(examples) == "鍵が開かない。"


def test_first_example_line_for_display_keeps_substantial_first_line() -> None:
    """First line with >= 5 chars is used."""
    assert _first_example_line_for_display(["大切な日。\nIt is important."]) == "大切な日。"
    assert _first_example_line_for_display(["野党は来るべき選挙に向けて結束を強めようと毎日会議を開いている。\n\nOpposition."]) == "野党は来るべき選挙に向けて結束を強めようと毎日会議を開いている。"


def test_split_example_empty_or_none_returns_empty_dict() -> None:
    assert _split_example("") == {"jp": "", "romaji": "", "en": ""}
    assert _split_example(None) == {"jp": "", "romaji": "", "en": ""}


def test_split_example_one_line_sets_jp_only() -> None:
    out = _split_example("今日。")
    assert out["jp"] == "今日。"
    assert out["romaji"] == ""
    assert out["en"] == ""


def test_split_example_two_lines_sets_jp_and_romaji() -> None:
    out = _split_example("今日。\nkyou.")
    assert out["jp"] == "今日。"
    assert out["romaji"] == "kyou."
    assert out["en"] == ""


def test_split_example_three_lines_sets_all() -> None:
    out = _split_example("今日。\nkyou.\nToday.")
    assert out["jp"] == "今日。"
    assert out["romaji"] == "kyou."
    assert out["en"] == "Today."


def test_split_example_more_than_three_lines_uses_first_three() -> None:
    out = _split_example("a\nb\nc\nd\ne")
    assert out["jp"] == "a"
    assert out["romaji"] == "b"
    assert out["en"] == "c"


# --- generate_for_note ---


def test_generate_for_note_unknown_source_returns_empty(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Test",
        source_type="unknown",
        level="N5",
        note_key="x",
        fields={},
    )
    assert out == []


def test_generate_for_note_normalizes_deck_name_and_level(factory: CardFactory) -> None:
    """norm_text is applied to deck_name, level, note_key (whitespace collapsed)."""
    out = factory.generate_for_note(
        deck_name="  N5   Grammar  ",
        source_type="grammar",
        level="  N5  ",
        note_key="  x  ",
        fields={"japanese_expression": "x", "english_meaning": "y"},
    )
    assert len(out) == 1
    assert "level:N5" in out[0].tags
    assert out[0].front["expression"] == "x"


def test_grammar_generates_one_card(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Grammar",
        source_type="grammar",
        level="N5",
        note_key="だ / です",
        fields={
            "japanese_expression": "だ / です",
            "english_meaning": "to be (copula)",
            "grammar_structure": "Noun + だ",
            "examples": ["これは本だ。", "That is a book."],
        },
    )
    assert len(out) == 1
    spec = out[0]
    assert spec.card_type == CardType.GRAMMAR_MEANING_RECOGNITION
    assert "source:grammar" in spec.tags
    assert "level:N5" in spec.tags
    assert spec.front["expression"] == "だ / です"
    assert spec.front["example"] == "これは本だ。"
    assert spec.back["meaning"] == "to be (copula)"
    assert spec.back["structure"] == "Noun + だ"
    assert spec.card_id  # stable_card_id produced


def test_grammar_empty_examples_uses_note_key_for_expression(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N4",
        note_key="こと",
        fields={"english_meaning": "thing", "examples": []},
    )
    assert len(out) == 1
    assert out[0].front["expression"] == "こと"
    assert out[0].front["example"] == ""


def test_grammar_examples_not_list_treated_as_empty(factory: CardFactory) -> None:
    """When examples is not a list (e.g. string or missing), backend uses [] so ex0 is empty."""
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N5",
        note_key="x",
        fields={"japanese_expression": "x", "english_meaning": "y", "examples": "not-a-list"},
    )
    assert len(out) == 1
    assert out[0].front["example"] == ""


def test_grammar_expression_fallback_from_note_key(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N5",
        note_key="だ",
        fields={"english_meaning": "copula"},  # no japanese_expression
    )
    assert len(out) == 1
    assert out[0].front["expression"] == "だ"


def test_grammar_structure_empty_when_missing(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N5",
        note_key="x",
        fields={"japanese_expression": "x", "english_meaning": "y"},
    )
    assert out[0].back["structure"] == ""


def test_grammar_meaning_empty_when_missing(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N5",
        note_key="x",
        fields={"japanese_expression": "x"},
    )
    assert out[0].back["meaning"] == ""


def test_grammar_back_examples_capped_at_five(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N5",
        note_key="x",
        fields={
            "japanese_expression": "x",
            "english_meaning": "y",
            "examples": ["a", "b", "c", "d", "e", "f"],
        },
    )
    assert len(out[0].back["examples"]) == 5
    assert out[0].back["examples"] == ["a", "b", "c", "d", "e"]


def test_kanji_generates_reading_and_meaning_cards(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Kanji",
        source_type="kanji",
        level="N5",
        note_key="日",
        fields={
            "kanji": "日",
            "meaning": "day, sun",
            "onyomi": "ニチ, ジツ",
            "kunyomi": "ひ, か",
            "examples": [],
        },
    )
    types = [s.card_type for s in out]
    assert CardType.KANJI_READING_RECALL in types
    assert CardType.KANJI_MEANING_RECALL in types
    assert len(out) == 2  # no example sentence -> no usage card

    reading = next(s for s in out if s.card_type == CardType.KANJI_READING_RECALL)
    assert reading.front["kanji"] == "日"
    assert reading.back["onyomi"] == "ニチ, ジツ"
    assert reading.back["kunyomi"] == "ひ, か"


def test_kanji_with_example_generates_usage_card(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Kanji",
        source_type="kanji",
        level="N5",
        note_key="日",
        fields={
            "kanji": "日",
            "meaning": "day",
            "onyomi": "ニチ",
            "kunyomi": "ひ",
            "examples": ["今日はいい天気です。\nk you wa ii tenki desu.\nThe weather is nice today."],
        },
    )
    assert len(out) == 3
    usage = next(s for s in out if s.card_type == CardType.KANJI_USAGE)
    assert usage.front["sentence_jp"] == "今日はいい天気です。"
    assert usage.front["target"] == "日"
    assert "mode:usage" in usage.tags


def test_kanji_uses_note_key_when_kanji_field_missing(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Kanji",
        source_type="kanji",
        level="N5",
        note_key="水",
        fields={"meaning": "water", "onyomi": "スイ", "kunyomi": "みず"},
    )
    assert len(out) >= 2
    assert out[0].front["kanji"] == "水"
    assert out[0].back["meaning"] == "water"


def test_kanji_examples_not_list_treated_as_empty(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Kanji",
        source_type="kanji",
        level="N5",
        note_key="日",
        fields={
            "kanji": "日",
            "meaning": "day",
            "onyomi": "ニチ",
            "kunyomi": "ひ",
            "examples": "single string",
        },
    )
    assert len(out) == 2  # no usage card


def test_kanji_back_examples_capped_at_five(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Kanji",
        source_type="kanji",
        level="N5",
        note_key="日",
        fields={
            "kanji": "日",
            "meaning": "day",
            "onyomi": "ニチ",
            "kunyomi": "ひ",
            "examples": ["1", "2", "3", "4", "5", "6"],
        },
    )
    reading = next(s for s in out if s.card_type == CardType.KANJI_READING_RECALL)
    assert len(reading.back["examples"]) == 5


def test_kanji_empty_kanji_and_note_key_still_produces_cards(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Kanji",
        source_type="kanji",
        level="N5",
        note_key="",
        fields={"meaning": "m", "onyomi": "o", "kunyomi": "k"},
    )
    assert len(out) == 2
    assert out[0].front["kanji"] == ""
    assert out[0].back["meaning"] == "m"


def test_vocab_generates_meaning_reading_listening(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="N5 Vocab",
        source_type="vocabulary",
        level="N5",
        note_key="日",
        fields={
            "word": "日",
            "meaning": "day, sun",
            "reading_kana": "ひ",
            "part_of_speech": "noun",
        },
    )
    assert len(out) == 2
    types = [s.card_type for s in out]
    assert CardType.VOCAB_MEANING_RECALL in types
    assert CardType.VOCAB_READING_RECALL in types
    assert CardType.VOCAB_LISTENING not in types

    meaning_card = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert meaning_card.front["word"] == "日"
    assert meaning_card.front["reading_kana"] == "ひ"
    assert meaning_card.back["meaning"] == "day, sun"
    assert "pos:noun" in meaning_card.tags


def test_vocab_falls_back_to_note_key_for_word(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="日|ひ",
        fields={"meaning": "day", "reading_kana": "ひ"},
    )
    assert len(out) == 2
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.front["word"] == "日"


def test_vocab_word_from_kanji_word(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="k",
        fields={"kanji_word": "漢字", "meaning": "kanji", "reading_kana": "かんじ"},
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.front["word"] == "漢字"


def test_vocab_meaning_from_english_word(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="x",
        fields={"word": "日", "english_word": "day", "reading_kana": "ひ"},
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.back["meaning"] == "day"


def test_vocab_reading_from_hiragana_word(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="x",
        fields={"word": "日", "meaning": "day", "hiragana_word": "ひ"},
    )
    r = next(s for s in out if s.card_type == CardType.VOCAB_READING_RECALL)
    assert r.back["reading_kana"] == "ひ"


def test_vocab_back_includes_reading_kana_and_examples(factory: CardFactory) -> None:
    """Generic vocab import: back shows reading_kana (hiragana) and examples; front shows word and first example."""
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="important|大切|たいせつ",
        fields={
            "english_word": "important",
            "kanji_word": "大切",
            "hiragana_word": "たいせつ",
            "examples": ["大切な日。", "It is an important day."],
        },
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.back["word"] == "大切"
    assert m.back["reading_kana"] == "たいせつ"
    assert m.back["meaning"] == "important"
    assert m.back["examples"] == ["大切な日。", "It is an important day."]
    assert m.front["example"] == "大切な日。"
    r = next(s for s in out if s.card_type == CardType.VOCAB_READING_RECALL)
    assert r.front["example"] == "大切な日。"


def test_vocab_pos_with_comma_uses_first_part(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="x",
        fields={"word": "走る", "meaning": "run", "reading_kana": "はしる", "part_of_speech": "verb, godan"},
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert "pos:verb" in m.tags


def test_vocab_no_pos_omits_pos_tag(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="x",
        fields={"word": "日", "meaning": "day", "reading_kana": "ひ"},
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert not any(t.startswith("pos:") for t in m.tags)


def test_vocab_meaning_empty_when_both_missing(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="日",
        fields={"word": "日", "reading_kana": "ひ"},
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.back["meaning"] == ""
    assert m.front["example"] == ""


def test_vocab_front_example_empty_when_no_examples(factory: CardFactory) -> None:
    """When vocab has no examples, front.example is empty string."""
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="日|ひ|day",
        fields={"word": "日", "meaning": "day", "reading_kana": "ひ"},
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.front["example"] == ""


def test_vocab_front_skips_fragment_example_uses_second(factory: CardFactory) -> None:
    """When first example's first line is a fragment (e.g. 'いる。'), front uses next substantial line."""
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="開く|あく|aku",
        fields={
            "word": "開く",
            "meaning": "to open",
            "reading_kana": "あく",
            "examples": [
                "いる。\n\nOpposition political parties are meeting daily.",
                "鍵が開かない。\n\nI am trying to unlock the warehouse.",
            ],
        },
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    r = next(s for s in out if s.card_type == CardType.VOCAB_READING_RECALL)
    assert m.front["example"] == "鍵が開かない。"
    assert r.front["example"] == "鍵が開かない。"


def test_vocab_front_example_empty_when_all_fragments(factory: CardFactory) -> None:
    """When all examples have only short first lines, front.example is empty."""
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="x",
        fields={
            "word": "開く",
            "meaning": "to open",
            "reading_kana": "あく",
            "examples": ["いる。\n\nEnglish.", "した。\n\nMore English."],
        },
    )
    m = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert m.front["example"] == ""


def test_import_notes_appear_on_card_back(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N5",
        note_key="w|r|m",
        fields={
            "word": "試す",
            "meaning": "to try",
            "reading_kana": "ためす",
            "notes": "Transitive\nSame family as 試験",
        },
    )
    spec = next(s for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    assert spec.back.get("notes") == "Transitive\nSame family as 試験"


def test_grammar_labels_and_notes_on_back_and_tags(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="grammar",
        level="N5",
        note_key="だ",
        fields={
            "japanese_expression": "だ",
            "english_meaning": "to be",
            "labels": ["core"],
            "notes": "Copula",
        },
    )
    spec = out[0]
    assert "label:core" in spec.tags
    assert spec.back.get("notes") == "Copula"


def test_vocab_labels_emitted_as_label_tags(factory: CardFactory) -> None:
    out = factory.generate_for_note(
        deck_name="Deck",
        source_type="vocabulary",
        level="N3",
        note_key="word|reading|meaning",
        fields={
            "word": "食べる",
            "meaning": "to eat",
            "reading_kana": "たべる",
            "labels": ["Food", " verb ", "", None],
        },
    )
    tags_for_meaning = next(s.tags for s in out if s.card_type == CardType.VOCAB_MEANING_RECALL)
    # Base tags are source/level/type; label tags are appended
    assert "label:Food" in tags_for_meaning
    assert "label:verb" in tags_for_meaning
    # Empty/None labels must be ignored
    assert not any(t == "label:" for t in tags_for_meaning)


def test_stable_card_ids_deterministic(factory: CardFactory) -> None:
    out1 = factory.generate_for_note(
        deck_name="D",
        source_type="grammar",
        level="N5",
        note_key="x",
        fields={"japanese_expression": "x", "english_meaning": "y"},
    )
    out2 = factory.generate_for_note(
        deck_name="D",
        source_type="grammar",
        level="N5",
        note_key="x",
        fields={"japanese_expression": "x", "english_meaning": "y"},
    )
    assert out1[0].card_id == out2[0].card_id
