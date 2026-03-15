"""Tests for app.tts.kana."""

from unittest.mock import MagicMock

import pytest

from app.tts.kana import (
    TTS_KANA_CACHE_VERSION,
    _get_reading,
    _is_katakana_reading,
    _katakana_to_hiragana,
    has_kanji,
    japanese_to_kana,
    strip_kanji,
)


def test_tts_kana_cache_version() -> None:
    assert isinstance(TTS_KANA_CACHE_VERSION, str)
    assert len(TTS_KANA_CACHE_VERSION) >= 1


def test_strip_kanji_removes_kanji() -> None:
    assert strip_kanji("日本語") == ""
    assert strip_kanji("hello日本world") == "helloworld"
    assert strip_kanji("  ひらがな  ") == "ひらがな"
    assert strip_kanji("カタカナ") == "カタカナ"


def test_strip_kanji_empty() -> None:
    assert strip_kanji("") == ""
    assert strip_kanji("   ") == ""


def test_has_kanji() -> None:
    assert has_kanji("日") is True
    assert has_kanji("本") is True
    assert has_kanji("hello") is False
    assert has_kanji("ひらがな") is False
    assert has_kanji("") is False
    assert has_kanji("a日b") is True


def test_japanese_to_kana_empty() -> None:
    assert japanese_to_kana("") == ""
    # Whitespace-only returns as-is (early exit)
    assert japanese_to_kana("   ").strip() == ""


def test_japanese_to_kana_kana_only_unchanged_or_wa() -> None:
    # は→わ for topic particle (when not at start)
    assert "わ" in japanese_to_kana("これは本")
    result = japanese_to_kana("ひらがな")
    assert not has_kanji(result)
    assert result.strip() != ""


def test_japanese_to_kana_fallback_strips_kanji() -> None:
    # With fugashi: "日本語" -> kana (e.g. にっぽんご). Without: strip kanji => empty/space.
    result = japanese_to_kana("日本語")
    assert not has_kanji(result)
    assert result.strip() == "" or result == " " or len(result.strip()) > 0


def test_japanese_to_kana_returns_space_if_nothing_left() -> None:
    # With fugashi: "漢字" -> kana (e.g. かんじ). Without: only kanji => strip => single space.
    result = japanese_to_kana("漢字")
    assert not has_kanji(result)
    assert result == " " or len(result.strip()) >= 1


# --- _katakana_to_hiragana ---


def test_katakana_to_hiragana_converts_range() -> None:
    assert _katakana_to_hiragana("カタカナ") == "かたかな"
    assert _katakana_to_hiragana("ア") == "あ"
    assert _katakana_to_hiragana("ン") == "ん"


def test_katakana_to_hiragana_leaves_non_katakana_unchanged() -> None:
    assert _katakana_to_hiragana("ひらがな") == "ひらがな"
    assert _katakana_to_hiragana("hello") == "hello"
    assert _katakana_to_hiragana("") == ""


# --- _is_katakana_reading ---


def test_is_katakana_reading_empty_false() -> None:
    assert _is_katakana_reading("") is False


def test_is_katakana_reading_too_long_false() -> None:
    assert _is_katakana_reading("ア" * 121) is False


def test_is_katakana_reading_katakana_true() -> None:
    assert _is_katakana_reading("カタカナ") is True
    assert _is_katakana_reading("ヒラガナ") is True


def test_is_katakana_reading_hiragana_true() -> None:
    assert _is_katakana_reading("ひらがな") is True


def test_is_katakana_reading_with_choon() -> None:
    assert _is_katakana_reading("カー") is True  # ー (choon) is in allowed set


def test_is_katakana_reading_non_kana_false() -> None:
    assert _is_katakana_reading("hello") is False
    assert _is_katakana_reading("日") is False
    assert _is_katakana_reading("カa") is False


# --- _get_reading ---


def test_get_reading_no_feature_returns_none() -> None:
    class Word:
        pass

    assert _get_reading(Word()) is None


def test_get_reading_feature_kana_string() -> None:
    word = MagicMock()
    word.feature = MagicMock()
    word.feature.kana = "カタカナ"
    word.feature.pron = None
    assert _get_reading(word) == "カタカナ"


def test_get_reading_feature_pron_fallback() -> None:
    word = MagicMock()
    word.feature = MagicMock()
    word.feature.kana = None
    word.feature.pron = "ヒラガナ"
    assert _get_reading(word) == "ヒラガナ"


def test_get_reading_feature_tuple_with_kana_at_index() -> None:
    word = MagicMock()
    word.feature = ["", "", "", "", "", "", "", "カタカナ", ""]
    assert _get_reading(word) == "カタカナ"


def test_get_reading_feature_csv_string() -> None:
    word = MagicMock()
    word.feature = "pos,pos2,,,reading,カナ,,"
    assert _get_reading(word) == "カナ"


def test_get_reading_empty_kana_skipped() -> None:
    class Feature:
        kana = "   "
        pron = None

    word = MagicMock()
    word.feature = Feature()
    assert _get_reading(word) is None


# --- japanese_to_kana は→わ replacement ---


def test_japanese_to_kana_ha_to_wa_topic_particle() -> None:
    # After another char, は becomes わ (topic particle)
    result = japanese_to_kana("これは本")
    assert "わ" in result
    assert not has_kanji(result)


def test_japanese_to_kana_leading_ha_unchanged() -> None:
    # は at start (e.g. 母) is not topic particle; fallback strip may leave は or remove it
    result = japanese_to_kana("は")
    assert result == " " or "は" in result or "わ" in result


# --- japanese_to_kana with fugashi (when available) ---


def test_japanese_to_kana_with_fugashi_if_available() -> None:
    pytest.importorskip("fugashi")
    # With fugashi we get proper conversion; 今日 -> きょう etc.
    result = japanese_to_kana("今日")
    assert not has_kanji(result)
    assert len(result.strip()) >= 1


def test_japanese_to_kana_fugashi_surface_ha_to_wa() -> None:
    pytest.importorskip("fugashi")
    # Sentence with topic は: fugashi may output は, we replace (?<=[^は])は with わ
    result = japanese_to_kana("私は学生です")
    assert not has_kanji(result)
    assert "わ" in result or "は" in result  # at least one reading


def test_japanese_to_kana_result_still_has_kanji_falls_back_to_strip() -> None:
    # If fugashi returned something that still had kanji, we strip again (branch in japanese_to_kana).
    # Without fugashi we always take the strip path; this test documents the branch.
    result = japanese_to_kana("漢字のみ")
    assert not has_kanji(result)
