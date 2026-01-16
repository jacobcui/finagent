from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

env_session_dir = os.getenv("FINAGENT_SESSION_DIR")
if env_session_dir:
    SESSION_DIR = Path(env_session_dir)
else:
    SESSION_DIR = Path.home() / ".finagent" / "sessions"


def load_session(session_id: Optional[str]) -> Tuple[str, List[Dict[str, Any]]]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    if session_id:
        path = SESSION_DIR / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session file not found for id {session_id}")
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            messages = []
        return session_id, messages
    new_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    data = {
        "session_id": new_id,
        "created_at": created_at,
        "updated_at": created_at,
        "messages": [],
    }
    path = SESSION_DIR / f"{new_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_id, []


def save_session(session_id: str, messages: List[Dict[str, Any]]) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{session_id}.json"
    now = datetime.utcnow().isoformat()
    data = {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "messages": messages,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
