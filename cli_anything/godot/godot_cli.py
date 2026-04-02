from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import click

from cli_anything.godot import __version__
from cli_anything.godot.bridge_client import (
    bridge_paths,
    call_bridge,
    install_bridge,
    write_bridge_request,
)
from cli_anything.godot.core import (
    add_autoload,
    add_input_action,
    add_node,
    create_procedural_sprite,
    create_procedural_tone,
    create_project,
    create_scene,
    create_script,
    generate_autoload_singleton,
    list_nodes,
    project_info,
    write_import_file,
)
from cli_anything.godot.core.session import (
    append_command_history,
    load_session_state,
    save_session_state,
    session_state_path,
)
from cli_anything.godot.utils import (
    export_project,
    import_project,
    probe_backend as backend_probe,
    run_godot,
    run_project,
)
from cli_anything.godot.utils.repl_skin import ReplSkin


PUBLIC_PROGRAM_NAME = "cli-anything-godot"
REPL_COMMANDS = {
    "help": "Show REPL help.",
    "exit": "Leave the REPL.",
    "quit": "Leave the REPL.",
    "use-project <path>": "Persist a default project path for this REPL.",
    "current-project": "Show the current project path.",
    "clear-project": "Clear the current project path.",
    "status": "Show session state.",
    "history [limit]": "Show recent REPL commands.",
    "state-path": "Show the session state file path.",
}


def normalize_program_name(program_name: str | None) -> str:
    candidate = Path(program_name or "").name.strip()
    return candidate or PUBLIC_PROGRAM_NAME


def repl_help_text(program_name: str | None = None) -> str:
    name = normalize_program_name(program_name)
    return "\n".join(
        [
            f"Interactive REPL for {name}",
            "",
            "Builtins:",
            "  help              Show this REPL help",
            "  exit, quit        Leave the REPL",
            "  use-project <p>   Persist current project path",
            "  current-project   Show current project path",
            "  clear-project     Clear current project path",
            "  status            Show current session status",
            "  history [limit]   Show recent command history",
            "  state-path        Show the session state file path",
            "",
            "Examples:",
            "  probe backend --json",
            "  project new /tmp/demo --name Demo",
            "  use-project /tmp/demo",
            "  scene new @project/scenes/main.tscn --root-type Node2D",
            "  script new @project/scripts/player.gd --extends CharacterBody2D --class Player",
            "  asset sprite @project/assets/player.png --project-dir @project --shape circle",
            "  import run --project @project",
            "  editor install-bridge --project @project",
        ]
    )


def session_payload(session: dict[str, object]) -> dict[str, object]:
    history = list(session.get("command_history", []))
    return {
        "current_project": session.get("current_project"),
        "current_scene": session.get("current_scene"),
        "state_path": str(session_state_path()),
        "history_count": len(history),
    }


def root_json_output(ctx: click.Context | None) -> bool:
    if ctx is None:
        return False
    root = ctx.find_root()
    return bool(root and root.obj and root.obj.get("json"))


def emit_json(payload: object) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def emit_output(ctx: click.Context, payload: dict[str, object]) -> None:
    if root_json_output(ctx):
        emit_json(payload)
        return
    for key, value in payload.items():
        click.echo(f"{key}: {value}")


def fail(ctx: click.Context, message: str, *, code: str = "runtime_error", details: dict | None = None) -> None:
    if root_json_output(ctx):
        emit_json({"ok": False, "error": {"code": code, "message": message, "details": details or {}}})
    else:
        click.echo(f"Error: {message}", err=True)
    raise SystemExit(1)


def handle_errors(func):
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        try:
            return func(*args, **kwargs)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            fail(ctx, str(exc), code=type(exc).__name__)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def _resolve_project(ctx: click.Context, explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    if ctx.obj.get("project"):
        return Path(ctx.obj["project"]).expanduser().resolve()
    session = load_session_state()
    current_project = session.get("current_project")
    if isinstance(current_project, str) and current_project:
        return Path(current_project).expanduser().resolve()
    raise RuntimeError("No project path set. Pass --project or use `use-project` in the REPL.")


def _expand_repl_tokens(argv: list[str], session: dict[str, object]) -> list[str]:
    current_project = session.get("current_project")
    expanded: list[str] = []
    for token in argv:
        if token.startswith("@project") and isinstance(current_project, str):
            suffix = token[len("@project") :]
            if suffix.startswith("/"):
                expanded.append(str(Path(current_project) / suffix[1:]))
            elif suffix:
                expanded.append(str(Path(current_project) / suffix))
            else:
                expanded.append(current_project)
        else:
            expanded.append(token)
    return expanded


def _set_godot_env(godot_bin: str | None) -> None:
    if godot_bin:
        os.environ["GODOT_PATH"] = str(Path(godot_bin).expanduser())


def dispatch(argv: list[str], prog_name: str = PUBLIC_PROGRAM_NAME) -> int:
    try:
        cli.main(args=argv, prog_name=prog_name, standalone_mode=False)
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        return 1
    return 0


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output machine-readable JSON.")
@click.option("--project", type=click.Path(), default=None, help="Default project directory for subcommands.")
@click.option("--godot-bin", type=click.Path(), default=None, help="Explicit Godot executable path.")
@click.pass_context
def cli(ctx: click.Context, use_json: bool, project: str | None, godot_bin: str | None) -> None:
    """cli-anything-godot: agent-oriented Godot CLI harness."""
    ctx.ensure_object(dict)
    _set_godot_env(godot_bin)
    ctx.obj.update({"json": use_json, "project": project, "godot_bin": godot_bin})
    if project:
        session = load_session_state()
        session["current_project"] = str(Path(project).expanduser().resolve())
        save_session_state(session)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.command("repl")
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Start the interactive REPL."""
    skin = ReplSkin("godot", version=__version__)
    skin.print_banner()
    click.echo(repl_help_text(ctx.info_name))
    pt_session = skin.create_prompt_session()
    while True:
        session = load_session_state()
        project_name = Path(session["current_project"]).name if isinstance(session.get("current_project"), str) else ""
        try:
            line = skin.get_input(pt_session, project_name=project_name)
        except EOFError:
            click.echo()
            break
        if not line:
            continue
        if line in {"exit", "quit"}:
            break
        if line == "help":
            click.echo(repl_help_text(ctx.info_name))
            continue
        if line.startswith("use-project "):
            project_path = shlex.split(line)[1]
            session["current_project"] = str(Path(project_path).expanduser().resolve())
            save_session_state(session)
            click.echo(f"Current project: {session['current_project']}")
            continue
        if line == "current-project":
            click.echo(f"Current project: {session.get('current_project') or '(none)'}")
            continue
        if line == "clear-project":
            session["current_project"] = None
            save_session_state(session)
            click.echo("Current project cleared.")
            continue
        if line == "status":
            payload = session_payload(session)
            if root_json_output(ctx):
                emit_json(payload)
            else:
                for key, value in payload.items():
                    click.echo(f"{key}: {value}")
            continue
        if line.startswith("history"):
            parts = shlex.split(line)
            limit = int(parts[1]) if len(parts) > 1 else 10
            for item in list(session.get("command_history", []))[-limit:]:
                click.echo(item)
            continue
        if line == "state-path":
            click.echo(str(session_state_path()))
            continue

        append_command_history(line)
        argv = _expand_repl_tokens(shlex.split(line), session)
        code = dispatch(argv, prog_name=PUBLIC_PROGRAM_NAME)
        if code != 0:
            click.echo(f"Command exited with status {code}", err=True)
    skin.print_goodbye()


@cli.group()
def probe() -> None:
    """Inspect the Godot backend."""


@probe.command("backend")
@click.pass_context
@handle_errors
def probe_backend(ctx: click.Context) -> None:
    """Show backend availability and version."""
    result = backend_probe()
    if not result["available"]:
        raise RuntimeError(str(result.get("error") or "Godot backend unavailable"))
    executable = result["executable"]
    emit_output(
        ctx,
        {
            "ok": True,
            "executable": executable,
            "version": result["version"],
            "on_path": bool(shutil.which(Path(executable).name)),
        },
    )


@cli.group()
def project() -> None:
    """Manage Godot projects."""


@project.command("new")
@click.argument("project_dir", type=click.Path())
@click.option("--name", default="CLI Anything Godot Game", help="Project name.")
@click.option("--main-scene", default="res://scenes/main.tscn", help="Main scene resource path.")
@click.pass_context
@handle_errors
def project_new(ctx: click.Context, project_dir: str, name: str, main_scene: str) -> None:
    """Create a text-first Godot project scaffold."""
    result = create_project(project_dir, name, main_scene=main_scene)
    main_scene_fs = Path(project_dir).resolve() / main_scene.replace("res://", "")
    create_scene(main_scene_fs)
    session = load_session_state()
    session["current_project"] = str(Path(project_dir).resolve())
    session["current_scene"] = str(main_scene_fs)
    save_session_state(session)
    emit_output(
        ctx,
        {
            "ok": True,
            "project_dir": str(result["project_dir"]),
            "project_godot": str(result["project_godot"]),
            "export_presets": str(result["export_presets"]),
            "main_scene": str(main_scene_fs),
        },
    )


@project.command("info")
@click.pass_context
@handle_errors
def project_info_cmd(ctx: click.Context) -> None:
    """Show project metadata."""
    info = project_info(_resolve_project(ctx))
    normalized = {key: str(value) if isinstance(value, Path) else value for key, value in info.items()}
    normalized["ok"] = True
    emit_output(ctx, normalized)


@project.command("add-input")
@click.argument("action_name")
@click.option("--key", "keys", multiple=True, required=True, help="Key name or keycode token.")
@click.pass_context
@handle_errors
def project_add_input(ctx: click.Context, action_name: str, keys: tuple[str, ...]) -> None:
    """Add or replace one input action in project.godot."""
    project_dir = _resolve_project(ctx)
    path = add_input_action(project_dir, action_name, list(keys))
    emit_output(ctx, {"ok": True, "project_dir": str(project_dir), "project_godot": str(path), "action": action_name})


@project.command("add-autoload")
@click.argument("name")
@click.argument("resource_path")
@click.pass_context
@handle_errors
def project_add_autoload(ctx: click.Context, name: str, resource_path: str) -> None:
    """Add or replace one autoload singleton."""
    project_dir = _resolve_project(ctx)
    path = add_autoload(project_dir, name, resource_path)
    emit_output(ctx, {"ok": True, "project_dir": str(project_dir), "project_godot": str(path), "autoload": name})


@cli.group()
def scene() -> None:
    """Create and edit text scenes."""


@scene.command("new")
@click.argument("scene_path", type=click.Path())
@click.option("--root-type", default="Node2D")
@click.option("--root-name", default="Main")
@click.pass_context
@handle_errors
def scene_new(ctx: click.Context, scene_path: str, root_type: str, root_name: str) -> None:
    path = create_scene(scene_path, root_type=root_type, root_name=root_name)
    session = load_session_state()
    session["current_scene"] = str(Path(scene_path).resolve())
    save_session_state(session)
    emit_output(ctx, {"ok": True, "scene_path": str(path), "root_type": root_type, "root_name": root_name})


def _parse_properties(pairs: tuple[str, ...]) -> dict[str, object]:
    properties: dict[str, object] = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        if not key or not _:
            raise ValueError(f"Property must use key=value format: {pair}")
        properties[key] = value
    return properties


@scene.command("add-node")
@click.argument("scene_path", type=click.Path())
@click.argument("name")
@click.argument("node_type")
@click.option("--parent", default=".")
@click.option("--property", "properties", multiple=True, help="Node property in key=value form.")
@click.pass_context
@handle_errors
def scene_add_node(ctx: click.Context, scene_path: str, name: str, node_type: str, parent: str, properties: tuple[str, ...]) -> None:
    path = add_node(scene_path, name, node_type, parent=parent, properties=_parse_properties(properties))
    emit_output(ctx, {"ok": True, "scene_path": str(path), "node": name, "type": node_type, "parent": parent})


@scene.command("list")
@click.argument("scene_path", type=click.Path())
@click.pass_context
@handle_errors
def scene_list(ctx: click.Context, scene_path: str) -> None:
    nodes = list_nodes(scene_path)
    if root_json_output(ctx):
        emit_json({"ok": True, "nodes": nodes})
    else:
        for node in nodes:
            click.echo(f"{node['name']} {node['type']} parent={node['parent'] or '<root>'}")


@cli.group()
def script() -> None:
    """Generate scripts."""


@script.command("new")
@click.argument("script_path", type=click.Path())
@click.option("--extends", "extends_name", default="Node")
@click.option("--class", "class_name", default=None)
@click.pass_context
@handle_errors
def script_new(ctx: click.Context, script_path: str, extends_name: str, class_name: str | None) -> None:
    path = create_script(script_path, extends_name=extends_name, class_name=class_name)
    emit_output(ctx, {"ok": True, "script_path": str(path), "extends": extends_name, "class_name": class_name})


@script.command("autoload")
@click.argument("script_path", type=click.Path())
@click.pass_context
@handle_errors
def script_autoload(ctx: click.Context, script_path: str) -> None:
    path = generate_autoload_singleton(script_path)
    emit_output(ctx, {"ok": True, "script_path": str(path), "singleton_ready": True})


@cli.group()
def asset() -> None:
    """Generate lightweight procedural assets."""


@asset.command("sprite")
@click.argument("output_path", type=click.Path())
@click.option("--shape", default="square")
@click.option("--color", default="#6fa8ff")
@click.option("--size", default=128, type=int)
@click.option("--project-dir", type=click.Path(), default=None, help="Write matching .import sidecar for this project.")
@click.pass_context
@handle_errors
def asset_sprite(ctx: click.Context, output_path: str, shape: str, color: str, size: int, project_dir: str | None) -> None:
    path = create_procedural_sprite(output_path, shape=shape, color=color, size=size)
    payload: dict[str, object] = {"ok": True, "asset_path": str(path), "shape": shape, "color": color, "size": size}
    if project_dir:
        import_path = write_import_file(project_dir, path)
        payload["import_path"] = str(import_path)
    emit_output(ctx, payload)


@asset.command("tone")
@click.argument("output_path", type=click.Path())
@click.option("--frequency", default=440, type=int)
@click.option("--duration-ms", default=250, type=int)
@click.pass_context
@handle_errors
def asset_tone(ctx: click.Context, output_path: str, frequency: int, duration_ms: int) -> None:
    path = create_procedural_tone(output_path, frequency=frequency, duration_ms=duration_ms)
    emit_output(ctx, {"ok": True, "asset_path": str(path), "frequency": frequency, "duration_ms": duration_ms})


@cli.group("import")
def import_group() -> None:
    """Run Godot import flows."""


@import_group.command("run")
@click.pass_context
@handle_errors
def import_run(ctx: click.Context) -> None:
    project_dir = _resolve_project(ctx)
    result = import_project(project_dir)
    emit_output(ctx, {"ok": True, "project_dir": str(project_dir), **result})


@cli.group()
def run() -> None:
    """Run a Godot project."""


@run.command("game")
@click.option("--scene", "scene_path", type=click.Path(), default=None)
@click.option("--headless/--no-headless", default=False)
@click.option("--quit", is_flag=True, default=False, help="Quit after first iteration.")
@click.pass_context
@handle_errors
def run_game(ctx: click.Context, scene_path: str | None, headless: bool, quit: bool) -> None:
    project_dir = _resolve_project(ctx)
    extra_args = ["--quit"] if quit else None
    result = run_project(project_dir, scene_path=scene_path, headless=headless, extra_args=extra_args)
    emit_output(ctx, {"ok": True, "project_dir": str(project_dir), **result})


@cli.group()
def export() -> None:
    """Export a Godot project."""


@export.command("release")
@click.argument("preset")
@click.argument("output_path", type=click.Path())
@click.option("--import-first", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--headless/--no-headless", default=True)
@click.pass_context
@handle_errors
def export_release(ctx: click.Context, preset: str, output_path: str, import_first: bool, overwrite: bool, headless: bool) -> None:
    project_dir = _resolve_project(ctx)
    if import_first:
        import_project(project_dir)
    if Path(output_path).exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {output_path}")
    if not headless:
        raise RuntimeError("Current backend only supports release export through headless mode.")
    result = export_project(project_dir, preset=preset, output_path=output_path, mode="release")
    emit_output(ctx, {"ok": True, "project_dir": str(project_dir), **result})


@export.command("debug")
@click.argument("preset")
@click.argument("output_path", type=click.Path())
@click.option("--import-first", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--headless/--no-headless", default=True)
@click.pass_context
@handle_errors
def export_debug(ctx: click.Context, preset: str, output_path: str, import_first: bool, overwrite: bool, headless: bool) -> None:
    project_dir = _resolve_project(ctx)
    if import_first:
        import_project(project_dir)
    if Path(output_path).exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {output_path}")
    if not headless:
        raise RuntimeError("Current backend only supports debug export through headless mode.")
    result = export_project(project_dir, preset=preset, output_path=output_path, mode="debug")
    emit_output(ctx, {"ok": True, "project_dir": str(project_dir), **result})


@export.command("pack")
@click.argument("preset")
@click.argument("output_path", type=click.Path())
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--headless/--no-headless", default=True)
@click.pass_context
@handle_errors
def export_pack(ctx: click.Context, preset: str, output_path: str, overwrite: bool, headless: bool) -> None:
    project_dir = _resolve_project(ctx)
    output = Path(output_path).resolve()
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not headless:
        raise RuntimeError("Current backend only supports pack export through headless mode.")
    result = run_godot(["--headless", "--path", str(project_dir), "--export-pack", preset, str(output)])
    result["output"] = str(output)
    result["file_exists"] = output.exists()
    if output.exists():
        result["file_size"] = output.stat().st_size
    emit_output(ctx, {"ok": result["ok"], "project_dir": str(project_dir), **result})


@cli.group()
def editor() -> None:
    """Install and use the editor bridge."""


@editor.command("install-bridge")
@click.pass_context
@handle_errors
def editor_install_bridge(ctx: click.Context) -> None:
    project_dir = _resolve_project(ctx)
    payload = install_bridge(project_dir)
    paths = bridge_paths(project_dir)
    payload.update({key: str(value) for key, value in paths.items()})
    payload["ok"] = True
    emit_output(ctx, payload)


@editor.command("ping")
@click.option("--timeout-s", default=30.0, type=float)
@click.pass_context
@handle_errors
def editor_ping(ctx: click.Context, timeout_s: float) -> None:
    project_dir = _resolve_project(ctx)
    response = call_bridge(project_dir, op="ping", timeout_s=timeout_s)
    if root_json_output(ctx):
        emit_json(response)
    else:
        click.echo(json.dumps(response, ensure_ascii=False, indent=2))


@editor.command("list-scenes")
@click.option("--timeout-s", default=30.0, type=float)
@click.pass_context
@handle_errors
def editor_list_scenes(ctx: click.Context, timeout_s: float) -> None:
    project_dir = _resolve_project(ctx)
    response = call_bridge(project_dir, op="list_scenes", timeout_s=timeout_s)
    if root_json_output(ctx):
        emit_json(response)
    else:
        click.echo(json.dumps(response, ensure_ascii=False, indent=2))


@editor.command("write-status")
@click.option("--path", "status_path", type=click.Path(), default=None)
@click.option("--state", default="ok")
@click.option("--timeout-s", default=30.0, type=float)
@click.pass_context
@handle_errors
def editor_write_status(ctx: click.Context, status_path: str | None, state: str, timeout_s: float) -> None:
    project_dir = _resolve_project(ctx)
    args = {"status": {"state": state}}
    if status_path:
        args["path"] = str(Path(status_path).resolve())
    response = call_bridge(project_dir, op="write_status", args=args, timeout_s=timeout_s)
    if root_json_output(ctx):
        emit_json(response)
    else:
        click.echo(json.dumps(response, ensure_ascii=False, indent=2))


@editor.command("enqueue")
@click.argument("op")
@click.option("--args-json", default="{}", help="Raw JSON object for args.")
@click.option("--timeout-s", default=30.0, type=float)
@click.pass_context
@handle_errors
def editor_enqueue(ctx: click.Context, op: str, args_json: str, timeout_s: float) -> None:
    project_dir = _resolve_project(ctx)
    args = json.loads(args_json)
    payload = write_bridge_request(project_dir, op=op, args=args, timeout_s=timeout_s)
    payload["ok"] = True
    if root_json_output(ctx):
        emit_json(payload)
    else:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@cli.group()
def inspect() -> None:
    """Inspect project files."""


@inspect.command("files")
@click.pass_context
@handle_errors
def inspect_files(ctx: click.Context) -> None:
    project_dir = _resolve_project(ctx)
    scenes = sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*.tscn"))
    scripts = sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*.gd"))
    assets = sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*.png"))
    payload = {"ok": True, "project_dir": str(project_dir), "scenes": scenes, "scripts": scripts, "assets": assets}
    if root_json_output(ctx):
        emit_json(payload)
    else:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@cli.group()
def session() -> None:
    """Inspect CLI session state."""


@session.command("status")
@click.pass_context
@handle_errors
def session_status(ctx: click.Context) -> None:
    payload = session_payload(load_session_state())
    payload["ok"] = True
    emit_output(ctx, payload)


@session.command("clear")
@click.pass_context
@handle_errors
def session_clear(ctx: click.Context) -> None:
    save_session_state({"current_project": None, "current_scene": None, "command_history": []})
    emit_output(ctx, {"ok": True, "cleared": True, "state_path": str(session_state_path())})


def entrypoint() -> int:
    return dispatch(sys.argv[1:], prog_name=PUBLIC_PROGRAM_NAME)
