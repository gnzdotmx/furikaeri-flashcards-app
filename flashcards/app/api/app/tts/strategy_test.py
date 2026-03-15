"""Tests for app.tts.strategy."""

import pytest

from app.tts.strategy import TtsEngine, TtsRequest, TtsResult


def test_tts_request() -> None:
    r = TtsRequest(text="hello", lang="en", rate=1.0)
    assert r.text == "hello"
    assert r.lang == "en"
    assert r.rate == 1.0


def test_tts_result() -> None:
    r = TtsResult(cache_key="k", file_path="/p/x.wav", mime_type="audio/wav", cache_hit=True)
    assert r.cache_key == "k"
    assert r.file_path == "/p/x.wav"
    assert r.mime_type == "audio/wav"
    assert r.cache_hit is True


def test_tts_engine_synthesize_not_implemented() -> None:
    class StubEngine(TtsEngine):
        pass

    engine = StubEngine()
    with pytest.raises(NotImplementedError):
        engine.synthesize_to_file(text="x", lang="en", rate=1.0, out_path="/tmp/out.wav")
