from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TtsRequest:
    text: str
    lang: str
    rate: float


@dataclass(frozen=True)
class TtsResult:
    cache_key: str
    file_path: str
    mime_type: str
    cache_hit: bool


class TtsEngine:
    name: str

    def synthesize_to_file(self, *, text: str, lang: str, rate: float, out_path: str) -> None:
        raise NotImplementedError

