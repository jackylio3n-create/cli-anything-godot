@tool
extends EditorPlugin

const BRIDGE_NAME := "cli_anything_godot_bridge"

const ENV_REQUEST_PATH := "CLI_ANYTHING_GODOT_REQUEST"
const ENV_RESPONSE_PATH := "CLI_ANYTHING_GODOT_RESPONSE"
const ENV_STATE_DIR := "CLI_ANYTHING_GODOT_STATE_DIR"

const DEFAULT_STATE_DIR := "res://.cli_anything_godot_bridge"
const DEFAULT_REQUEST_FILE := "request.json"
const DEFAULT_RESPONSE_FILE := "response.json"
const DEFAULT_STATUS_FILE := "status.json"

const POLL_INTERVAL_S := 0.35
const DEFAULT_TIMEOUT_S := 30.0
const SUPPORTED_OPS := ["ping", "list_scenes", "write_status"]

var _state_dir_path := ""
var _request_path := ""
var _response_path := ""
var _last_request_fingerprint := 0
var _poller: Timer = null


func _enter_tree() -> void:
	_configure_paths()
	_ensure_parent_dir(_request_path)
	_ensure_parent_dir(_response_path)
	_start_poller()


func _exit_tree() -> void:
	if is_instance_valid(_poller):
		_poller.stop()
		_poller.queue_free()
	_poller = null


func _start_poller() -> void:
	_poller = Timer.new()
	_poller.one_shot = false
	_poller.autostart = true
	_poller.wait_time = POLL_INTERVAL_S
	_poller.timeout.connect(_on_poll_timeout)
	add_child(_poller)


func _configure_paths() -> void:
	var state_dir_env := OS.get_environment(ENV_STATE_DIR).strip_edges()
	_state_dir_path = _normalize_path(state_dir_env if not state_dir_env.is_empty() else DEFAULT_STATE_DIR)

	var request_env := OS.get_environment(ENV_REQUEST_PATH).strip_edges()
	var request_candidate := request_env if not request_env.is_empty() else _state_dir_path.path_join(DEFAULT_REQUEST_FILE)
	_request_path = _normalize_path(request_candidate)

	var response_env := OS.get_environment(ENV_RESPONSE_PATH).strip_edges()
	var response_candidate := response_env if not response_env.is_empty() else _state_dir_path.path_join(DEFAULT_RESPONSE_FILE)
	_response_path = _normalize_path(response_candidate)


func _on_poll_timeout() -> void:
	if _request_path == _response_path:
		_write_json_response(
			_error_response(
				null,
				"invalid_bridge_paths",
				"Request and response file paths must be different.",
				{
					"request_path": _request_path,
					"response_path": _response_path,
				}
			)
		)
		return

	var raw_request := _read_text_file(_request_path)
	if raw_request.strip_edges().is_empty():
		return

	var fingerprint := raw_request.hash()
	if fingerprint == _last_request_fingerprint:
		return
	_last_request_fingerprint = fingerprint

	var response := _handle_request(raw_request)
	_write_json_response(response)


func _handle_request(raw_request: String) -> Dictionary:
	var parser := JSON.new()
	var parse_err := parser.parse(raw_request)
	if parse_err != OK:
		return _error_response(
			null,
			"invalid_json",
			"Failed to parse request JSON.",
			{
				"error_message": parser.get_error_message(),
				"error_line": parser.get_error_line(),
			}
		)

	if typeof(parser.data) != TYPE_DICTIONARY:
		return _error_response(
			null,
			"invalid_request",
			"Request payload must be a JSON object.",
			{
				"expected_fields": ["id", "op", "args", "timeout_s"],
			}
		)

	var request: Dictionary = parser.data
	return _dispatch_request(request)


func _dispatch_request(request: Dictionary) -> Dictionary:
	var request_id = request.get("id", null)
	var op := str(request.get("op", "")).strip_edges()
	if op.is_empty():
		return _error_response(
			request_id,
			"missing_op",
			"Request is missing `op`.",
			{
				"supported_ops": SUPPORTED_OPS,
			}
		)

	var args_value: Variant = request.get("args", {})
	if typeof(args_value) != TYPE_DICTIONARY:
		return _error_response(
			request_id,
			"invalid_args",
			"`args` must be a JSON object.",
			{
				"op": op,
			}
		)
	var args: Dictionary = args_value

	var warnings: Array = []
	var timeout_s := _coerce_timeout(request.get("timeout_s", DEFAULT_TIMEOUT_S), warnings)
	var started_ms := Time.get_ticks_msec()

	var response: Dictionary
	match op:
		"ping":
			response = _success_response(request_id, _ping_result(), warnings)
		"list_scenes":
			var scenes := _list_scene_paths()
			response = _success_response(
				request_id,
				{
					"scenes": scenes,
					"count": scenes.size(),
				},
				warnings
			)
		"write_status":
			response = _op_write_status(request_id, args, warnings)
		_:
			response = _error_response(
				request_id,
				"unknown_op",
				"Unsupported op `%s`." % op,
				{
					"supported_ops": SUPPORTED_OPS,
				},
				warnings
			)

	var elapsed_s := float(Time.get_ticks_msec() - started_ms) / 1000.0
	if elapsed_s > timeout_s:
		return _error_response(
			request_id,
			"timeout_exceeded",
			"Operation exceeded timeout_s.",
			{
				"timeout_s": timeout_s,
				"elapsed_s": elapsed_s,
				"op": op,
			},
			response.get("warnings", []),
			response.get("artifacts", [])
		)

	return response


func _ping_result() -> Dictionary:
	return {
		"bridge": BRIDGE_NAME,
		"ops": SUPPORTED_OPS,
		"env_vars": {
			"request_path": ENV_REQUEST_PATH,
			"response_path": ENV_RESPONSE_PATH,
			"state_dir": ENV_STATE_DIR,
		},
		"paths": {
			"request_path": _request_path,
			"response_path": _response_path,
			"state_dir": _state_dir_path,
		},
		"timestamp_unix": Time.get_unix_time_from_system(),
	}


func _list_scene_paths() -> Array:
	var scenes: Array = []
	_collect_scene_paths("res://", scenes)
	scenes.sort()
	return scenes


func _collect_scene_paths(dir_path: String, scenes: Array) -> void:
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return

	dir.list_dir_begin()
	while true:
		var entry := dir.get_next()
		if entry.is_empty():
			break
		if entry == "." or entry == "..":
			continue

		var full_path := dir_path.path_join(entry)
		if dir.current_is_dir():
			if entry == ".godot":
				continue
			_collect_scene_paths(full_path, scenes)
			continue

		if entry.ends_with(".tscn") or entry.ends_with(".scn"):
			scenes.append(full_path)
	dir.list_dir_end()


func _op_write_status(request_id, args: Dictionary, base_warnings: Array) -> Dictionary:
	var warnings: Array = base_warnings.duplicate()
	var path_arg := str(args.get("path", "")).strip_edges()
	var status_path := _normalize_path(path_arg if not path_arg.is_empty() else _state_dir_path.path_join(DEFAULT_STATUS_FILE))

	var status_payload: Variant
	if args.has("status"):
		status_payload = args["status"]
	elif args.has("content"):
		status_payload = args["content"]
		warnings.append("`content` is accepted, but `status` is preferred.")
	else:
		status_payload = {
			"bridge": BRIDGE_NAME,
			"state": "ok",
			"updated_unix": Time.get_unix_time_from_system(),
		}
		warnings.append("No `status` payload provided; wrote default status object.")

	var status_text := ""
	if typeof(status_payload) == TYPE_STRING:
		status_text = status_payload
	else:
		status_text = JSON.stringify(status_payload, "\t")
	if not status_text.ends_with("\n"):
		status_text += "\n"

	if not _write_text_atomic(status_path, status_text):
		return _error_response(
			request_id,
			"status_write_failed",
			"Failed to write status file.",
			{
				"path": status_path,
			},
			warnings
		)

	var artifacts := [
		{
			"type": "file",
			"path": status_path,
		}
	]
	return _success_response(
		request_id,
		{
			"status_path": status_path,
			"bytes": status_text.to_utf8_buffer().size(),
			"updated_unix": Time.get_unix_time_from_system(),
		},
		warnings,
		artifacts
	)


func _coerce_timeout(value: Variant, warnings: Array) -> float:
	if typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT:
		var timeout_s := float(value)
		if timeout_s > 0.0:
			return timeout_s
	warnings.append("Invalid timeout_s; defaulted to %.1f." % DEFAULT_TIMEOUT_S)
	return DEFAULT_TIMEOUT_S


func _success_response(request_id, result: Variant, warnings: Array = [], artifacts: Array = []) -> Dictionary:
	return {
		"id": request_id,
		"ok": true,
		"result": result,
		"error": null,
		"warnings": warnings,
		"artifacts": artifacts,
	}


func _error_response(
	request_id,
	code: String,
	message: String,
	details: Variant = null,
	warnings: Array = [],
	artifacts: Array = []
) -> Dictionary:
	var error_obj := {
		"code": code,
		"message": message,
	}
	if details != null:
		error_obj["details"] = details
	return {
		"id": request_id,
		"ok": false,
		"result": null,
		"error": error_obj,
		"warnings": warnings,
		"artifacts": artifacts,
	}


func _write_json_response(response: Dictionary) -> void:
	var text := JSON.stringify(response, "\t") + "\n"
	_write_text_atomic(_response_path, text)


func _read_text_file(path: String) -> String:
	if not FileAccess.file_exists(path):
		return ""
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return ""
	var text := file.get_as_text()
	file = null
	return text


func _write_text_atomic(path: String, text: String) -> bool:
	_ensure_parent_dir(path)

	var tmp_path := "%s.tmp" % path
	var tmp_file := FileAccess.open(tmp_path, FileAccess.WRITE)
	if tmp_file == null:
		return false
	tmp_file.store_string(text)
	tmp_file.flush()
	tmp_file = null

	var rename_err := DirAccess.rename_absolute(tmp_path, path)
	if rename_err == OK:
		return true

	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(text)
	file.flush()
	file = null
	return true


func _ensure_parent_dir(file_path: String) -> void:
	var dir_path := file_path.get_base_dir()
	if dir_path.is_empty():
		return
	DirAccess.make_dir_recursive_absolute(dir_path)


func _normalize_path(raw_path: String) -> String:
	var path := raw_path.strip_edges()
	if path.is_empty():
		return ProjectSettings.globalize_path(DEFAULT_STATE_DIR)
	if path.begins_with("res://") or path.begins_with("user://"):
		return ProjectSettings.globalize_path(path)
	if path.is_absolute_path():
		return path
	var project_root := ProjectSettings.globalize_path("res://")
	return project_root.path_join(path)
