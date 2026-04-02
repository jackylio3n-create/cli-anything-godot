# Godot Editor Bridge Scaffold

This bridge is an editor-only Godot plugin at:

- `cli_anything/godot/bridge/addons/cli_anything_godot_bridge`

## Request/Response Protocol

The plugin polls a JSON request file and writes a JSON response file.

Environment variables used:

- `CLI_ANYTHING_GODOT_REQUEST`: absolute or `res://`/`user://` path for request JSON.
- `CLI_ANYTHING_GODOT_RESPONSE`: absolute or `res://`/`user://` path for response JSON.
- `CLI_ANYTHING_GODOT_STATE_DIR` (optional): directory used only when request/response vars are not provided.

Deterministic fallback paths (when request/response env vars are empty):

- `request_path`: `<state_dir>/request.json`
- `response_path`: `<state_dir>/response.json`
- `state_dir` default: `res://.cli_anything_godot_bridge`

Request schema:

```json
{
  "id": "req-123",
  "op": "ping",
  "args": {},
  "timeout_s": 30
}
```

Response schema:

```json
{
  "id": "req-123",
  "ok": true,
  "result": {},
  "error": null,
  "warnings": [],
  "artifacts": []
}
```

Supported ops:

- `ping`: returns bridge metadata, supported ops, env var names, and resolved file paths.
- `list_scenes`: returns `res://` scene files (`.tscn`, `.scn`).
- `write_status`: writes status content to `args.path` (or `<state_dir>/status.json`) using `args.status` (or `args.content`).
