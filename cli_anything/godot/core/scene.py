"""Text model helpers for Godot .tscn scenes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from .project import format_variant


EXT_RESOURCE_RE = re.compile(
    r'^\[ext_resource\s+type="(?P<type>[^"]+)"\s+path="(?P<path>[^"]+)"\s+id="(?P<id>\d+)"\]$',
    re.MULTILINE,
)
NODE_RE = re.compile(r'^\[node\s+(?P<body>.+)\]$')
NODE_KV_RE = re.compile(r'(\w+)="([^"]*)"')


@dataclass(frozen=True)
class ExtResourceRef:
    """Pointer to an external resource that should be added to the scene."""

    path: str
    resource_type: str


def _next_ext_resource_id(text: str) -> int:
    ids = [int(match.group("id")) for match in EXT_RESOURCE_RE.finditer(text)]
    return (max(ids) + 1) if ids else 1


def _find_or_add_ext_resource(text: str, ref: ExtResourceRef) -> tuple[str, int]:
    for match in EXT_RESOURCE_RE.finditer(text):
        if match.group("path") == ref.path and match.group("type") == ref.resource_type:
            return text, int(match.group("id"))

    new_id = _next_ext_resource_id(text)
    ext_line = f'[ext_resource type="{ref.resource_type}" path="{ref.path}" id="{new_id}"]\n'
    lines = text.splitlines(keepends=True)
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("[node "):
            insert_at = i
            break
    lines.insert(insert_at, ext_line)
    return "".join(lines), new_id


def create_scene(scene_path, root_type="Node2D", root_name="Main"):
    """Create a minimal deterministic ``.tscn`` scene."""
    output = Path(scene_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            [
                "[gd_scene format=3]\n",
                "\n",
                f'[node name="{root_name}" type="{root_type}"]\n',
                "\n",
            ]
        ),
        encoding="utf-8",
    )
    return output


def add_node(scene_path, name, node_type, parent=".", properties=None):
    """Append a node block to an existing text scene file."""
    scene_file = Path(scene_path)
    text = scene_file.read_text(encoding="utf-8")
    if not text.lstrip().startswith("[gd_scene "):
        raise ValueError(f"Not a valid Godot scene file: {scene_path}")

    prop_lines: list[str] = []
    work_text = text
    for key, value in (properties or {}).items():
        if isinstance(value, ExtResourceRef):
            work_text, ext_id = _find_or_add_ext_resource(work_text, value)
            prop_lines.append(f'{key} = ExtResource("{ext_id}")')
        else:
            prop_lines.append(f"{key} = {format_variant(value)}")

    block = [f'[node name="{name}" type="{node_type}" parent="{parent}"]']
    block.extend(prop_lines)
    block.append("")

    if not work_text.endswith("\n"):
        work_text += "\n"
    if not work_text.endswith("\n\n"):
        work_text += "\n"
    work_text += "\n".join(block) + "\n"

    scene_file.write_text(work_text, encoding="utf-8")
    return scene_file


def list_nodes(scene_path):
    """Return node blocks in source order."""
    text = Path(scene_path).read_text(encoding="utf-8")
    nodes = []
    for line in text.splitlines():
        match = NODE_RE.match(line.strip())
        if not match:
            continue
        attrs = {k: v for k, v in NODE_KV_RE.findall(match.group("body"))}
        nodes.append(
            {
                "name": attrs.get("name"),
                "type": attrs.get("type"),
                "parent": attrs.get("parent", ""),
            }
        )
    return nodes


def append_node(
    scene_file: str | Path,
    *,
    name: str,
    node_type: str,
    parent: str = ".",
    properties: Mapping[str, Any] | None = None,
) -> Path:
    """Backward-compatible internal alias."""
    return add_node(scene_file, name, node_type, parent=parent, properties=properties)
