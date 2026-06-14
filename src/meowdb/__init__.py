from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("meowdb")
except PackageNotFoundError:
    __version__ = "dev"
