from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meowdb.db import MeowDB
    from meowdb.processor import MeowProcessor


@dataclass(frozen=True)
class Context:
    db: MeowDB
    processor: MeowProcessor
