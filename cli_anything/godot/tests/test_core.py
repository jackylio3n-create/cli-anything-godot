import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli_anything.godot.bridge_client import bridge_paths
from cli_anything.godot.core import (
    add_autoload,
    add_input_action,
    add_node,
    create_procedural_sprite,
    create_procedural_tone,
    create_project,
    create_scene,
    create_script,
    list_nodes,
    project_info,
)


class ProjectCoreTests(unittest.TestCase):
    def test_create_project_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_project(tmpdir, "Demo")
            self.assertTrue((Path(tmpdir) / "project.godot").exists())
            self.assertTrue((Path(tmpdir) / "export_presets.cfg").exists())
            self.assertEqual(result["project_dir"], Path(tmpdir))

    def test_add_input_action_and_autoload_are_reflected_in_project_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_project(tmpdir, "Demo")
            add_input_action(tmpdir, "move_left", ["KEY_A", "KEY_LEFT"])
            add_autoload(tmpdir, "GameState", "res://scripts/game_state.gd")
            info = project_info(tmpdir)
            self.assertIn("move_left", info["input_actions"])
            self.assertIn("GameState", info["autoloads"])


class SceneCoreTests(unittest.TestCase):
    def test_create_scene_and_add_node(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scene_path = Path(tmpdir) / "scenes" / "main.tscn"
            create_scene(scene_path, root_type="Node2D", root_name="Main")
            add_node(scene_path, "Player", "CharacterBody2D", properties={"speed": "240"})
            nodes = list_nodes(scene_path)
            self.assertEqual(nodes[0]["name"], "Main")
            self.assertEqual(nodes[1]["name"], "Player")
            self.assertEqual(nodes[1]["type"], "CharacterBody2D")


class ScriptAndAssetCoreTests(unittest.TestCase):
    def test_create_script_writes_expected_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "scripts" / "player.gd"
            create_script(script_path, extends_name="CharacterBody2D", class_name="Player")
            text = script_path.read_text(encoding="utf-8")
            self.assertIn("extends CharacterBody2D", text)
            self.assertIn("class_name Player", text)

    def test_create_procedural_sprite_writes_png_signature(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sprite_path = Path(tmpdir) / "assets" / "player.png"
            create_procedural_sprite(sprite_path, shape="circle", size=32)
            self.assertTrue(sprite_path.exists())
            self.assertEqual(sprite_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_create_procedural_tone_writes_wav_signature(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tone_path = Path(tmpdir) / "assets" / "jump.wav"
            create_procedural_tone(tone_path, frequency=880, duration_ms=100)
            self.assertTrue(tone_path.exists())
            self.assertEqual(tone_path.read_bytes()[:4], b"RIFF")


class BridgePathTests(unittest.TestCase):
    def test_bridge_paths_are_project_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = bridge_paths(tmpdir)
            self.assertTrue(str(paths["request_path"]).startswith(tmpdir))
            self.assertTrue(str(paths["response_path"]).startswith(tmpdir))

    def test_bridge_paths_honor_documented_env_vars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            request_path = Path(tmpdir) / "requests" / "request.json"
            response_path = Path(tmpdir) / "responses" / "response.json"
            with patch.dict(
                "os.environ",
                {
                    "CLI_ANYTHING_GODOT_REQUEST": str(request_path),
                    "CLI_ANYTHING_GODOT_RESPONSE": str(response_path),
                    "CLI_ANYTHING_GODOT_STATE_DIR": "res://bridge_state",
                },
            ):
                paths = bridge_paths(tmpdir)
        self.assertEqual(paths["state_dir"], Path(tmpdir) / "bridge_state")
        self.assertEqual(paths["request_path"], request_path)
        self.assertEqual(paths["response_path"], response_path)
