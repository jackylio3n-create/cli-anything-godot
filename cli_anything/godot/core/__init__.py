"""Godot text-model helpers used by the CLI harness."""

from .assets import (
    create_checkerboard_png,
    create_procedural_sprite,
    create_procedural_tone,
    create_solid_color_png,
    write_import_file,
)
from .project import (
    add_autoload,
    add_input_action,
    create_project,
    create_project_scaffold,
    project_info,
    remove_autoload,
    remove_input_action,
    upsert_autoload,
    upsert_input_action,
)
from .scene import ExtResourceRef, add_node, append_node, create_scene, list_nodes
from .script import create_script, generate_autoload_singleton, generate_gdscript

__all__ = [
    "ExtResourceRef",
    "add_autoload",
    "add_input_action",
    "add_node",
    "append_node",
    "create_checkerboard_png",
    "create_procedural_sprite",
    "create_procedural_tone",
    "create_project",
    "create_project_scaffold",
    "create_scene",
    "create_script",
    "create_solid_color_png",
    "generate_autoload_singleton",
    "generate_gdscript",
    "list_nodes",
    "project_info",
    "remove_autoload",
    "remove_input_action",
    "upsert_autoload",
    "upsert_input_action",
    "write_import_file",
]
