from __future__ import annotations

import json
import sqlite3
import uuid

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_CREATE_MEOWS = """
CREATE TABLE IF NOT EXISTS meows (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    labels TEXT NOT NULL DEFAULT '[]',
    play_count INTEGER NOT NULL DEFAULT 0,
    last_played TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    wav_path TEXT NOT NULL,
    mp3_path TEXT NOT NULL,
    waveform_data TEXT NOT NULL DEFAULT '[]',
    peak_dbfs REAL,
    cat_energy_ratio REAL,
    ai_analysis TEXT
)
"""

_CREATE_INGEST_JOBS = """
CREATE TABLE IF NOT EXISTS ingest_jobs (
    id TEXT PRIMARY KEY,
    source_filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_INGEST_SEGMENTS = """
CREATE TABLE IF NOT EXISTS ingest_segments (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES ingest_jobs(id) ON DELETE CASCADE,
    index_in_job INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    wav_path TEXT NOT NULL,
    waveform_data TEXT NOT NULL DEFAULT '[]',
    peak_dbfs REAL,
    cat_energy_ratio REAL,
    status TEXT NOT NULL DEFAULT 'pending'
)
"""


class MeowDB:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_MEOWS)
        self._conn.execute(_CREATE_INGEST_JOBS)
        self._conn.execute(_CREATE_INGEST_SEGMENTS)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> dict:  # type: ignore[type-arg]
        d = dict(row)
        for field in ("labels", "waveform_data"):
            if field in d and isinstance(d[field], str):
                d[field] = json.loads(d[field])
        return d

    # -------------------------------------------------------------------------
    # Meow CRUD
    # -------------------------------------------------------------------------

    def add(self, metadata: dict) -> str:  # type: ignore[type-arg]
        meow_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO meows
                (id, timestamp, duration_ms, labels, wav_path, mp3_path,
                 waveform_data, peak_dbfs, cat_energy_ratio)
            VALUES
                (:id, :timestamp, :duration_ms, :labels, :wav_path, :mp3_path,
                 :waveform_data, :peak_dbfs, :cat_energy_ratio)
            """,
            {
                "id": meow_id,
                "timestamp": metadata.get("timestamp", ""),
                "duration_ms": metadata["duration_ms"],
                "labels": json.dumps(metadata.get("labels", [])),
                "wav_path": metadata["wav_path"],
                "mp3_path": metadata["mp3_path"],
                "waveform_data": json.dumps(metadata.get("waveform_data", [])),
                "peak_dbfs": metadata.get("peak_dbfs"),
                "cat_energy_ratio": metadata.get("cat_energy_ratio"),
            },
        )
        self._conn.commit()
        return meow_id

    def get_random(self) -> dict | None:  # type: ignore[type-arg]
        row = self._conn.execute("SELECT * FROM meows ORDER BY RANDOM() LIMIT 1").fetchone()
        if row is None:
            return None
        meow_id = row["id"]
        self._conn.execute(
            "UPDATE meows SET play_count = play_count + 1, last_played = datetime('now') WHERE id = ?",
            (meow_id,),
        )
        self._conn.commit()
        updated = self._conn.execute("SELECT * FROM meows WHERE id = ?", (meow_id,)).fetchone()
        return self._row_to_dict(updated)

    def get_all(
        self,
        sort: str = "newest",
        label_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:  # type: ignore[type-arg]
        # rowid tiebreaker gives stable ordering when timestamps are identical (same-second inserts)
        order = {
            "newest": "created_at DESC, rowid DESC",
            "oldest": "created_at ASC, rowid ASC",
            "most_played": "play_count DESC, rowid DESC",
            "duration_asc": "duration_ms ASC, rowid ASC",
            "duration_desc": "duration_ms DESC, rowid DESC",
        }.get(sort, "created_at DESC, rowid DESC")

        if label_filter:
            rows = self._conn.execute(
                f"SELECT * FROM meows WHERE labels LIKE ? ORDER BY {order} LIMIT ? OFFSET ?",
                (f'%"{label_filter}"%', limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"SELECT * FROM meows ORDER BY {order} LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_by_id(self, meow_id: str) -> dict | None:  # type: ignore[type-arg]
        row = self._conn.execute("SELECT * FROM meows WHERE id = ?", (meow_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def update_labels(self, meow_id: str, labels: list[str]) -> bool:
        cursor = self._conn.execute(
            "UPDATE meows SET labels = ? WHERE id = ?",
            (json.dumps(labels), meow_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, meow_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM meows WHERE id = ?", (meow_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def increment_play_count(self, meow_id: str) -> None:
        self._conn.execute(
            "UPDATE meows SET play_count = play_count + 1, last_played = datetime('now') WHERE id = ?",
            (meow_id,),
        )
        self._conn.commit()

    # -------------------------------------------------------------------------
    # Job staging
    # -------------------------------------------------------------------------

    def create_job(self, source_filename: str) -> str:
        job_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO ingest_jobs (id, source_filename) VALUES (?, ?)",
            (job_id, source_filename),
        )
        self._conn.commit()
        return job_id

    def get_job(self, job_id: str) -> dict | None:  # type: ignore[type-arg]
        row = self._conn.execute("SELECT * FROM ingest_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        if job["status"] == "ready":
            segs = self._conn.execute(
                "SELECT * FROM ingest_segments WHERE job_id = ? ORDER BY index_in_job",
                (job_id,),
            ).fetchall()
            job["segments"] = [self._row_to_dict(s) for s in segs]
        return job

    def update_job_status(self, job_id: str, status: str, error: str | None = None) -> None:
        self._conn.execute(
            "UPDATE ingest_jobs SET status = ?, error = ?, updated_at = datetime('now') WHERE id = ?",
            (status, error, job_id),
        )
        self._conn.commit()

    def add_segments(self, job_id: str, segments: list[dict]) -> None:  # type: ignore[type-arg]
        for seg in segments:
            seg_id = str(uuid.uuid4())
            self._conn.execute(
                """
                INSERT INTO ingest_segments
                    (id, job_id, index_in_job, duration_ms, wav_path, waveform_data,
                     peak_dbfs, cat_energy_ratio)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seg_id,
                    job_id,
                    seg["index"],
                    seg["duration_ms"],
                    seg["wav_path"],
                    json.dumps(seg.get("waveform_data", [])),
                    seg.get("peak_dbfs"),
                    seg.get("cat_energy_ratio"),
                ),
            )
        self._conn.commit()

    def update_segment_status(self, segment_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE ingest_segments SET status = ? WHERE id = ?",
            (status, segment_id),
        )
        self._conn.commit()

    def commit_job(
        self,
        job_id: str,
        accepted_ids: list[str],
        rejected_ids: list[str],
    ) -> list[str]:
        new_meow_ids: list[str] = []

        for seg_id in accepted_ids:
            seg_row = self._conn.execute(
                "SELECT * FROM ingest_segments WHERE id = ?", (seg_id,)
            ).fetchone()
            if seg_row is None:
                continue
            seg = self._row_to_dict(seg_row)
            meow_id = str(uuid.uuid4())
            self._conn.execute(
                """
                INSERT INTO meows
                    (id, timestamp, duration_ms, labels, wav_path, mp3_path,
                     waveform_data, peak_dbfs, cat_energy_ratio)
                VALUES
                    (:id, datetime('now'), :duration_ms, '[]', :wav_path, '',
                     :waveform_data, :peak_dbfs, :cat_energy_ratio)
                """,
                {
                    "id": meow_id,
                    "duration_ms": seg["duration_ms"],
                    "wav_path": seg["wav_path"],
                    "waveform_data": json.dumps(seg.get("waveform_data", [])),
                    "peak_dbfs": seg.get("peak_dbfs"),
                    "cat_energy_ratio": seg.get("cat_energy_ratio"),
                },
            )
            self._conn.execute(
                "UPDATE ingest_segments SET status = 'accepted' WHERE id = ?", (seg_id,)
            )
            new_meow_ids.append(meow_id)

        for seg_id in rejected_ids:
            self._conn.execute(
                "UPDATE ingest_segments SET status = 'rejected' WHERE id = ?", (seg_id,)
            )

        self._conn.execute(
            "UPDATE ingest_jobs SET status = 'committed', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
        self._conn.commit()
        return new_meow_ids

    def delete_job(self, job_id: str) -> None:
        # ON DELETE CASCADE removes segments automatically
        self._conn.execute("DELETE FROM ingest_jobs WHERE id = ?", (job_id,))
        self._conn.commit()

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def get_stats(self) -> dict:  # type: ignore[type-arg]
        agg = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total_meows,
                COALESCE(SUM(duration_ms), 0) AS total_duration_ms,
                COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
            FROM meows
            """
        ).fetchone()

        most_played = [
            self._row_to_dict(r)
            for r in self._conn.execute(
                "SELECT * FROM meows ORDER BY play_count DESC LIMIT 5"
            ).fetchall()
        ]

        recent = [
            self._row_to_dict(r)
            for r in self._conn.execute(
                "SELECT * FROM meows ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        ]

        label_rows = self._conn.execute("SELECT labels FROM meows").fetchall()
        label_counts: dict[str, int] = {}
        for row in label_rows:
            for label in json.loads(row["labels"]):
                label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "total_meows": agg["total_meows"],
            "total_duration_ms": agg["total_duration_ms"],
            "avg_duration_ms": agg["avg_duration_ms"],
            "most_played": most_played,
            "recent": recent,
            "label_counts": label_counts,
        }

    def get_labels(self) -> list[dict]:  # type: ignore[type-arg]
        label_rows = self._conn.execute("SELECT labels FROM meows").fetchall()
        counts: dict[str, int] = {}
        for row in label_rows:
            for label in json.loads(row["labels"]):
                counts[label] = counts.get(label, 0) + 1
        return [{"label": lbl, "count": cnt} for lbl, cnt in sorted(counts.items())]
