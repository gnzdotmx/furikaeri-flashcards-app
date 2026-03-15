"""Tests for app.tts.service."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.tts.service import TtsService


def test_tts_service_raises_when_engine_unavailable() -> None:
    with patch("app.tts.service.EspeakEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.available = False
        mock_engine_class.return_value = mock_engine
        svc = TtsService(cache_dir=tempfile.mkdtemp())
    with pytest.raises(RuntimeError, match="No local TTS engine"):
        svc.synthesize(text="hello", lang="en", rate=1.0)


def test_tts_service_raises_on_empty_text() -> None:
    with patch("app.tts.service.EspeakEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.available = True
        mock_engine_class.return_value = mock_engine
        tmp = tempfile.mkdtemp()
        svc = TtsService(cache_dir=tmp)
    with pytest.raises(ValueError, match="empty text"):
        svc.synthesize(text="   ", lang="en", rate=1.0)
    try:
        os.rmdir(tmp)
    except OSError:
        pass


def test_tts_service_cache_hit_returns_result() -> None:
    with patch("app.tts.service.EspeakEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.name = "espeak"
        mock_engine.available = True
        mock_engine_class.return_value = mock_engine
        tmp = tempfile.mkdtemp()
        try:
            svc = TtsService(cache_dir=tmp)
            # Pre-create a cache file so we get a cache hit (key depends on text/lang/rate)
            from app.tts.cache import cache_key, cache_path

            key = cache_key("espeak", "en", "1.00", "hello")
            path = cache_path(svc.cfg, key, "wav")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"x")
            result = svc.synthesize(text="hello", lang="en", rate=1.0)
            assert result.cache_hit is True
            assert result.file_path == path
            assert result.mime_type == "audio/wav"
            mock_engine.synthesize_to_file.assert_not_called()
        finally:
            for root, dirs, files in os.walk(tmp, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            os.rmdir(tmp)


def test_tts_service_cache_miss_calls_engine() -> None:
    with patch("app.tts.service.EspeakEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.name = "espeak"
        mock_engine.available = True
        mock_engine_class.return_value = mock_engine
        tmp = tempfile.mkdtemp()
        try:
            svc = TtsService(cache_dir=tmp)
            result = svc.synthesize(text="hello", lang="en", rate=1.0)
            assert result.cache_hit is False
            mock_engine.synthesize_to_file.assert_called_once()
            call_kw = mock_engine.synthesize_to_file.call_args[1]
            assert call_kw["text"] == "hello"
            assert call_kw["lang"] == "en"
            assert call_kw["rate"] == 1.0
            assert call_kw["out_path"].endswith(".wav")
        finally:
            for root, dirs, files in os.walk(tmp, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            try:
                os.rmdir(tmp)
            except OSError:
                pass
