from __future__ import annotations

from pathlib import Path

from PIL import Image


def optimize_photo(src: Path) -> Path:
    """
    Resize to max 1200px on longest edge, convert to WebP quality=85.
    Saves alongside src as {stem}.webp. Returns the dest path.
    """
    dest = src.with_suffix(".webp")
    with Image.open(src) as img:
        max_dim = 1200
        if max(img.width, img.height) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        img.save(dest, format="WEBP", quality=85)
    return dest
