"""Text-to-speech and kana conversion endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..settings import Settings, get_settings
from ..tts.kana import japanese_to_kana
from ..tts.service import TtsService

router = APIRouter()


class TtsReq(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    lang: str = Field(default="ja-JP", max_length=16)
    rate: float = Field(default=1.0, ge=0.6, le=1.4)


@router.get("/tts/to-kana")
def tts_to_kana(text: str = "", lang: str = "ja-JP"):
    """
    Return kana-only version of text (for browser TTS: correct は→わ, no kanji).
    No DB, no cache. Used when "Natural voice" uses browser speech.
    """
    if not text or len(text) > 500:
        raise HTTPException(status_code=400, detail="text required, max 500 chars")
    text = text.strip()
    if lang.lower().startswith("ja"):
        kana = japanese_to_kana(text)
    else:
        kana = text
    return {"kana": kana}


@router.post("/tts")
def tts(req: TtsReq, settings: Settings = Depends(get_settings)):
    """
    Generate (or fetch cached) audio for a short piece of text.
    Returns a URL to stream the cached file.
    No DB access so TTS never blocks on or causes "database is locked".
    """
    svc = TtsService(cache_dir=settings.audio_cache_dir)
    result = svc.synthesize(text=req.text, lang=req.lang, rate=req.rate)
    return {
        "cache_key": result.cache_key,
        "cache_hit": result.cache_hit,
        "mime_type": result.mime_type,
        "url": f"/audio/{result.cache_key[0:2]}/{result.cache_key[2:4]}/{result.cache_key}.wav",
    }
