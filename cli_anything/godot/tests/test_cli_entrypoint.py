import json
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cli_anything.godot.godot_cli import dispatch, repl_help_text


REPO_ROOT = Path(__file__).resolve().parents[4]


def resolve_cli() -> list[str]:
    installed = shutil.which("cli-anything-godot")
    if installed:
        return [installed]
    return [sys.executable, "-m", "cli_anything.godot"]


class CliEntrypointTests(unittest.TestCase):
    CLI_BASE = resolve_cli()

    def run_cli(self, args, input_text=None, extra_env=None):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            self.CLI_BASE + args,
            input=input_text,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_help_renders_root_commands(self):
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("project", result.stdout)
        self.assertIn("scene", result.stdout)
        self.assertIn("editor", result.stdout)

    def test_dispatch_uses_expected_program_name(self):
        stream = subprocess.run(
            [sys.executable, "-c", f"from cli_anything.godot.godot_cli import dispatch; raise SystemExit(dispatch(['--help'], prog_name='cli-anything-godot'))"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(REPO_ROOT)},
        )
        self.assertEqual(stream.returncode, 0)
        self.assertIn("Usage: cli-anything-godot", stream.stdout)

    def test_repl_help_mentions_use_project(self):
        self.assertIn("use-project", repl_help_text())
        self.assertIn("  import run", repl_help_text())
        self.assertNotIn("import run --project", repl_help_text())

    def test_invalid_option_returns_click_error_without_traceback(self):
        result = self.run_cli(["import", "run", "--project", "/tmp/demo"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No such option: --project", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_default_entrypoint_starts_repl_and_can_exit(self):
        result = self.run_cli([], input_text="exit\n")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Interactive REPL", result.stdout)

    def test_project_new_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_cli(["--json", "project", "new", tmpdir, "--name", "Demo"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(Path(tmpdir, "project.godot").exists())
            self.assertTrue(Path(tmpdir, "scenes", "main.tscn").exists())

    def test_scene_and_script_commands_create_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(["project", "new", tmpdir, "--name", "Demo"])
            scene_path = Path(tmpdir) / "scenes" / "extra.tscn"
            script_path = Path(tmpdir) / "scripts" / "player.gd"
            result_scene = self.run_cli(["scene", "new", str(scene_path), "--root-type", "Node2D"])
            result_script = self.run_cli(["script", "new", str(script_path), "--extends", "CharacterBody2D", "--class", "Player"])
            self.assertEqual(result_scene.returncode, 0, msg=result_scene.stderr)
            self.assertEqual(result_script.returncode, 0, msg=result_script.stderr)
            self.assertTrue(scene_path.exists())
            self.assertTrue(script_path.exists())

    def test_editor_install_bridge_copies_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(["project", "new", tmpdir, "--name", "Demo"])
            result = self.run_cli(["--json", "--project", tmpdir, "editor", "install-bridge"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(Path(tmpdir, "addons", "cli_anything_godot_bridge", "plugin.cfg").exists())
            project_text = Path(tmpdir, "project.godot").read_text(encoding="utf-8")
            self.assertIn('enabled=PackedStringArray("res://addons/cli_anything_godot_bridge/plugin.cfg")', project_text)

    def test_asset_sprite_with_import_sidecar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(["project", "new", tmpdir, "--name", "Demo"])
            asset_path = Path(tmpdir) / "assets" / "player.png"
            result = self.run_cli(["asset", "sprite", str(asset_path), "--project-dir", tmpdir])
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(asset_path.exists())
            self.assertTrue(Path(f"{asset_path}.import").exists())

    def test_probe_backend_json_uses_backend_probe(self):
        with patch("cli_anything.godot.godot_cli.backend_probe", return_value={"available": True, "executable": "/tmp/godot", "version": "4.5.1"}):
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = dispatch(["--json", "probe", "backend"])
        self.assertEqual(code, 0)
        data = json.loads(stream.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["version"], "4.5.1")

    def test_run_game_fails_when_backend_process_fails(self):
        failed = {"ok": False, "returncode": 7, "stdout": "", "stderr": "scene crashed", "command": "godot"}
        with patch("cli_anything.godot.godot_cli.run_project", return_value=failed):
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = dispatch(["--json", "--project", "/tmp/demo", "run", "game"])
        self.assertEqual(code, 1)
        data = json.loads(stream.getvalue())
        self.assertFalse(data["ok"])
        self.assertIn("Godot run failed", data["error"]["message"])
        self.assertEqual(data["error"]["code"], "backend_process_failed")
        self.assertEqual(data["error"]["details"]["returncode"], 7)
        self.assertEqual(data["error"]["details"]["stderr"], "scene crashed")

    def test_export_pack_fails_when_backend_reports_failure(self):
        failed = {"ok": False, "returncode": 9, "stdout": "", "stderr": "missing preset", "command": "godot"}
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "project.godot").write_text("[application]\nconfig/name=\"Demo\"\n", encoding="utf-8")
            output_path = Path(tmpdir) / "build" / "demo.pck"
            with patch("cli_anything.godot.godot_cli.run_godot", return_value=failed):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = dispatch(["--json", "--project", tmpdir, "export", "pack", "Linux/X11", str(output_path)])
        self.assertEqual(code, 1)
        data = json.loads(stream.getvalue())
        self.assertFalse(data["ok"])
        self.assertIn("Godot pack export failed", data["error"]["message"])
        self.assertEqual(data["error"]["details"]["returncode"], 9)
        self.assertEqual(data["error"]["details"]["stderr"], "missing preset")

    def test_project_option_does_not_persist_session_state(self):
        with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as project_dir:
            result = self.run_cli(
                ["--json", "--project", project_dir, "session", "status"],
                extra_env={"CLI_ANYTHING_GODOT_STATE_DIR": state_dir},
            )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertIsNone(data["current_project"])
