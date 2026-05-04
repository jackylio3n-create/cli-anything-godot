from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path

from cli_anything.godot.core.project import upsert_enabled_editor_plugin


def packaged_bridge_dir() -> Path:
    return Path(__file__).resolve().parent / "bridge"


def default_bridge_state_dir(project_dir: str | Path) -> Path:
    state_dir = os.environ.get("CLI_ANYTHING_GODOT_STATE_DIR", "").strip()
    if state_dir:
        return _resolve_bridge_path(project_dir, state_dir)
    return Path(project_dir).resolve() / ".cli_anything_godot_bridge"


def _resolve_bridge_path(project_dir: str | Path, value: str | Path) -> Path:
    raw = str(value).strip()
    project_root = Path(project_dir).resolve()
    if raw.startswith("res://"):
        return project_root / raw.removeprefix("res://")
    if raw.startswith("user://"):
        raise ValueError(
            "user:// bridge paths cannot be resolved by the external Python client; "
            "use an absolute path or res:// path for CLI-driven bridge requests."
        )
    return Path(raw).expanduser().resolve()


def install_bridge(project_dir: str | Path) -> dict[str, str]:
    project_root = Path(project_dir).resolve()
    source_dir = packaged_bridge_dir() / "addons"
    target_dir = project_root / "addons"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    project_file = upsert_enabled_editor_plugin(
        project_root / "project.godot",
        "res://addons/cli_anything_godot_bridge/plugin.cfg",
    )
    return {
        "project_dir": str(project_root),
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "plugin_dir": str(target_dir / "cli_anything_godot_bridge"),
        "project_godot": str(project_file),
        "enabled_plugin": "res://addons/cli_anything_godot_bridge/plugin.cfg",
    }


def bridge_paths(project_dir: str | Path) -> dict[str, Path]:
    state_dir = default_bridge_state_dir(project_dir)
    request_env = os.environ.get("CLI_ANYTHING_GODOT_REQUEST", "").strip()
    response_env = os.environ.get("CLI_ANYTHING_GODOT_RESPONSE", "").strip()
    return {
        "state_dir": state_dir,
        "request_path": _resolve_bridge_path(project_dir, request_env) if request_env else state_dir / "request.json",
        "response_path": _resolve_bridge_path(project_dir, response_env) if response_env else state_dir / "response.json",
        "status_path": state_dir / "status.json",
    }


def write_bridge_request(
    project_dir: str | Path,
    *,
    op: str,
    args: dict | None = None,
    timeout_s: float = 30.0,
    request_id: str | None = None,
) -> dict[str, object]:
    paths = bridge_paths(project_dir)
    payload = {
        "id": request_id or f"req-{uuid.uuid4().hex[:12]}",
        "op": op,
        "args": args or {},
        "timeout_s": timeout_s,
    }
    paths["state_dir"].mkdir(parents=True, exist_ok=True)
    paths["request_path"].write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "payload": payload,
        "paths": {key: str(value) for key, value in paths.items()},
    }


def read_bridge_response(project_dir: str | Path) -> dict | None:
    response_path = bridge_paths(project_dir)["response_path"]
    if not response_path.exists():
        return None
    try:
        return json.loads(response_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def call_bridge(
    project_dir: str | Path,
    *,
    op: str,
    args: dict | None = None,
    timeout_s: float = 30.0,
    poll_interval_s: float = 0.25,
) -> dict:
    request = write_bridge_request(project_dir, op=op, args=args, timeout_s=timeout_s)
    request_id = request["payload"]["id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        response = read_bridge_response(project_dir)
        if isinstance(response, dict) and response.get("id") == request_id:
            return response
        time.sleep(poll_interval_s)
    raise TimeoutError(
        "Timed out waiting for Godot editor bridge response. "
        "Ensure the project is open in the Godot editor and the plugin is enabled."
    )
