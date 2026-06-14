from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _e2e_marker(request: pytest.FixtureRequest) -> None:
    """Auto-mark all tests in e2e/ directory."""
    request.node.add_marker(pytest.mark.e2e)
