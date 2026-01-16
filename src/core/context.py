from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Context:
    user_id: str
    session_id: Optional[str] = None
