"""Kanji→kana for TTS so espeak never sees kanji. Fugashi+unidic or strip fallback."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# CJK ideographs (kanji)
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")

# Bump to invalidate TTS cache when kana logic changes
TTS_KANA_CACHE_VERSION = "4"


def _katakana_to_hiragana(s: str) -> str:
    """Convert full-width katakana to hiragana (Unicode: 0x60 offset)."""
    return "".join(
        chr(ord(c) - 0x60) if "\u30A1" <= c <= "\u30F6" else c for c in s
    )


def strip_kanji(s: str) -> str:
    """Remove kanji so espeak only gets kana/punctuation. Public for TTS service."""
    return _CJK_RE.sub("", s).strip()


def has_kanji(s: str) -> bool:
    """True if string contains CJK ideographs."""
    return bool(s and _CJK_RE.search(s))


def _is_katakana_reading(s: str) -> bool:
    """True if s looks like a reading (mostly katakana, or kana)."""
    if not s or len(s) > 120:
        return False
    kana_count = 0
    for c in s:
        if "\u30A1" <= c <= "\u30F6" or "\u3041" <= c <= "\u3096" or c in "\u30FC\u30A0・":
            kana_count += 1
        elif c.isspace():
            continue
        else:
            return False
    return kana_count > 0


def _get_reading(word: object) -> str | None:
    """Get kana reading from fugashi word (UniDic .kana, tuple index, or CSV string)."""
    feature = getattr(word, "feature", None)
    if not feature:
        return None
    # Named attribute (fugashi + UniDic)
    reading = getattr(feature, "kana", None) or getattr(feature, "pron", None)
    if isinstance(reading, str) and reading.strip():
        return reading.strip()
    # Tuple/list by index (UniDic 2.x: kana/pron often around 7–9)
    if hasattr(feature, "__getitem__"):
        for idx in range(15):
            try:
                v = feature[idx]
                if isinstance(v, str) and v.strip() and _is_katakana_reading(v.strip()):
                    return v.strip()
            except (IndexError, KeyError, TypeError):
                continue
    # Raw MeCab CSV string (comma-separated columns)
    if isinstance(feature, str):
        for part in feature.split(","):
            part = part.strip()
            if part and _is_katakana_reading(part):
                return part
    return None


def japanese_to_kana(text: str) -> str:
    """
    Convert to kana-only so espeak-ng never says "Chinese character".
    Uses fugashi+unidic when available; if result still has kanji, strips them.
    """
    if not text or not text.strip():
        return text
    result: str | None = None
    try:
        import fugashi  # type: ignore
    except ImportError:
        pass
    else:
        try:
            try:
                tagger = fugashi.Tagger()
            except (AttributeError, TypeError):
                tagger = fugashi.GenericTagger()
            parts: list[str] = []
            for word in tagger(text):
                reading = _get_reading(word)
                if reading:
                    parts.append(_katakana_to_hiragana(reading))
                else:
                    surface = (getattr(word, "surface", None) or "").strip()
                    if surface and not _CJK_RE.search(surface):
                        # Particle は is pronounced "wa"; espeak reads は as "ha"
                        if surface == "は":
                            surface = "わ"
                        parts.append(surface)
            if parts:
                result = "".join(parts).strip()
        except Exception:
            logger.debug("Fugashi kana conversion fallback")
    if not result or _CJK_RE.search(result):
        result = strip_kanji(text)
    # Particle は is pronounced "wa"; espeak reads は as "ha". Replace は→わ when
    # preceded by another character (topic particle), not at start or after は (e.g. 母).
    if result:
        result = re.sub(r"(?<=[^は])は", "わ", result)
    # Never return kanji; if nothing left use space so espeak doesn't get raw kanji
    if not result:
        return " "
    return result
