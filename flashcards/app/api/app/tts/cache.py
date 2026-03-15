from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CacheConfig:
    dir_path: str
    max_bytes: int = 200 * 1024 * 1024  # 200MB


def cache_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:32]


def cache_path(cfg: CacheConfig, key: str, ext: str) -> str:
    # shard to avoid huge directories
    p = Path(cfg.dir_path) / key[0:2] / key[2:4]
    p.mkdir(parents=True, exist_ok=True)
    return str(p / f"{key}.{ext}")


def _dir_size_bytes(root: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                continue
    return total


def enforce_size_limit(cfg: CacheConfig) -> None:
    """Evict oldest files by mtime when cache exceeds max_bytes."""
    root = cfg.dir_path
    if not os.path.isdir(root):
        return
    total = _dir_size_bytes(root)
    if total <= cfg.max_bytes:
        return

    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
                files.append((st.st_mtime, st.st_size, path))
            except OSError:
                continue
    files.sort()  # oldest first

    target = int(cfg.max_bytes * 0.85)
    for _, size, path in files:
        try:
            os.remove(path)
            total -= int(size)
        except OSError:
            continue
        if total <= target:
            break


def touch(path: str) -> None:
    try:
        now = time.time()
        os.utime(path, (now, now))
    except OSError:
        pass

