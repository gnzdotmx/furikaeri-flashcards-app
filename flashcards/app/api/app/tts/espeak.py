from __future__ import annotations

import os
import shutil
import subprocess

from .strategy import TtsEngine


class EspeakEngine(TtsEngine):
    """
    Offline TTS via espeak-ng (or espeak).
    Produces WAV output.
    """

    name = "espeak"

    def __init__(self) -> None:
        self._exe = shutil.which("espeak-ng") or shutil.which("espeak")

    @property
    def available(self) -> bool:
        return bool(self._exe)

    def synthesize_to_file(self, *, text: str, lang: str, rate: float, out_path: str) -> None:
        if not self._exe:
            raise RuntimeError("espeak not available")

        # Basic sanitization: strip NULs/control chars
        text = "".join(ch for ch in text if ch >= " " and ch != "\x7f")
        text = text.strip()
        if not text:
            raise ValueError("empty text")

        # Map BCP-47 to espeak-ish lang codes (best-effort)
        voice = "ja"
        if lang.lower().startswith("en"):
            voice = "en"

        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # espeak rate: 80..450-ish words per minute; approximate from our 0.8/1.0/1.2 selector.
        base_wpm = 175
        wpm = int(max(80, min(300, base_wpm * float(rate))))

        # Use argv list (no shell) for safety.
        cmd = [self._exe, "-v", voice, "-s", str(wpm), "-w", out_path, text]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

