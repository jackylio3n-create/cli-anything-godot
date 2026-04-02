from __future__ import annotations

import json
import os
from pathlib import Path


SESSION_HISTORY_LIMIT = 100


def session_state_dir() -> Path:
    override = os.environ.get("CLI_ANYTHING_GODOT_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "cli-anything-godot"


def session_state_path() -> Path:
    return session_state_dir() / "session.json"


def default_session_state() -> dict[str, object]:
    return {
        "current_project": None,
        "current_scene": None,
        "command_history": [],
    }


def load_session_state() -> dict[str, object]:
    path = session_state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default_session_state()
    history = data.get("command_history")
    return {
        "current_project": data.get("current_project") if isinstance(data.get("current_project"), str) else None,
        "current_scene": data.get("current_scene") if isinstance(data.get("current_scene"), str) else None,
        "command_history": [item for item in history if isinstance(item, str)][-SESSION_HISTORY_LIMIT:]
        if isinstance(history, list)
        else [],
    }


def _locked_save_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(path, "r+", encoding="utf-8")
    except FileNotFoundError:
        handle = open(path, "w+", encoding="utf-8")
    with handle:
        locked = False
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            handle.seek(0)
            handle.truncate()
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
        finally:
            if locked:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def save_session_state(session: dict[str, object]) -> None:
    _locked_save_json(
        session_state_path(),
        {
            "current_project": session.get("current_project"),
            "current_scene": session.get("current_scene"),
            "command_history": list(session.get("command_history", [])),
        },
    )


def append_command_history(command_line: str) -> None:
    command_line = command_line.strip()
    if not command_line:
        return
    session = load_session_state()
    history = list(session.get("command_history", []))
    history.append(command_line)
    session["command_history"] = history[-SESSION_HISTORY_LIMIT:]
    save_session_state(session)
