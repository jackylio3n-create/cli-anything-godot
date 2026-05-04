import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HAS_GODOT = bool(os.environ.get("GODOT_PATH")) or bool(shutil.which("godot")) or bool(shutil.which("godot4"))


def resolve_cli() -> list[str]:
    installed = shutil.which("cli-anything-godot")
    if installed:
        return [installed]
    return [sys.executable, "-m", "cli_anything.godot"]


class HarnessE2ETests(unittest.TestCase):
    CLI_BASE = resolve_cli()

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, env=env, timeout=30)

    def test_create_project_scene_script_and_asset_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            commands = [
                ["--json", "project", "new", tmpdir, "--name", "Demo"],
                ["--json", "scene", "new", str(Path(tmpdir) / "scenes" / "level_1.tscn"), "--root-type", "Node2D"],
                ["--json", "script", "new", str(Path(tmpdir) / "scripts" / "player.gd"), "--extends", "CharacterBody2D", "--class", "Player"],
                ["--json", "script", "autoload", str(Path(tmpdir) / "scripts" / "game_state.gd")],
                ["--json", "asset", "tone", str(Path(tmpdir) / "assets" / "jump.wav"), "--frequency", "660"],
                ["--json", "asset", "sprite", str(Path(tmpdir) / "assets" / "player.png"), "--project-dir", tmpdir],
                ["--json", "--project", tmpdir, "inspect", "files"],
            ]
            last = None
            for command in commands:
                last = self.run_cli(command)
                self.assertEqual(last.returncode, 0, msg=last.stderr)
            data = json.loads(last.stdout)
            self.assertIn("project.godot", data["configs"])
            self.assertIn("scenes/level_1.tscn", data["scenes"])
            self.assertIn("scripts/player.gd", data["scripts"])
            self.assertIn("assets/jump.wav", data["assets"])
            self.assertIn("assets/player.png.import", data["resources"])


@unittest.skipUnless(HAS_GODOT, "Godot executable not available in this environment")
class BackendE2ETests(unittest.TestCase):
    CLI_BASE = resolve_cli()

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, env=env, timeout=120)

    def test_probe_backend(self):
        result = self.run_cli(["--json", "probe", "backend"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["version"])

    def test_import_run_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            created = self.run_cli(["project", "new", tmpdir, "--name", "BackendDemo"])
            self.assertEqual(created.returncode, 0, msg=created.stderr)
            imported = self.run_cli(["--json", "--project", tmpdir, "import", "run"])
            self.assertEqual(imported.returncode, 0, msg=imported.stderr)
            data = json.loads(imported.stdout)
            self.assertTrue(data["ok"])
