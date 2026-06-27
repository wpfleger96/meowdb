from __future__ import annotations

import json
import zipfile

from datetime import date
from pathlib import Path

import click

from meowdb.cli.helpers import build_context
from meowdb.cli.options import db_path_option
from meowdb.display import print_success, print_warning

_MANIFEST_PATH = "meowdb-export/manifest.json"
_AUDIO_PREFIX = "meowdb-export/audio/"
_FORMAT_VERSION = 1

_PORTABLE_FIELDS = {
    "id", "timestamp", "duration_ms", "labels", "play_count", "last_played",
    "created_at", "waveform_data", "peak_dbfs", "cat_energy_ratio",
    "recorded_at", "title", "upvote_count", "downvote_count",
}


@click.command(name="export")
@click.argument("output", type=click.Path(dir_okay=False), default=None, required=False)
@db_path_option
def export_meows(output: str | None, db_path: str | None) -> None:
    """Export the meow library to a portable zip archive."""
    ctx = build_context(Path(db_path) if db_path else None)
    meows = ctx.db.get_all_for_export()
    ctx.db.close()

    out_path = Path(output) if output else Path(f"meowdb-export-{date.today()}.zip")

    exported = 0
    skipped = 0
    manifest_meows = []

    with zipfile.ZipFile(out_path, "w") as zf:
        for meow in meows:
            wav_path = Path(meow.get("wav_path") or "")
            if not wav_path.exists():
                print_warning(f"Missing WAV for {meow['id'][:8]}, skipping")
                skipped += 1
                continue

            zf.write(wav_path, _AUDIO_PREFIX + meow["id"] + ".wav", compress_type=zipfile.ZIP_STORED)
            manifest_meows.append({k: v for k, v in meow.items() if k in _PORTABLE_FIELDS})
            exported += 1

        manifest = {
            "format_version": _FORMAT_VERSION,
            "meow_count": exported,
            "meows": manifest_meows,
        }
        zf.writestr(
            zipfile.ZipInfo(_MANIFEST_PATH),
            json.dumps(manifest, indent=2),
            compress_type=zipfile.ZIP_DEFLATED,
        )

    if skipped:
        print_warning(f"Skipped {skipped} meow(s) with missing WAV files")
    print_success(f"Exported {exported} meow(s) to {out_path}")
