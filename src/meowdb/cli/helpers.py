from __future__ import annotations

import subprocess

from pathlib import Path

from meowdb.cli.context import Context
from meowdb.config import DB_PATH
from meowdb.db import MeowDB
from meowdb.processor import MeowProcessor


def build_context(db_path: Path | None = None) -> Context:
    db = MeowDB(db_path or DB_PATH)
    processor = MeowProcessor()
    return Context(db=db, processor=processor)


def play_audio(path: Path) -> None:
    subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
        check=False,
    )


def format_duration(ms: int) -> str:
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining = int(seconds % 60)
    return f"{minutes}m {remaining:02d}s"
