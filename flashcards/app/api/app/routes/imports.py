"""CSV import: grammar, kanji, vocabulary, sync."""

import csv

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..auth import get_current_user_id
from ..db import connection
from ..imports.adapters import (
    GrammarCsvAdapter,
    KanjiCsvAdapter,
    VocabularyCsvAdapter,
)
from ..imports.service import import_items_into_deck, sync_items_into_deck
from ..imports.utils import decode_upload, norm_text, sniff_dialect
from ..settings import Settings, get_settings
from ..study_config import get_study_config

router = APIRouter()


def _parse_import_items(
    *,
    source_type: str,
    format: str,
    level: str,
    sio,
    dialect,
    has_header: bool,
    max_rows: int,
    max_cell_chars: int,
) -> list:
    """Parse CSV to ImportItems (grammar/kanji/vocabulary)."""
    if source_type == "grammar":
        reader = csv.DictReader(sio, dialect=dialect)
        adapter = GrammarCsvAdapter()
        return list(adapter.iter_items(level=level, reader=reader, max_rows=max_rows, max_cell_chars=max_cell_chars))
    if source_type == "kanji":
        reader = csv.DictReader(sio, dialect=dialect)
        adapter = KanjiCsvAdapter()
        return list(adapter.iter_items(level=level, reader=reader, max_rows=max_rows, max_cell_chars=max_cell_chars))
    if source_type == "vocabulary":
        reader = csv.DictReader(sio, dialect=dialect)
        adapter = VocabularyCsvAdapter()
        return list(adapter.iter_items(level=level, reader=reader, max_rows=max_rows, max_cell_chars=max_cell_chars))
    raise ValueError("source_type must be grammar|kanji|vocabulary")


@router.post("/imports/sync")
async def import_sync(
    deck_id: str = Form(...),
    level: str = Form(...),
    source_type: str = Form(...),
    format: str = Form(...),
    merge_existing: str = Form("skip"),
    has_header: bool = Form(True),
    max_rows: int | None = Form(None),
    max_cell_chars: int | None = Form(None),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    """Sync CSV to existing deck; new rows only or merge_examples for existing."""
    level = norm_text(level)
    if len(level) > 16:
        raise HTTPException(status_code=400, detail="level too long")
    if len(deck_id) > 80:
        raise HTTPException(status_code=400, detail="deck_id too long")
    if source_type not in ("grammar", "kanji", "vocabulary"):
        raise HTTPException(status_code=400, detail="source_type must be grammar|kanji|vocabulary")
    if merge_existing not in ("skip", "merge_examples"):
        raise HTTPException(status_code=400, detail="merge_existing must be skip|merge_examples")

    imp_cfg = get_study_config().import_
    max_rows_val = int(max_rows) if max_rows is not None else imp_cfg.max_rows_default
    max_cell_chars_val = int(max_cell_chars) if max_cell_chars is not None else imp_cfg.max_cell_chars_default

    data = await file.read()
    if len(data) > settings.csv_upload_max_bytes:
        raise HTTPException(status_code=400, detail="CSV file too large")
    try:
        sio = decode_upload(data)
        sample = sio.getvalue()[:4096]
        sio.seek(0)
        dialect = sniff_dialect(sample)
        items = _parse_import_items(
            source_type=source_type,
            format=format,
            level=level,
            sio=sio,
            dialect=dialect,
            has_header=has_header,
            max_rows=max_rows_val,
            max_cell_chars=max_cell_chars_val,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    with connection(settings.sqlite_path) as conn:
        conn.execute("BEGIN;")
        try:
            result = sync_items_into_deck(
                conn=conn,
                deck_id=deck_id,
                level=level,
                source_type=source_type,
                items=items,
                merge_existing=merge_existing,
            )
            conn.execute("COMMIT;")
        except ValueError as e:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=400, detail=str(e)) from e

    return {"ok": True, **result}


@router.post("/imports/grammar")
async def import_grammar(
    level: str = Form(...),
    deck_name: str | None = Form(None),
    merge_policy: str = Form("overwrite"),
    max_rows: int | None = Form(None),
    max_cell_chars: int | None = Form(None),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    imp_cfg = get_study_config().import_
    max_rows_val = int(max_rows) if max_rows is not None else imp_cfg.max_rows_default
    max_cell_chars_val = int(max_cell_chars) if max_cell_chars is not None else imp_cfg.max_cell_chars_default
    level = norm_text(level)
    if len(level) > 16:
        raise HTTPException(status_code=400, detail="level too long")
    data = await file.read()
    if len(data) > settings.csv_upload_max_bytes:
        raise HTTPException(status_code=400, detail="CSV file too large")
    try:
        sio = decode_upload(data)
        sample = sio.getvalue()[:4096]
        sio.seek(0)
        dialect = sniff_dialect(sample)
        reader = csv.DictReader(sio, dialect=dialect)
        adapter = GrammarCsvAdapter()
        items = list(adapter.iter_items(level=level, reader=reader, max_rows=max_rows_val, max_cell_chars=max_cell_chars_val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not deck_name:
        deck_name = f"{level} Grammar"

    with connection(settings.sqlite_path) as conn:
        conn.execute("BEGIN;")
        try:
            result = import_items_into_deck(
                conn=conn,
                level=level,
                deck_name=deck_name,
                source_type="grammar",
                items=items,
                merge_policy=merge_policy,
            )
            conn.execute("COMMIT;")
        except Exception as e:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=400, detail=str(e)) from e

    return {"ok": True, **result}


@router.post("/imports/kanji")
async def import_kanji(
    level: str = Form(...),
    deck_name: str | None = Form(None),
    merge_policy: str = Form("overwrite"),
    max_rows: int | None = Form(None),
    max_cell_chars: int | None = Form(None),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    imp_cfg = get_study_config().import_
    max_rows_val = int(max_rows) if max_rows is not None else imp_cfg.max_rows_default
    max_cell_chars_val = int(max_cell_chars) if max_cell_chars is not None else imp_cfg.max_cell_chars_default
    level = norm_text(level)
    if len(level) > 16:
        raise HTTPException(status_code=400, detail="level too long")
    data = await file.read()
    if len(data) > settings.csv_upload_max_bytes:
        raise HTTPException(status_code=400, detail="CSV file too large")
    try:
        sio = decode_upload(data)
        sample = sio.getvalue()[:4096]
        sio.seek(0)
        dialect = sniff_dialect(sample)
        reader = csv.DictReader(sio, dialect=dialect)
        adapter = KanjiCsvAdapter()
        items = list(adapter.iter_items(level=level, reader=reader, max_rows=max_rows_val, max_cell_chars=max_cell_chars_val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not deck_name:
        deck_name = f"{level} Kanji"

    with connection(settings.sqlite_path) as conn:
        conn.execute("BEGIN;")
        try:
            result = import_items_into_deck(
                conn=conn,
                level=level,
                deck_name=deck_name,
                source_type="kanji",
                items=items,
                merge_policy=merge_policy,
            )
            conn.execute("COMMIT;")
        except Exception as e:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=400, detail=str(e)) from e

    return {"ok": True, **result}


@router.post("/imports/vocabulary")
async def import_vocabulary(
    level: str = Form(...),
    deck_name: str | None = Form(None),
    merge_policy: str = Form("overwrite"),
    max_rows: int | None = Form(None),
    max_cell_chars: int | None = Form(None),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    imp_cfg = get_study_config().import_
    max_rows_val = int(max_rows) if max_rows is not None else imp_cfg.max_rows_default
    max_cell_chars_val = int(max_cell_chars) if max_cell_chars is not None else imp_cfg.max_cell_chars_default
    level = norm_text(level)
    if len(level) > 16:
        raise HTTPException(status_code=400, detail="level too long")

    data = await file.read()
    if len(data) > settings.csv_upload_max_bytes:
        raise HTTPException(status_code=400, detail="CSV file too large")
    try:
        sio = decode_upload(data)
        sample = sio.getvalue()[:4096]
        sio.seek(0)
        dialect = sniff_dialect(sample)
        reader = csv.DictReader(sio, dialect=dialect)
        adapter = VocabularyCsvAdapter()
        items = list(adapter.iter_items(level=level, reader=reader, max_rows=max_rows_val, max_cell_chars=max_cell_chars_val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not deck_name:
        deck_name = f"{level} Vocabulary"

    with connection(settings.sqlite_path) as conn:
        conn.execute("BEGIN;")
        try:
            result = import_items_into_deck(
                conn=conn,
                level=level,
                deck_name=deck_name,
                source_type="vocabulary",
                items=items,
                merge_policy=merge_policy,
            )
            conn.execute("COMMIT;")
        except Exception as e:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=400, detail=str(e)) from e

    return {"ok": True, **result}
