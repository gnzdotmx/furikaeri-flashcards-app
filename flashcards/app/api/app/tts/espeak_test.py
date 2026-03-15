"""Tests for app.tts.espeak."""

import os
import tempfile
from unittest.mock import patch

import pytest

from app.tts.espeak import EspeakEngine


def test_espeak_available_property() -> None:
    engine = EspeakEngine()
    assert isinstance(engine.available, bool)


def test_espeak_synthesize_empty_text_raises() -> None:
    with patch("app.tts.espeak.shutil.which", return_value="/usr/bin/espeak-ng"):
        engine = EspeakEngine()
    with pytest.raises(ValueError, match="empty text"):
        engine.synthesize_to_file(text="   ", lang="en", rate=1.0, out_path="/tmp/out.wav")


def test_espeak_synthesize_no_exe_raises() -> None:
    with patch("app.tts.espeak.shutil.which", return_value=None):
        engine = EspeakEngine()
    with pytest.raises(RuntimeError, match="espeak not available"):
        engine.synthesize_to_file(text="hi", lang="en", rate=1.0, out_path="/tmp/out.wav")


def test_espeak_synthesize_to_file_sanitizes_and_calls_subprocess() -> None:
    tmp = tempfile.mkdtemp()
    out_path = os.path.join(tmp, "sub", "out.wav")
    try:
        with patch("app.tts.espeak.shutil.which", return_value="/usr/bin/espeak-ng"):
            with patch("app.tts.espeak.subprocess.run") as mock_run:
                engine = EspeakEngine()
                engine.synthesize_to_file(text="hello\x00world", lang="en", rate=1.2, out_path=out_path)
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert args[0] == "/usr/bin/espeak-ng"
                assert args[args.index("-v") + 1] == "en"
                assert "-s" in args and "-w" in args
                assert args[args.index("-w") + 1] == out_path
                text_arg = args[-1]
                assert "\x00" not in text_arg
                assert "hello" in text_arg and "world" in text_arg
    finally:
        if os.path.isdir(tmp):
            for root, dirs, files in os.walk(tmp, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            os.rmdir(tmp)


def test_espeak_synthesize_ja_voice() -> None:
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "x.wav")
    try:
        with patch("app.tts.espeak.shutil.which", return_value="/usr/bin/espeak-ng"):
            with patch("app.tts.espeak.subprocess.run") as mock_run:
                engine = EspeakEngine()
                engine.synthesize_to_file(text="ひ", lang="ja", rate=1.0, out_path=out)
                args = mock_run.call_args[0][0]
                assert args[args.index("-v") + 1] == "ja"
    finally:
        if os.path.isdir(tmp):
            for r, d, f in os.walk(tmp, topdown=False):
                for x in f:
                    os.remove(os.path.join(r, x))
                for x in d:
                    os.rmdir(os.path.join(r, x))
            os.rmdir(tmp)


def test_espeak_name() -> None:
    assert EspeakEngine.name == "espeak"
