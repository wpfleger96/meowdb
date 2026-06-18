from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

import meowdb

from meowdb.config import ALLOWED_MEDIA_SUFFIXES

_INDEX_HTML = Path(meowdb.__file__).parent / "static" / "index.html"


class _AcceptExtractor(HTMLParser):
    """Pulls the `accept` value off the audio/video upload <input>."""

    def __init__(self) -> None:
        super().__init__()
        self.accept: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        attr = dict(attrs)
        if attr.get("x-ref") == "fileInput":
            self.accept = attr.get("accept")


@pytest.mark.unit
def test_picker_accept_matches_allowed_suffixes() -> None:
    parser = _AcceptExtractor()
    parser.feed(_INDEX_HTML.read_text(encoding="utf-8"))
    assert parser.accept is not None, "upload input (x-ref=fileInput) not found"
    picker = {ext.strip() for ext in parser.accept.split(",")}
    assert picker == ALLOWED_MEDIA_SUFFIXES
