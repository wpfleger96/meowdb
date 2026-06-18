from __future__ import annotations

from pathlib import Path

import pytest

import meowdb

from meowdb.config import ALLOWED_MEDIA_SUFFIXES, UPLOAD_ACCEPT

_INDEX_HTML = Path(meowdb.__file__).parent / "static" / "index.html"


@pytest.mark.unit
def test_upload_accept_derived_from_allowed_suffixes() -> None:
    assert set(UPLOAD_ACCEPT.split(",")) == ALLOWED_MEDIA_SUFFIXES


@pytest.mark.unit
def test_index_sources_picker_accept_from_config() -> None:
    html = _INDEX_HTML.read_text(encoding="utf-8")
    # The accepted-format list lives only in config; the page ships a placeholder
    # the server fills from UPLOAD_ACCEPT at serve time, so the HTML can't drift.
    assert 'accept="{{UPLOAD_ACCEPT}}"' in html
    rendered = html.replace("{{UPLOAD_ACCEPT}}", UPLOAD_ACCEPT)
    assert "{{UPLOAD_ACCEPT}}" not in rendered
    assert f'accept="{UPLOAD_ACCEPT}"' in rendered
