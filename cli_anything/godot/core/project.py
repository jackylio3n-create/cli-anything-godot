"""Schema-aware text helpers for Godot project config files."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, MutableMapping


def _quote_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_dict(value: MutableMapping[str, Any]) -> str:
    items: list[str] = []
    for key in sorted(value.keys()):
        items.append(f"{_quote_string(str(key))}: {format_variant(value[key])}")
    return "{" + ", ".join(items) + "}"


def format_variant(value: Any) -> str:
    """Serialize a Python value into a practical Godot text variant literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        return _quote_string(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return _format_dict(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(format_variant(item) for item in value) + "]"
    raise TypeError(f"Unsupported variant type: {type(value)!r}")


def format_packed_string_array(values: Iterable[str]) -> str:
    joined = ", ".join(_quote_string(v) for v in values)
    return f"PackedStringArray({joined})"


def parse_packed_string_array(value: str | None) -> list[str]:
    if value is None:
        return []
    text = value.strip()
    if not text.startswith("PackedStringArray(") or not text.endswith(")"):
        return []
    body = text[len("PackedStringArray(") : -1]
    items: list[str] = []
    for raw in re.findall(r'"((?:[^"\\\\]|\\\\.)*)"', body):
        items.append(bytes(raw, "utf-8").decode("unicode_escape"))
    return items


class GodotConfig:
    """Minimal deterministic parser/writer for project.godot-like files."""

    def __init__(self) -> None:
        self._sections: "OrderedDict[str, OrderedDict[str, str]]" = OrderedDict()

    @classmethod
    def from_text(cls, text: str) -> "GodotConfig":
        cfg = cls()
        current_section: str | None = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                cfg._sections.setdefault(current_section, OrderedDict())
                continue
            if current_section is None or "=" not in raw_line:
                continue
            key, value = raw_line.split("=", 1)
            cfg._sections[current_section][key.strip()] = value.strip()
        return cfg

    @classmethod
    def from_path(cls, path: str | Path) -> "GodotConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_text(p.read_text(encoding="utf-8"))

    def to_text(self) -> str:
        chunks: list[str] = []
        for section, kv in self._sections.items():
            chunks.append(f"[{section}]")
            for key, value in kv.items():
                chunks.append(f"{key}={value}")
            chunks.append("")
        return "\n".join(chunks).rstrip() + "\n"

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_text(), encoding="utf-8")
        return p

    def set(self, section: str, key: str, value: str) -> None:
        self._sections.setdefault(section, OrderedDict())[key] = value

    def ensure_section(self, section: str) -> None:
        self._sections.setdefault(section, OrderedDict())

    def remove(self, section: str, key: str) -> bool:
        section_values = self._sections.get(section)
        if not section_values or key not in section_values:
            return False
        del section_values[key]
        if not section_values:
            del self._sections[section]
        return True

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        return self._sections.get(section, {}).get(key, default)

    def keys(self, section: str) -> list[str]:
        return list(self._sections.get(section, {}).keys())


def create_project_scaffold(
    project_dir: str | Path,
    project_name: str,
    main_scene: str = "res://scenes/Main.tscn",
    config_features: Iterable[str] = ("4.2",),
) -> dict[str, Path]:
    """Create a deterministic text scaffold for a Godot project."""
    root = Path(project_dir)
    root.mkdir(parents=True, exist_ok=True)
    for subdir in ("scenes", "scripts", "assets"):
        (root / subdir).mkdir(exist_ok=True)

    project_cfg = GodotConfig()
    project_cfg.set("application", "config/name", format_variant(project_name))
    project_cfg.set("application", "run/main_scene", format_variant(main_scene))
    project_cfg.set("application", "config/features", format_packed_string_array(config_features))
    project_cfg.set("rendering", "renderer/rendering_method", format_variant("forward_plus"))
    project_path = project_cfg.save(root / "project.godot")

    export_cfg = GodotConfig()
    export_cfg.set("preset.0", "name", format_variant("Linux/X11"))
    export_cfg.set("preset.0", "platform", format_variant("Linux/X11"))
    export_cfg.set("preset.0", "runnable", format_variant(True))
    export_cfg.set("preset.0", "export_filter", format_variant("all_resources"))
    export_cfg.set("preset.0", "include_filter", format_variant(""))
    export_cfg.set("preset.0", "exclude_filter", format_variant(""))
    export_cfg.set("preset.0", "export_path", format_variant(""))
    export_cfg.set("preset.0.options", "binary_format/architecture", format_variant("x86_64"))
    export_path = export_cfg.save(root / "export_presets.cfg")

    return {
        "project_dir": root,
        "project_godot": project_path,
        "export_presets": export_path,
    }


def set_project_setting(project_file: str | Path, section: str, key: str, value: Any) -> Path:
    cfg = GodotConfig.from_path(project_file)
    cfg.set(section, key, format_variant(value))
    return cfg.save(project_file)


def remove_project_setting(project_file: str | Path, section: str, key: str) -> bool:
    cfg = GodotConfig.from_path(project_file)
    removed = cfg.remove(section, key)
    if removed:
        cfg.save(project_file)
    return removed


def upsert_input_action(
    project_file: str | Path,
    action_name: str,
    *,
    deadzone: float = 0.5,
    events: list[dict[str, Any]] | None = None,
) -> Path:
    """Create or replace one InputMap action entry in ``project.godot``."""
    cfg = GodotConfig.from_path(project_file)
    payload = {
        "deadzone": deadzone,
        "events": events or [],
    }
    cfg.set("input", action_name, format_variant(payload))
    return cfg.save(project_file)


def remove_input_action(project_file: str | Path, action_name: str) -> bool:
    cfg = GodotConfig.from_path(project_file)
    removed = cfg.remove("input", action_name)
    if removed:
        cfg.save(project_file)
    return removed


def upsert_autoload(
    project_file: str | Path,
    name: str,
    script_path: str,
    *,
    singleton: bool = True,
) -> Path:
    """Create or replace one autoload entry in ``project.godot``."""
    normalized = script_path if script_path.startswith("res://") else f"res://{script_path.lstrip('/')}"
    payload = f"*{normalized}" if singleton else normalized
    cfg = GodotConfig.from_path(project_file)
    cfg.set("autoload", name, format_variant(payload))
    return cfg.save(project_file)


def remove_autoload(project_file: str | Path, name: str) -> bool:
    cfg = GodotConfig.from_path(project_file)
    removed = cfg.remove("autoload", name)
    if removed:
        cfg.save(project_file)
    return removed


def create_project(project_dir, name, main_scene="res://scenes/main.tscn"):
    """Requested API: create a practical Godot text-project scaffold."""
    return create_project_scaffold(project_dir, name, main_scene=main_scene)


def project_info(project_dir):
    """Requested API: summarize project.godot and export_presets.cfg state."""
    root = Path(project_dir)
    project_file = root / "project.godot"
    export_file = root / "export_presets.cfg"
    cfg = GodotConfig.from_path(project_file)
    return {
        "project_dir": root,
        "project_file": project_file,
        "project_exists": project_file.exists(),
        "export_presets_file": export_file,
        "export_presets_exists": export_file.exists(),
        "name": cfg.get("application", "config/name"),
        "main_scene": cfg.get("application", "run/main_scene"),
        "autoloads": sorted(cfg.keys("autoload")),
        "input_actions": sorted(cfg.keys("input")),
    }


def add_input_action(project_dir, action_name, keys):
    """Requested API: add/replace one InputMap action using simple key names."""
    events = [{"type": "key", "keycode": str(key)} for key in (keys or [])]
    project_file = Path(project_dir) / "project.godot"
    return upsert_input_action(project_file, action_name, events=events)


def add_autoload(project_dir, name, path):
    """Requested API: add/replace one autoload singleton."""
    project_file = Path(project_dir) / "project.godot"
    return upsert_autoload(project_file, name, path, singleton=True)


def upsert_enabled_editor_plugin(project_file: str | Path, plugin_ref: str) -> Path:
    cfg = GodotConfig.from_path(project_file)
    existing = parse_packed_string_array(cfg.get("editor_plugins", "enabled"))
    normalized = plugin_ref if plugin_ref.startswith("res://") else f"res://{plugin_ref.lstrip('/')}"
    merged = [item for item in existing if item != normalized]
    merged.append(normalized)
    cfg.set("editor_plugins", "enabled", format_packed_string_array(merged))
    return cfg.save(project_file)
