from __future__ import annotations

import os
import struct
import wave
from pathlib import Path

from meowdb.db import MeowDB


def _make_wav(path: Path) -> None:
    """Write a 1-second silent mono WAV at 44100 Hz."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack("<" + "h" * 44100, *([0] * 44100)))


def _make_mp3(path: Path) -> None:
    """Write a minimal fake MP3 with an ID3 header."""
    # ID3v2.3 header: "ID3" + version 2.3 + flags 0 + syncsafe size 0
    path.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00")


def _waveform(seed: int) -> list[float]:
    return [abs(0.5 * ((j + seed) % 10 - 5) / 5) for j in range(100)]


def main() -> None:
    data_dir_env = os.environ.get("MEOWDB_DATA_DIR")
    if not data_dir_env:
        raise RuntimeError("MEOWDB_DATA_DIR environment variable is required")

    data_dir = Path(data_dir_env)
    db_path = data_dir / "meowdb.sqlite"
    wav_dir = data_dir / "audio" / "wav"
    mp3_dir = data_dir / "audio" / "mp3"

    wav_dir.mkdir(parents=True, exist_ok=True)
    mp3_dir.mkdir(parents=True, exist_ok=True)

    meows = [
        {
            "timestamp": "2026-01-01T10:00:00",
            "duration_ms": 800,
            "labels": ["happy"],
            "peak_dbfs": -8.0,
            "cat_energy_ratio": 3.1,
            "plays": 12,
        },
        {
            "timestamp": "2026-01-02T10:00:00",
            "duration_ms": 1200,
            "labels": ["hungry", "loud"],
            "peak_dbfs": -5.0,
            "cat_energy_ratio": 2.8,
            "plays": 7,
        },
        {
            "timestamp": "2026-01-03T10:00:00",
            "duration_ms": 450,
            "labels": ["happy"],
            "peak_dbfs": -12.0,
            "cat_energy_ratio": 2.2,
            "plays": 3,
        },
        {
            "timestamp": "2026-01-04T10:00:00",
            "duration_ms": 2100,
            "labels": [],
            "peak_dbfs": -15.0,
            "cat_energy_ratio": 1.8,
            "plays": 0,
        },
        {
            "timestamp": "2026-01-05T10:00:00",
            "duration_ms": 600,
            "labels": ["sleepy"],
            "peak_dbfs": -20.0,
            "cat_energy_ratio": 1.5,
            "plays": 1,
        },
    ]

    db = MeowDB(db_path)
    try:
        for i, meow in enumerate(meows):
            stem = f"meow-{i + 1:02d}"
            wav_path = wav_dir / f"{stem}.wav"
            mp3_path = mp3_dir / f"{stem}.mp3"

            _make_wav(wav_path)
            _make_mp3(mp3_path)

            meow_id = db.add(
                {
                    "timestamp": meow["timestamp"],
                    "duration_ms": meow["duration_ms"],
                    "labels": meow["labels"],
                    "wav_path": str(wav_path),
                    "mp3_path": str(mp3_path),
                    "waveform_data": _waveform(i),
                    "peak_dbfs": meow["peak_dbfs"],
                    "cat_energy_ratio": meow["cat_energy_ratio"],
                }
            )

            for _ in range(meow["plays"]):
                db.increment_play_count(meow_id)
    finally:
        db.close()

    print(f"Seeded {len(meows)} meows into {db_path}")


if __name__ == "__main__":
    main()
