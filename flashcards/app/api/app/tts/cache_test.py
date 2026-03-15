"""Tests for app.tts.cache."""

import os
import tempfile

from app.tts.cache import (
    CacheConfig,
    cache_key,
    cache_path,
    enforce_size_limit,
    touch,
)


def test_cache_config() -> None:
    cfg = CacheConfig(dir_path="/tmp/tts", max_bytes=1000)
    assert cfg.dir_path == "/tmp/tts"
    assert cfg.max_bytes == 1000


def test_cache_key_deterministic() -> None:
    a = cache_key("a", "b", "c")
    b = cache_key("a", "b", "c")
    assert a == b
    assert len(a) == 32
    assert all(c in "0123456789abcdef" for c in a)


def test_cache_key_different_inputs_differ() -> None:
    assert cache_key("a") != cache_key("b")
    assert cache_key("a", "b") != cache_key("ab")


def test_cache_path_sharded() -> None:
    tmp = tempfile.mkdtemp(prefix="tts_cache_test_")
    try:
        cfg = CacheConfig(dir_path=tmp, max_bytes=1000)
        key = "a" * 32
        path = cache_path(cfg, key, "wav")
        assert path.endswith(".wav")
        assert key[:4] in path or key in path
        assert os.path.isdir(os.path.dirname(path))
        assert os.path.basename(path) == f"{key}.wav"
    finally:
        for root, _, files in os.walk(tmp, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
        os.rmdir(os.path.join(tmp, key[0:2], key[2:4]))
        os.rmdir(os.path.join(tmp, key[0:2]))
        os.rmdir(tmp)


def test_cache_path_creates_dirs() -> None:
    tmp = tempfile.mkdtemp(prefix="tts_cache_test_")
    try:
        cfg = CacheConfig(dir_path=tmp, max_bytes=1000)
        key = "abcdef0123456789abcdef0123456789"
        path = cache_path(cfg, key, "mp3")
        assert os.path.isdir(os.path.dirname(path))
        assert path == os.path.join(tmp, "ab", "cd", f"{key}.mp3")
    finally:
        if os.path.isdir(tmp):
            for root, dirs, files in os.walk(tmp, topdown=False):
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            os.rmdir(tmp)


def test_touch_updates_mtime() -> None:
    fd, path = tempfile.mkstemp(prefix="tts_touch_")
    os.close(fd)
    try:
        old_mtime = os.path.getmtime(path)
        touch(path)
        new_mtime = os.path.getmtime(path)
        assert new_mtime >= old_mtime
    finally:
        os.remove(path)


def test_touch_missing_file_no_raise() -> None:
    touch("/nonexistent/path/xyz")


def test_enforce_size_limit_no_dir_no_op() -> None:
    enforce_size_limit(CacheConfig(dir_path="/nonexistent_tts_dir_12345", max_bytes=0))


def test_enforce_size_limit_under_limit_no_op() -> None:
    tmp = tempfile.mkdtemp(prefix="tts_cache_test_")
    try:
        cfg = CacheConfig(dir_path=tmp, max_bytes=10**9)
        with open(os.path.join(tmp, "f"), "w") as f:
            f.write("x")
        enforce_size_limit(cfg)
        assert os.path.exists(os.path.join(tmp, "f"))
    finally:
        os.remove(os.path.join(tmp, "f"))
        os.rmdir(tmp)


def test_enforce_size_limit_evicts_when_over() -> None:
    tmp = tempfile.mkdtemp(prefix="tts_cache_test_")
    try:
        cfg = CacheConfig(dir_path=tmp, max_bytes=10)
        p1 = os.path.join(tmp, "a")
        p2 = os.path.join(tmp, "b")
        with open(p1, "w") as f:
            f.write("x" * 20)
        with open(p2, "w") as f:
            f.write("y" * 20)
        enforce_size_limit(cfg)
        total_files = sum(1 for _ in os.listdir(tmp) if os.path.isfile(os.path.join(tmp, _)))
        assert total_files < 2
    finally:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
