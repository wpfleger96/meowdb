from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from meowdb.api.models import MeowListResponse, MeowResponse, UpdateLabelsRequest

router = APIRouter()


def _meow_to_response(meow: dict) -> MeowResponse:  # type: ignore[type-arg]
    mp3_path = meow.get("mp3_path", "")
    wav_path = meow.get("wav_path", "")
    mp3_url = f"/audio/{meow['id']}" if mp3_path else None
    wav_url = f"/static/wav/{meow['id']}" if wav_path else None
    return MeowResponse(
        id=meow["id"],
        timestamp=meow.get("timestamp") or "",
        duration_ms=meow["duration_ms"],
        labels=meow.get("labels") or [],
        play_count=meow.get("play_count") or 0,
        created_at=meow.get("created_at") or "",
        wav_url=wav_url,
        mp3_url=mp3_url,
    )


# /meows/random MUST be registered before /{id} — see Gotcha 2 in PLAN
@router.get("/meows/random", response_model=MeowResponse)
async def get_random_meow(request: Request) -> MeowResponse:
    db = request.app.state.db
    meow = db.get_random()
    if meow is None:
        raise HTTPException(status_code=404, detail="No meows in library")
    return _meow_to_response(meow)


@router.get("/meows", response_model=MeowListResponse)
async def list_meows(
    request: Request,
    sort: str = "newest",
    label: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> MeowListResponse:
    db = request.app.state.db
    label_filter = label[0] if label else None
    rows = db.get_all(sort=sort, label_filter=label_filter, limit=limit, offset=offset)
    all_rows = db.get_all(sort=sort, label_filter=label_filter, limit=10000, offset=0)
    items = [_meow_to_response(m) for m in rows]
    return MeowListResponse(items=items, total=len(all_rows), limit=limit, offset=offset)


@router.patch("/meows/{meow_id}", response_model=MeowResponse)
async def update_meow_labels(
    meow_id: str,
    body: UpdateLabelsRequest,
    request: Request,
) -> MeowResponse:
    db = request.app.state.db
    updated = db.update_labels(meow_id, body.labels)
    if not updated:
        raise HTTPException(status_code=404, detail="Meow not found")
    meow = db.get_by_id(meow_id)
    assert meow is not None
    return _meow_to_response(meow)


@router.delete("/meows/{meow_id}", status_code=204)
async def delete_meow(meow_id: str, request: Request) -> Response:
    db = request.app.state.db
    meow = db.get_by_id(meow_id)
    if meow is None:
        raise HTTPException(status_code=404, detail="Meow not found")

    wav_path = meow.get("wav_path", "")
    mp3_path = meow.get("mp3_path", "")
    if wav_path:
        Path(wav_path).unlink(missing_ok=True)
    if mp3_path:
        Path(mp3_path).unlink(missing_ok=True)

    db.delete(meow_id)
    return Response(status_code=204)


@router.post("/meows/{meow_id}/play", status_code=204)
async def play_meow(meow_id: str, request: Request) -> Response:
    db = request.app.state.db
    db.increment_play_count(meow_id)
    return Response(status_code=204)
