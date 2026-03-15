"""Tests for app.imports.adapters."""

import csv
from io import StringIO
from pathlib import Path

import pytest

from app.imports.adapters import (
    GenericKanjiCsvAdapter,
    GenericVocabularyCsvAdapter,
    GenericVocabularyCsvAdapterWordReadingMeaning,
    GrammarCsvAdapter,
    ImportItem,
    KanjiCsvAdapter,
    VocabularyCsvAdapter,
    encode_fields_json,
)


# --- ImportItem ---


def test_import_item_creation() -> None:
    item = ImportItem(
        source_type="grammar",
        level="N5",
        key="だ",
        fields={"japanese_expression": "だ", "english_meaning": "to be"},
    )
    assert item.source_type == "grammar"
    assert item.level == "N5"
    assert item.key == "だ"
    assert item.fields["english_meaning"] == "to be"
    assert item.source_url is None


def test_import_item_source_url_optional() -> None:
    item = ImportItem(
        source_type="kanji",
        level="N5",
        key="日",
        fields={},
        source_url="https://example.com",
    )
    assert item.source_url == "https://example.com"


# --- encode_fields_json ---


def test_encode_fields_json_unicode() -> None:
    out = encode_fields_json({"word": "日", "reading": "ひ"})
    assert "日" in out
    assert "ひ" in out


def test_encode_fields_json_compact() -> None:
    out = encode_fields_json({"a": 1, "b": 2})
    assert " " not in out
    assert out == '{"a":1,"b":2}'


# --- GrammarCsvAdapter ---


def _grammar_reader(csv_text: str) -> csv.DictReader:
    return csv.DictReader(StringIO(csv_text, newline=""))


def test_grammar_adapter_missing_required_columns_raises() -> None:
    data = "japanese_expression\nだ\n"
    reader = _grammar_reader(data)
    with pytest.raises(ValueError, match="Missing required columns:.*english_meaning"):
        list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))


def test_grammar_adapter_one_valid_row() -> None:
    data = "japanese_expression,english_meaning,grammar_structure\nだ,to be,Noun + だ\n"
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    assert items[0].source_type == "grammar"
    assert items[0].level == "N5"
    assert items[0].key == "だ"
    assert items[0].fields["japanese_expression"] == "だ"
    assert items[0].fields["english_meaning"] == "to be"
    assert items[0].fields["grammar_structure"] == "Noun + だ"
    assert items[0].fields["examples"] == []


def test_grammar_adapter_empty_expression_skipped() -> None:
    data = "japanese_expression,english_meaning\n,to be\n"
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 0


def test_grammar_adapter_empty_meaning_skipped() -> None:
    data = "japanese_expression,english_meaning\nだ,\n"
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 0


def test_grammar_adapter_example_columns_collected() -> None:
    data = "japanese_expression,english_meaning,example_1,example_2\nだ,to be,これは本だ。,That is a book.\n"
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))
    assert items[0].fields["examples"] == ["これは本だ。", "That is a book."]


def test_grammar_adapter_labels_column_parsed_and_normalized() -> None:
    # labels column is a single CSV cell; extra comma-separated values beyond the column
    # become DictReader's "extra columns" and are not part of labels.
    data = "japanese_expression,english_meaning,labels\nだ,to be,formal; polite, extra \n"
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    labels = items[0].fields["labels"]
    assert labels == ["formal", "polite"]


def test_grammar_adapter_norm_text_applied() -> None:
    data = "japanese_expression,english_meaning\n  だ  ,  to be  \n"
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader))
    assert items[0].fields["japanese_expression"] == "だ"
    assert items[0].fields["english_meaning"] == "to be"


def test_grammar_adapter_too_many_rows_raises() -> None:
    header = "japanese_expression,english_meaning\n"
    rows = "だ,to be\n" * 3
    reader = _grammar_reader(header + rows)
    with pytest.raises(ValueError, match="Too many rows"):
        list(GrammarCsvAdapter().iter_items(level="N5", reader=reader, max_rows=2))


def test_grammar_adapter_n3_style() -> None:
    """N3-style CSV: japanese_expression, english_meaning, grammar_structure, example_1..example_5."""
    data = (
        "japanese_expression,english_meaning,grammar_structure,example_1,example_2,example_3,example_4,example_5\n"
        "上げる(ageru),to finish doing ~,\"Meaning: to finish. Level: N3.\","
        "Ex1 line1.,Ex2.,Ex3.,Ex4.,Ex5.\n"
    )
    reader = _grammar_reader(data)
    items = list(GrammarCsvAdapter().iter_items(level="N3", reader=reader))
    assert len(items) == 1
    assert items[0].level == "N3"
    assert items[0].key == "上げる(ageru)"
    assert items[0].fields["japanese_expression"] == "上げる(ageru)"
    assert items[0].fields["english_meaning"] == "to finish doing ~"
    assert "N3" in items[0].fields["grammar_structure"]
    assert len(items[0].fields["examples"]) == 5
    assert items[0].fields["examples"][0] == "Ex1 line1."
    assert items[0].fields["examples"][4] == "Ex5."


def _find_data_jlptsensei_root() -> Path | None:
    """Walk up from this file until we find a directory containing data/jlptsensei."""
    p = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = p / "data" / "jlptsensei"
        if candidate.is_dir():
            return p
        if p.parent == p:
            return None
        p = p.parent
    return None


def test_grammar_adapter_jlpt_n3_file_if_present() -> None:
    """If data/jlptsensei/jlpt_N3_grammar.csv exists, parse it with GrammarCsvAdapter."""
    repo_root = _find_data_jlptsensei_root()
    if repo_root is None:
        pytest.skip("data/jlptsensei not found (run from repo root or set up data)")
    csv_path = repo_root / "data" / "jlptsensei" / "jlpt_N3_grammar.csv"
    if not csv_path.is_file():
        pytest.skip("data/jlptsensei/jlpt_N3_grammar.csv not found")
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        items = list(GrammarCsvAdapter().iter_items(level="N3", reader=reader, max_rows=5000))
    assert len(items) >= 1
    first = items[0]
    assert first.source_type == "grammar"
    assert first.level == "N3"
    assert first.key
    assert "japanese_expression" in first.fields
    assert "english_meaning" in first.fields
    assert "examples" in first.fields


# --- KanjiCsvAdapter ---


def _kanji_reader(csv_text: str) -> csv.DictReader:
    return csv.DictReader(StringIO(csv_text, newline=""))


def test_kanji_adapter_missing_required_columns_raises() -> None:
    data = "kanji\n日\n"
    reader = _kanji_reader(data)
    with pytest.raises(ValueError, match="Missing required columns:.*meaning"):
        list(KanjiCsvAdapter().iter_items(level="N5", reader=reader))


def test_kanji_adapter_one_valid_row() -> None:
    data = "kanji,meaning,onyomi,kunyomi,rank\n日,day sun,ニチ,ひ,1\n"
    reader = _kanji_reader(data)
    items = list(KanjiCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    assert items[0].source_type == "kanji"
    assert items[0].key == "日"
    assert items[0].fields["kanji"] == "日"
    assert items[0].fields["meaning"] == "day sun"
    assert items[0].fields["onyomi"] == "ニチ"
    assert items[0].fields["kunyomi"] == "ひ"
    assert items[0].source_url is None


def test_kanji_adapter_empty_kanji_skipped() -> None:
    data = "kanji,meaning\n,day\n"
    reader = _kanji_reader(data)
    items = list(KanjiCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 0


def test_kanji_adapter_source_url_not_processed() -> None:
    """Kanji adapter does not read source_url from CSV; item.source_url is always None."""
    data = "kanji,meaning,source_url\n日,day,https://example.com\n"
    reader = _kanji_reader(data)
    items = list(KanjiCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    assert items[0].source_url is None


def test_kanji_adapter_jlpt_n3_file_if_present() -> None:
    """If data/jlptsensei/jlpt_N3_kanji.csv exists, parse it with KanjiCsvAdapter; all rows must be presented."""
    repo_root = _find_data_jlptsensei_root()
    if repo_root is None:
        pytest.skip("data/jlptsensei not found (run from repo root or set up data)")
    csv_path = repo_root / "data" / "jlptsensei" / "jlpt_N3_kanji.csv"
    if not csv_path.is_file():
        pytest.skip("data/jlptsensei/jlpt_N3_kanji.csv not found")
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        items = list(KanjiCsvAdapter().iter_items(level="N3", reader=reader, max_rows=500))
    assert len(items) >= 1, "expected at least one kanji from N3 file"
    # File has 100 kanji; all must have kanji and meaning (no row skipped for missing required)
    with open(csv_path, encoding="utf-8", newline="") as f:
        row_count = sum(1 for _ in csv.DictReader(f))
    assert len(items) == row_count, f"every row must be imported: got {len(items)} items for {row_count} rows"
    first = items[0]
    assert first.source_type == "kanji"
    assert first.level == "N3"
    assert first.key
    assert "kanji" in first.fields
    assert "meaning" in first.fields
    assert "onyomi" in first.fields
    assert "kunyomi" in first.fields
    assert "examples" in first.fields
    # CardFactory must generate cards for each item (no crash on multiline examples / comma in onyomi)
    from app.cards.factory import CardFactory

    factory = CardFactory()
    for item in items:
        cards = factory.generate_for_note(
            deck_name="N3 Kanji",
            source_type="kanji",
            level=item.level,
            note_key=item.key,
            fields=item.fields,
        )
        assert len(cards) >= 2, f"kanji {item.key} must yield at least reading+meaning cards"
    # Spot-check one with multiline example and comma in onyomi (e.g. 連 or 対)
    kanji_with_examples = next((i for i in items if i.fields.get("examples")), None)
    if kanji_with_examples:
        ex0 = kanji_with_examples.fields["examples"][0]
        assert "\n" in ex0, "example should preserve newlines for jp/romaji/en split"
        specs = factory.generate_for_note(
            deck_name="N3",
            source_type="kanji",
            level=kanji_with_examples.level,
            note_key=kanji_with_examples.key,
            fields=kanji_with_examples.fields,
        )
        usage_cards = [s for s in specs if s.card_type == "kanji_usage"]
        assert len(usage_cards) == 1, "one usage card when first example has jp line"
        assert usage_cards[0].front.get("sentence_jp")
        assert usage_cards[0].back.get("meaning") is not None


# --- VocabularyCsvAdapter ---


def _vocab_reader(csv_text: str) -> csv.DictReader:
    return csv.DictReader(StringIO(csv_text, newline=""))


def test_vocab_adapter_missing_required_columns_raises() -> None:
    data = "word\n日\n"
    reader = _vocab_reader(data)
    with pytest.raises(ValueError, match="Missing required columns:.*meaning"):
        list(VocabularyCsvAdapter().iter_items(level="N5", reader=reader))


def test_vocab_adapter_one_valid_row() -> None:
    data = "word,meaning,reading_kana,reading_romaji,part_of_speech,rank,source_url\n日,day,ひ,hi,noun,1,\n"
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    assert items[0].source_type == "vocabulary"
    assert items[0].key == "日|ひ|day"
    assert items[0].fields["word"] == "日"
    assert items[0].fields["meaning"] == "day"
    assert items[0].fields["reading_kana"] == "ひ"
    assert items[0].fields["reading_romaji"] == "hi"
    assert items[0].fields["part_of_speech"] == "noun"


def test_vocab_adapter_empty_word_skipped() -> None:
    data = "word,meaning\n,day\n"
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 0


def test_vocab_adapter_swaps_word_and_rank_when_word_is_numeric() -> None:
    # CSV with column order word,rank,reading_kana,... (e.g. 9 in word column for 部分)
    data = "word,rank,reading_kana,reading_romaji,part_of_speech,meaning,source_url\n9,部分,ぶぶん,bubun,Noun,portion; section; part,\n"
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N3", reader=reader))
    assert len(items) == 1
    assert items[0].fields["word"] == "部分"
    assert items[0].fields["reading_kana"] == "ぶぶん"
    assert items[0].fields["part_of_speech"] == "Noun"
    assert items[0].key == "部分|ぶぶん|portion; section; part"


def test_vocab_adapter_skips_row_when_word_stays_numeric() -> None:
    # No rank column or word is numeric and can't swap -> skip row so rank never appears on cards
    data = "word,reading_kana,meaning\n2,あける,to dawn\n"
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N3", reader=reader))
    assert len(items) == 0


def test_vocab_adapter_clears_numeric_part_of_speech() -> None:
    # part_of_speech that is purely numeric (e.g. column shift) is cleared so it never shows as badge
    data = "rank,word,reading_kana,reading_romaji,part_of_speech,meaning,source_url\n1,日,ひ,hi,2,day,\n"
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    assert items[0].fields["part_of_speech"] == ""


def test_vocab_adapter_header_based_example_columns_collected() -> None:
    """When header-based vocab CSV has example_1, example_2, etc., they are in fields['examples'] for GUI."""
    data = (
        "rank,word,reading_kana,reading_romaji,part_of_speech,meaning,example_1,example_2,source_url\n"
        "1,明かり,あかり,akari,Noun,light,あかりがつく。,The light turns on.,\n"
    )
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N3", reader=reader))
    assert len(items) == 1
    assert items[0].fields["word"] == "明かり"
    assert "examples" in items[0].fields
    assert items[0].fields["examples"] == ["あかりがつく。", "The light turns on."]


def test_vocab_adapter_header_based_no_example_columns_empty_list() -> None:
    """Vocab CSV without example_1, example_2, ... columns has examples=[]."""
    data = "rank,word,reading_kana,reading_romaji,part_of_speech,meaning\n1,明かり,あかり,akari,Noun,light\n"
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N3", reader=reader))
    assert len(items) == 1
    assert items[0].fields["examples"] == []


def test_vocab_adapter_extra_example_columns_like_grammar() -> None:
    """After meaning, example_1, example_2, example_3, example_4, ... are all collected (same as grammar)."""
    data = (
        "rank,word,reading_kana,reading_romaji,part_of_speech,meaning,example_1,example_2,example_3,example_4\n"
        "1,日,ひ,hi,Noun,day,今日。,明日。,毎日。,良い日。\n"
    )
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    assert items[0].fields["examples"] == ["今日。", "明日。", "毎日。", "良い日。"]


def test_vocab_adapter_labels_column_parsed_and_normalized() -> None:
    data = (
        "rank,word,reading_kana,reading_romaji,part_of_speech,labels,meaning\n"
        "1,食べる,たべる,taberu,Verb,food; verb ,to eat\n"
    )
    reader = _vocab_reader(data)
    items = list(VocabularyCsvAdapter().iter_items(level="N5", reader=reader))
    assert len(items) == 1
    labels = items[0].fields["labels"]
    assert labels == ["food", "verb"]


# --- GenericKanjiCsvAdapter ---


def test_generic_kanji_adapter_one_row() -> None:
    adapter = GenericKanjiCsvAdapter()
    rows = [["日", "day sun", "ニチ", "ひ", "今日。", "kyou."]]
    items = list(adapter.iter_items(level="N5", rows=rows))
    assert len(items) == 1
    assert items[0].source_type == "kanji"
    assert items[0].key == "日"
    assert items[0].fields["kanji"] == "日"
    assert items[0].fields["meaning"] == "day sun"
    assert items[0].fields["onyomi"] == "ニチ"
    assert items[0].fields["kunyomi"] == "ひ"
    assert items[0].fields["examples"] == ["今日。", "kyou."]


def test_generic_kanji_adapter_short_row_skipped() -> None:
    adapter = GenericKanjiCsvAdapter()
    items = list(adapter.iter_items(level="N5", rows=[["日"]]))
    assert len(items) == 0


def test_generic_kanji_adapter_minimal_two_cols() -> None:
    adapter = GenericKanjiCsvAdapter()
    items = list(adapter.iter_items(level="N5", rows=[["日", "day"]]))
    assert len(items) == 1
    assert items[0].fields["onyomi"] == ""
    assert items[0].fields["kunyomi"] == ""
    assert items[0].fields["examples"] == []


# --- GenericVocabularyCsvAdapter ---


def test_generic_vocab_adapter_one_row() -> None:
    adapter = GenericVocabularyCsvAdapter()
    rows = [["day", "日", "ひ", "今日はいい天気。"]]
    items = list(adapter.iter_items(level="N5", rows=rows))
    assert len(items) == 1
    assert items[0].source_type == "vocabulary"
    assert items[0].key == "day|日|ひ"
    assert items[0].fields["english_word"] == "day"
    assert items[0].fields["kanji_word"] == "日"
    assert items[0].fields["hiragana_word"] == "ひ"
    assert items[0].fields["examples"] == ["今日はいい天気。"]


def test_generic_vocab_adapter_english_required_kanji_or_hira() -> None:
    adapter = GenericVocabularyCsvAdapter()
    items = list(adapter.iter_items(level="N5", rows=[["day", "", ""]]))
    assert len(items) == 0
    items = list(adapter.iter_items(level="N5", rows=[["", "日", "ひ"]]))
    assert len(items) == 0
    items = list(adapter.iter_items(level="N5", rows=[["day", "日", ""]]))
    assert len(items) == 1
    items = list(adapter.iter_items(level="N5", rows=[["day", "", "ひ"]]))
    assert len(items) == 1


def test_generic_vocab_adapter_columns_abc_de_examples() -> None:
    """Format: A=English, B=Kanji, C=Hiragana, D=example1, E=example2, ..."""
    adapter = GenericVocabularyCsvAdapter()
    # Row: A=English, B=Kanji, C=Hiragana, D=ex1, E=ex2
    rows = [["important", "大切", "たいせつ", "大切な日", "It is an important day."]]
    items = list(adapter.iter_items(level="N5", rows=rows))
    assert len(items) == 1
    assert items[0].fields["english_word"] == "important"
    assert items[0].fields["kanji_word"] == "大切"
    assert items[0].fields["hiragana_word"] == "たいせつ"
    assert items[0].fields["examples"] == ["大切な日", "It is an important day."]
    assert items[0].key == "important|大切|たいせつ"


def test_generic_vocab_adapter_short_row_skipped() -> None:
    adapter = GenericVocabularyCsvAdapter()
    items = list(adapter.iter_items(level="N5", rows=[["a", "b"]]))
    assert len(items) == 0


# --- GenericVocabularyCsvAdapterWordReadingMeaning ---


def test_generic_vocab_word_reading_meaning_one_row() -> None:
    adapter = GenericVocabularyCsvAdapterWordReadingMeaning()
    rows = [["日", "ひ", "day", "今日はいい天気。"]]
    items = list(adapter.iter_items(level="N5", rows=rows))
    assert len(items) == 1
    assert items[0].key == "日|ひ|day"
    assert items[0].fields["kanji_word"] == "日"
    assert items[0].fields["hiragana_word"] == "ひ"
    assert items[0].fields["english_word"] == "day"
    assert items[0].fields["meaning"] == "day"
    assert items[0].fields["examples"] == ["今日はいい天気。"]


def test_generic_vocab_word_reading_meaning_word_fallback_from_reading() -> None:
    adapter = GenericVocabularyCsvAdapterWordReadingMeaning()
    # When word (col0) is empty, it uses reading (col1).
    rows = [["", "ひ", "day"]]
    items = list(adapter.iter_items(level="N5", rows=rows))
    assert len(items) == 1
    assert items[0].fields["kanji_word"] == "ひ"
    assert items[0].fields["hiragana_word"] == "ひ"


def test_generic_vocab_word_reading_meaning_meaning_required() -> None:
    adapter = GenericVocabularyCsvAdapterWordReadingMeaning()
    items = list(adapter.iter_items(level="N5", rows=[["日", "ひ", ""]]))
    assert len(items) == 0


# --- max_cell_chars (validate_row_limits) ---


def test_grammar_adapter_cell_too_large_raises() -> None:
    data = "japanese_expression,english_meaning\n" + "x," + ("y" * 30) + "\n"
    reader = _grammar_reader(data)
    with pytest.raises(ValueError, match="Cell too large"):
        list(GrammarCsvAdapter().iter_items(level="N5", reader=reader, max_cell_chars=20))


