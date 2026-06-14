from __future__ import annotations

from fastapi import APIRouter, Request

from meowdb.api.models import LabelResponse, StatsResponse

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(request: Request) -> StatsResponse:
    db = request.app.state.db
    data = db.get_stats()
    return StatsResponse(**data)


@router.get("/labels", response_model=list[LabelResponse])
async def get_labels(request: Request) -> list[LabelResponse]:
    db = request.app.state.db
    rows = db.get_labels()
    return [LabelResponse(**row) for row in rows]
