from __future__ import annotations

import struct
import wave

from collections.abc import Generator
from pathlib import Path

import pytest

from click.testing import CliRunner

from meowdb.db import MeowDB


@pytest.fixture
def tmp_db(tmp_path: Path) -> Generator[MeowDB]:
    db = MeowDB(tmp_path / "test.sqlite")
    yield db
    db.close()


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def silent_wav_bytes() -> bytes:
    import io

    sample_rate = 44100
    num_channels = 1
    sample_width = 2
    num_frames = sample_rate

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * num_frames, *([0] * num_frames)))

    return buf.getvalue()
