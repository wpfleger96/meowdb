from __future__ import annotations

import os
import subprocess

from pathlib import Path

import pytest

MEOW_FILES = [
    "/home/will/Development/meowdb/Meow 1.m4a",
    "/home/will/Development/meowdb/Meow 2.m4a",
    "/home/will/Development/meowdb/Meow 3.m4a",
    "/home/will/Development/meowdb/Meow 4.m4a",
    "/home/will/Development/meowdb/Meow 5.m4a",
]


@pytest.mark.e2e
@pytest.mark.parametrize("meow_path", MEOW_FILES)
def test_ingest_real_m4a(meow_path: str, tmp_path: Path) -> None:
    data_dir = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "meowdb", "ingest", meow_path, "--no-review"],
        env={**os.environ, "MEOWDB_DATA_DIR": data_dir},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ingest failed:\n{result.stderr}"
    mp3_dir = os.path.join(data_dir, "audio", "mp3")
    committed = (
        [f for f in os.listdir(mp3_dir) if f.endswith(".mp3")] if os.path.isdir(mp3_dir) else []
    )
    assert len(committed) > 0, f"No segments committed for {meow_path}"
