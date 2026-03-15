from __future__ import annotations

import os
import unicodedata

from .cache import CacheConfig, cache_key, cache_path, enforce_size_limit, touch
from .espeak import EspeakEngine
from .kana import TTS_KANA_CACHE_VERSION, has_kanji, japanese_to_kana, strip_kanji
from .strategy import TtsResult


def _normalize_text(s: str) -> str:
    """Normalize so cache hits on repeated play."""
    return unicodedata.normalize("NFKC", s.strip())


class TtsService:
    def __init__(self, *, cache_dir: str, max_cache_bytes: int = 200 * 1024 * 1024) -> None:
        self.cfg = CacheConfig(dir_path=cache_dir, max_bytes=max_cache_bytes)
        self.engine = EspeakEngine()

    def synthesize(self, *, text: str, lang: str, rate: float) -> TtsResult:
        if not self.engine.available:
            raise RuntimeError("No local TTS engine available in this build.")

        text = _normalize_text(text)
        if not text:
            raise ValueError("empty text after normalize")

        os.makedirs(self.cfg.dir_path, exist_ok=True)
        enforce_size_limit(self.cfg)

        # Include kana version for Japanese so cache invalidates when kana logic changes
        key_parts = [self.engine.name, lang, f"{rate:.2f}", text]
        if lang.lower().startswith("ja"):
            key_parts.append(TTS_KANA_CACHE_VERSION)
        key = cache_key(*key_parts)
        out = cache_path(self.cfg, key, "wav")
        if os.path.exists(out) and os.path.getsize(out) > 0:
            touch(out)
            return TtsResult(cache_key=key, file_path=out, mime_type="audio/wav", cache_hit=True)

        # Japanese: convert to kana so espeak doesn't read kanji
        tts_input = text
        if lang.lower().startswith("ja"):
            tts_input = japanese_to_kana(text)
            if has_kanji(tts_input) or not tts_input.strip():
                tts_input = strip_kanji(text) or " "
        self.engine.synthesize_to_file(text=tts_input, lang=lang, rate=rate, out_path=out)
        enforce_size_limit(self.cfg)
        return TtsResult(cache_key=key, file_path=out, mime_type="audio/wav", cache_hit=False)

