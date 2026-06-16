from __future__ import annotations

import time

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from meowdb.api.auth import require_auth
from meowdb.api.models import RecalculateResponse
from meowdb.similarity import MeowSimilarity

router = APIRouter()

_similarity = MeowSimilarity()


def _run_recalculate(db: Any) -> int:
    """Extract any missing fingerprints, recompute all uniqueness scores."""
    all_rows = db.get_all_wav_paths()
    existing_fps = db.get_all_fingerprints()

    updated = 0
    for row in all_rows:
        meow_id = row["id"]
        if meow_id not in existing_fps:
            try:
                fp = _similarity.extract_fingerprint(Path(row["wav_path"]))
                db.update_fingerprint(meow_id, fp)
                existing_fps[meow_id] = fp
                updated += 1
            except Exception:
                pass

    if existing_fps:
        scores = _similarity.compute_uniqueness_scores(existing_fps)
        db.update_uniqueness_scores_bulk(scores)

    return updated


@router.post("/uniqueness/recalculate", response_model=RecalculateResponse)
async def recalculate_uniqueness(
    request: Request,
    _: None = Depends(require_auth),
) -> RecalculateResponse:
    """Recompute MFCC fingerprints (for any missing) and all uniqueness scores."""
    db = request.app.state.db
    t0 = time.monotonic()
    updated_count = await run_in_threadpool(_run_recalculate, db)
    return RecalculateResponse(
        updated_count=updated_count,
        elapsed_seconds=round(time.monotonic() - t0, 2),
    )
