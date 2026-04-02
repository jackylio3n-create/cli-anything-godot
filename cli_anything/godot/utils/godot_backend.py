"""Backend module that wraps the real Godot CLI executable."""

from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
import textwrap
from pathlib import Path


_INSTALL_INSTRUCTIONS = textwrap.dedent("""\
    Godot executable not found.

    Install Godot and ensure one of its CLI binaries is available on PATH.

      Linux:
        sudo apt install godot3   # distro package (often older)
        or use the official Linux binary/AppImage from https://godotengine.org

      macOS:
        brew install --cask godot
        or use the official app from https://godotengine.org

      Windows:
        winget install GodotEngine.GodotEngine
        or use the official installer from https://godotengine.org

    You can also set GODOT_PATH to an explicit executable path.
""")


_GODOT_NAMES = (
    "godot4",
    "godot4.exe",
    "godot",
    "godot.exe",
    "Godot_v4",
    "Godot_v4.exe",
    "Godot_v3",
    "Godot_v3.exe",
)


def find_godot(preferred_path=None):
    """Locate the Godot executable on the current system."""
    if preferred_path and os.path.isfile(preferred_path):
        return os.path.abspath(preferred_path)

    env_path = os.environ.get("GODOT_PATH")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    for name in _GODOT_NAMES:
        which = shutil.which(name)
        if which:
            return os.path.abspath(which)

    system = platform.system()
    if system == "Windows":
        win_patterns = [
            "C:/Program Files/Godot*/Godot*.exe",
            "C:/Program Files (x86)/Godot*/Godot*.exe",
            os.path.expanduser("~/Downloads/Godot*.exe"),
        ]
        for pattern in win_patterns:
            matches = sorted(glob.glob(pattern), reverse=True)
            if matches:
                return os.path.abspath(matches[0])
    elif system == "Darwin":
        mac_paths = [
            "/Applications/Godot.app/Contents/MacOS/Godot",
            "/Applications/Godot_mono.app/Contents/MacOS/Godot",
        ]
        for candidate in mac_paths:
            if os.path.isfile(candidate):
                return candidate
    elif system == "Linux":
        linux_paths = [
            "/usr/bin/godot",
            "/usr/bin/godot4",
            "/usr/local/bin/godot",
            "/usr/local/bin/godot4",
            "/snap/bin/godot",
        ]
        for candidate in linux_paths:
            if os.path.isfile(candidate):
                return candidate

    raise RuntimeError(_INSTALL_INSTRUCTIONS)


def _resolve_project_path(project_dir):
    path = Path(project_dir).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Godot project directory not found: {path}")
    project_file = path / "project.godot"
    if not project_file.is_file():
        raise FileNotFoundError(
            f"project.godot not found in project directory: {path}"
        )
    return str(path)


def run_godot(args, executable=None, cwd=None, env=None, capture_output=True):
    """Run Godot with raw CLI args and return a normalized process dict."""
    godot = find_godot(preferred_path=executable)
    cmd = [godot] + [str(arg) for arg in args]

    env_map = None
    if env:
        env_map = os.environ.copy()
        env_map.update(env)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            cwd=cwd,
            env=env_map,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "command": " ".join(cmd),
        }

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout if capture_output else "",
        "stderr": proc.stderr if capture_output else "",
        "command": " ".join(cmd),
    }


def detect_version(executable=None):
    """Return the installed Godot version string."""
    result = run_godot(["--version"], executable=executable)
    output = (result["stdout"].strip() or result["stderr"].strip())
    if result["ok"] and output:
        return output.splitlines()[0].strip()
    raise RuntimeError(
        f"Failed to read Godot version: {output or 'no output from --version'}"
    )


def probe_backend(executable=None):
    """Probe backend availability and return executable/version details."""
    try:
        resolved = find_godot(preferred_path=executable)
        version = detect_version(executable=resolved)
        return {
            "available": True,
            "executable": resolved,
            "version": version,
        }
    except Exception as exc:
        return {
            "available": False,
            "executable": None,
            "version": None,
            "error": str(exc),
        }


def import_project(project_dir, executable=None):
    """Import project assets with Godot."""
    project_path = _resolve_project_path(project_dir)
    result = run_godot(
        ["--headless", "--path", project_path, "--import", "--quit"],
        executable=executable,
    )
    if result["returncode"] != 0:
        raise RuntimeError(
            f"Godot import failed (exit {result['returncode']}): "
            f"{result['stderr'].strip()[-500:]}"
        )
    return result


def run_project(
    project_dir,
    executable=None,
    headless=False,
    scene_path=None,
    extra_args=None,
):
    """Run a Godot project, optionally selecting scene and extra args."""
    project_path = _resolve_project_path(project_dir)
    args = []
    if headless:
        args.append("--headless")
    args.extend(["--path", project_path])
    if scene_path is not None:
        args.append(str(scene_path))
    if extra_args:
        args.extend(str(arg) for arg in extra_args)
    return run_godot(args, executable=executable)


def export_project(
    project_dir,
    preset,
    output_path,
    mode="release",
    executable=None,
):
    """Export a Godot project with a named preset and output path."""
    if not str(preset).strip():
        raise ValueError("preset must be a non-empty string")
    if mode not in ("release", "debug"):
        raise ValueError("mode must be 'release' or 'debug'")

    project_path = _resolve_project_path(project_dir)
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    export_flag = "--export-release" if mode == "release" else "--export-debug"
    result = run_godot(
        ["--headless", "--path", project_path, export_flag, str(preset), str(output)],
        executable=executable,
    )
    if result["returncode"] != 0:
        raise RuntimeError(
            f"Godot export failed (exit {result['returncode']}): "
            f"{result['stderr'].strip()[-500:]}"
        )
    if not output.exists():
        raise RuntimeError(
            f"Godot export completed without output file: {output}\n"
            f"stderr: {result['stderr'][-500:]}"
        )

    result["output"] = str(output)
    result["file_size"] = output.stat().st_size
    result["method"] = "godot-cli"
    result["format"] = output.suffix.lstrip(".")
    return result


def install_bridge_files(project_dir, source_dir):
    """Copy bridge files from source_dir into project_dir, preserving layout."""
    project_path = Path(project_dir).expanduser().resolve()
    source_path = Path(source_dir).expanduser().resolve()
    if not project_path.is_dir():
        raise FileNotFoundError(f"Godot project directory not found: {project_path}")
    if not source_path.is_dir():
        raise FileNotFoundError(f"Bridge source directory not found: {source_path}")

    installed = []
    for root, _, filenames in os.walk(source_path):
        rel_root = Path(root).relative_to(source_path)
        target_root = project_path / rel_root
        target_root.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            src = Path(root) / name
            dst = target_root / name
            shutil.copy2(src, dst)
            installed.append(str(dst))

    return {
        "project_dir": str(project_path),
        "source_dir": str(source_path),
        "installed_count": len(installed),
        "installed_files": installed,
    }

