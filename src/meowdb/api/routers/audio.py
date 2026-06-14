from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

_CHUNK_SIZE = 65536


async def _stream_range(
    path: Path,
    start: int,
    end: int,
) -> AsyncGenerator[bytes]:
    with path.open("rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/audio/{meow_id}")
async def stream_audio(meow_id: str, request: Request) -> StreamingResponse:
    db = request.app.state.db
    meow = db.get_by_id(meow_id)
    if meow is None:
        raise HTTPException(status_code=404, detail="Meow not found")

    mp3_path_str = meow.get("mp3_path", "")
    if not mp3_path_str:
        raise HTTPException(status_code=404, detail="Audio file not available")

    path = Path(mp3_path_str)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        range_val = range_header.strip().removeprefix("bytes=")
        parts = range_val.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        }
        return StreamingResponse(
            _stream_range(path, start, end),
            status_code=206,
            media_type="audio/mpeg",
            headers=headers,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    return StreamingResponse(
        _stream_range(path, 0, file_size - 1),
        status_code=200,
        media_type="audio/mpeg",
        headers=headers,
    )
