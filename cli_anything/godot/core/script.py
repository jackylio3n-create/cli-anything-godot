"""Helpers for deterministic GDScript file generation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def generate_gdscript(
    script_file: str | Path,
    *,
    extends: str = "Node",
    class_name: str | None = None,
    tool: bool = False,
    signals: Iterable[str] | None = None,
    body_lines: Iterable[str] | None = None,
) -> Path:
    """Generate a practical GDScript file without editor involvement."""
    script_path = Path(script_file)
    script_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if tool:
        lines.append("@tool")
    lines.append(f"extends {extends}")
    if class_name:
        lines.append(f"class_name {class_name}")
    for signal_name in (signals or ()):
        lines.append(f"signal {signal_name}")
    lines.append("")

    if body_lines is None:
        lines.extend(
            [
                "func _ready() -> void:",
                "\tpass",
                "",
            ]
        )
    else:
        for line in body_lines:
            lines.append(line.rstrip())
        if lines[-1] != "":
            lines.append("")

    script_path.write_text("\n".join(lines), encoding="utf-8")
    return script_path


def generate_autoload_singleton(
    script_file: str | Path,
    *,
    body_lines: Iterable[str] | None = None,
) -> Path:
    """Generate a minimal singleton-style script for autoload usage."""
    default_body = [
        "var state: Dictionary = {}",
        "",
        "func reset() -> void:",
        "\tstate.clear()",
        "",
    ]
    return generate_gdscript(
        script_file,
        extends="Node",
        body_lines=body_lines if body_lines is not None else default_body,
    )


def create_script(script_path, extends_name="Node", class_name=None, body_lines=None):
    """Requested API: generate a simple GDScript file."""
    return generate_gdscript(
        script_path,
        extends=extends_name,
        class_name=class_name,
        body_lines=body_lines,
    )
