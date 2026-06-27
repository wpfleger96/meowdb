from __future__ import annotations

import json
import sys
import uuid
import zipfile

from pathlib import Path

import click

from pydub import AudioSegment

from meowdb.cli.helpers import build_context
from meowdb.cli.options import db_path_option
from meowdb.config import MP3_DIR, WAV_DIR
from meowdb.display import print_error, print_info, print_success, print_warning
from meowdb.similarity import update_library_uniqueness

_MANIFEST_PATH = "meowdb-export/manifest.json"
_SUPPORTED_FORMAT_VERSIONS = {1}


@click.command(name="import")
@click.argument("archive", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--on-conflict",
    type=click.Choice(["skip", "replace", "new-ids"]),
    default="skip",
    show_default=True,
    help="How to handle meows whose ID already exists in the library.",
)
@db_path_option
def import_meows(archive: str, on_conflict: str, db_path: str | None) -> None:
    """Import meows from an export archive."""
    ctx = build_context(Path(db_path) if db_path else None)

    try:
        zf = zipfile.ZipFile(archive, "r")
    except zipfile.BadZipFile:
        print_error(f"Not a valid zip archive: {archive}")
        ctx.db.close()
        sys.exit(1)

    with zf:
        try:
            manifest = json.loads(zf.read(_MANIFEST_PATH))
        except KeyError:
            print_error("Archive is missing manifest.json — not a meowdb export.")
            ctx.db.close()
            sys.exit(1)

        if manifest.get("format_version") not in _SUPPORTED_FORMAT_VERSIONS:
            print_error(
                f"Unsupported archive format version: {manifest.get('format_version')!r}"
            )
            ctx.db.close()
            sys.exit(1)

        WAV_DIR.mkdir(parents=True, exist_ok=True)
        MP3_DIR.mkdir(parents=True, exist_ok=True)

        imported = 0
        skipped = 0
        replaced = 0
        new_ids: list[str] = []

        for meow in manifest.get("meows", []):
            archive_id: str = meow["id"]
            arc_wav = f"meowdb-export/audio/{archive_id}.wav"

            if arc_wav not in zf.namelist():
                print_warning(f"WAV missing in archive for {archive_id[:8]}, skipping")
                skipped += 1
                continue

            existing = ctx.db.get_by_id(archive_id)
            if existing:
                if on_conflict == "skip":
                    skipped += 1
                    continue
                elif on_conflict == "replace":
                    for field in ("wav_path", "mp3_path"):
                        p = Path(existing.get(field) or "")
                        if p.exists():
                            p.unlink()
                    ctx.db.delete(archive_id)
                    replaced += 1

            meow_id = str(uuid.uuid4()) if on_conflict == "new-ids" else archive_id

            wav_path = WAV_DIR / f"{meow_id}.wav"
            mp3_path = MP3_DIR / f"{meow_id}.mp3"

            with zf.open(arc_wav) as src, wav_path.open("wb") as dst:
                dst.write(src.read())

            audio = AudioSegment.from_wav(str(wav_path))
            audio.export(str(mp3_path), format="mp3", bitrate="192k")

            ctx.db.import_meow(meow_id, meow, str(wav_path), str(mp3_path))
            new_ids.append(meow_id)
            imported += 1

    if new_ids:
        print_info("Recomputing fingerprints and uniqueness scores...")
        update_library_uniqueness(ctx.db, new_ids)

    ctx.db.close()

    parts = [f"Imported {imported} meow(s)"]
    if replaced:
        parts.append(f"{replaced} replaced")
    if skipped:
        parts.append(f"{skipped} skipped")
    print_success(", ".join(parts))
