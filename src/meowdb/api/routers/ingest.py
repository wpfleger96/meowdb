from __future__ import annotations

import shutil

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from meowdb.api.models import (
    CommitRequest,
    CommitResponse,
    IngestJobResponse,
    IngestSegmentResponse,
)
from meowdb.config import DB_PATH, MP3_DIR, STAGING_DIR, WAV_DIR

router = APIRouter()

_CHUNK_SIZE = 65536


def _seg_to_response(seg: dict, job_id: str) -> IngestSegmentResponse:  # type: ignore[type-arg]
    return IngestSegmentResponse(
        id=seg["id"],
        index=seg["index_in_job"],
        duration_ms=seg["duration_ms"],
        url=f"/api/ingest/{job_id}/audio/{seg['id']}",
        waveform=seg.get("waveform_data") or [],
        status=seg.get("status") or "pending",
    )


def _job_to_response(job: dict) -> IngestJobResponse:  # type: ignore[type-arg]
    segments = None
    if job.get("segments"):
        segments = [_seg_to_response(s, job["id"]) for s in job["segments"]]
    return IngestJobResponse(
        job_id=job["id"],
        status=job["status"],
        segments=segments,
        source_filename=job.get("source_filename"),
        error=job.get("error"),
    )


def _run_processor(db_path: Path, job_id: str, source_path: Path, staging_dir: Path) -> None:
    from meowdb.db import MeowDB
    from meowdb.processor import MeowProcessor

    db = MeowDB(db_path)
    try:
        processor = MeowProcessor()
        result = processor.process_file(source_path, staging_dir=staging_dir)

        segment_dicts = [
            {
                "index": seg.index,
                "duration_ms": seg.duration_ms,
                "wav_path": str(seg.wav_path) if seg.wav_path else "",
                "waveform_data": seg.waveform_data,
                "peak_dbfs": seg.peak_dbfs,
                "cat_energy_ratio": seg.cat_energy_ratio,
            }
            for seg in result.segments
        ]
        db.add_segments(job_id, segment_dicts)
        db.update_job_status(job_id, "ready")
    except Exception as exc:
        db.update_job_status(job_id, "failed", error=str(exc))
    finally:
        db.close()


@router.post("/ingest", response_model=IngestJobResponse, status_code=202)
async def create_ingest_job(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile,
) -> IngestJobResponse:
    db = request.app.state.db

    source_filename = file.filename or "upload"
    job_id = db.create_job(source_filename)

    job_staging_dir = STAGING_DIR / job_id
    job_staging_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(source_filename).suffix or ".audio"
    temp_path = job_staging_dir / f"source{suffix}"
    content = await file.read()
    temp_path.write_bytes(content)

    background_tasks.add_task(
        _run_processor,
        DB_PATH,
        job_id,
        temp_path,
        job_staging_dir,
    )

    return IngestJobResponse(
        job_id=job_id,
        status="processing",
        source_filename=source_filename,
    )


@router.get("/ingest/{job_id}", response_model=IngestJobResponse)
async def get_ingest_job(job_id: str, request: Request) -> IngestJobResponse:
    db = request.app.state.db
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


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


@router.get("/ingest/{job_id}/audio/{segment_id}")
async def stream_segment_audio(
    job_id: str,
    segment_id: str,
    request: Request,
) -> StreamingResponse:
    db = request.app.state.db
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Locate any audio file matching the segment — look for mp3 first, then wav
    seg_row = None
    conn = db._conn
    row = conn.execute(
        "SELECT * FROM ingest_segments WHERE id = ? AND job_id = ?",
        (segment_id, job_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    seg_row = dict(row)

    wav_path_str = seg_row.get("wav_path", "")
    if not wav_path_str:
        raise HTTPException(status_code=404, detail="Segment audio not available")

    # Serve MP3 if it exists alongside WAV, else fall back to WAV
    wav_path = Path(wav_path_str)
    mp3_path = wav_path.with_suffix(".mp3")
    if mp3_path.exists():
        serve_path = mp3_path
        media_type = "audio/mpeg"
    elif wav_path.exists():
        serve_path = wav_path
        media_type = "audio/wav"
    else:
        raise HTTPException(status_code=404, detail="Segment audio file not found on disk")

    file_size = serve_path.stat().st_size
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
            _stream_range(serve_path, start, end),
            status_code=206,
            media_type=media_type,
            headers=headers,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    return StreamingResponse(
        _stream_range(serve_path, 0, file_size - 1),
        status_code=200,
        media_type=media_type,
        headers=headers,
    )


@router.post("/ingest/{job_id}/commit", response_model=CommitResponse)
async def commit_ingest_job(
    job_id: str,
    body: CommitRequest,
    request: Request,
) -> CommitResponse:
    db = request.app.state.db
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Move accepted segment WAV files from staging → library
    conn = db._conn
    for seg_id in body.accepted_ids:
        row = conn.execute(
            "SELECT * FROM ingest_segments WHERE id = ? AND job_id = ?",
            (seg_id, job_id),
        ).fetchone()
        if row is None:
            continue
        seg = dict(row)
        wav_src = Path(seg.get("wav_path", ""))
        if wav_src.exists():
            wav_dest = WAV_DIR / wav_src.name
            WAV_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(wav_src), str(wav_dest))
            conn.execute(
                "UPDATE ingest_segments SET wav_path = ? WHERE id = ?",
                (str(wav_dest), seg_id),
            )
            mp3_src = wav_src.with_suffix(".mp3")
            if mp3_src.exists():
                mp3_dest = MP3_DIR / mp3_src.name
                MP3_DIR.mkdir(parents=True, exist_ok=True)
                shutil.move(str(mp3_src), str(mp3_dest))
    conn.commit()

    meow_ids = db.commit_job(job_id, body.accepted_ids, body.rejected_ids)

    # Update mp3_path for committed meows
    for meow_id in meow_ids:
        meow = db.get_by_id(meow_id)
        if meow:
            wav_p = Path(meow.get("wav_path", ""))
            mp3_p = MP3_DIR / wav_p.with_suffix(".mp3").name
            if mp3_p.exists():
                conn.execute(
                    "UPDATE meows SET mp3_path = ? WHERE id = ?",
                    (str(mp3_p), meow_id),
                )
    conn.commit()

    # Clean up rejected staging files
    for seg_id in body.rejected_ids:
        row = conn.execute(
            "SELECT wav_path FROM ingest_segments WHERE id = ?", (seg_id,)
        ).fetchone()
        if row:
            wav_p = Path(row["wav_path"] if row["wav_path"] else "")
            if wav_p.exists():
                wav_p.unlink(missing_ok=True)
            mp3_p = wav_p.with_suffix(".mp3")
            if mp3_p.exists():
                mp3_p.unlink(missing_ok=True)

    # Clean up staging directory if empty
    job_staging_dir = STAGING_DIR / job_id
    if job_staging_dir.exists():
        shutil.rmtree(str(job_staging_dir), ignore_errors=True)

    return CommitResponse(meow_ids=meow_ids, rejected_count=len(body.rejected_ids))


@router.delete("/ingest/{job_id}", status_code=204)
async def delete_ingest_job(job_id: str, request: Request) -> None:
    db = request.app.state.db
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job_staging_dir = STAGING_DIR / job_id
    if job_staging_dir.exists():
        shutil.rmtree(str(job_staging_dir), ignore_errors=True)

    db.delete_job(job_id)
