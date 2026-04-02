# TEST.md

## Test Inventory Plan

- `test_core.py`: 12 unit tests planned
- `test_cli_entrypoint.py`: 9 CLI contract tests planned
- `test_full_e2e.py`: 3 end-to-end tests planned

## Unit Test Plan

- `project.py`
  - Create project tree and `project.godot`
  - Add input actions and autoloads
  - Validate deterministic config output
- `scene.py`
  - Create empty scenes
  - Append nodes and preserve valid node hierarchy
- `script.py`
  - Generate GDScript files with class name and extends header
  - Generate singleton-ready autoload scripts without conflicting `class_name`
- `assets.py`
  - Generate procedural SVG sprites
  - Generate procedural WAV assets
- `godot_backend.py`
  - Resolve executable candidates
  - Build import, run, and export commands

## E2E Test Plan

- Create a project through the CLI and verify key files exist
- Create a scene and script and verify files are valid text assets
- Generate placeholder assets and verify they exist and are non-empty
- If Godot is installed, run import and a headless launch
- If Godot is installed, probe the real backend and verify structured output

## Realistic Workflow Scenarios

- **Minimal playable scaffold**
  - Simulates creating a new 2D prototype project
  - Operations chained: project new, scene new, script new, asset sprite, inspect
  - Verified: key files exist and contain expected values

- **Runtime smoke**
  - Simulates running a generated project with the real Godot backend
  - Operations chained: project new, import run, run game
  - Verified: backend exit status, structured command output, artifact paths

## Test Results

Environment notes:

- `pytest` was not available in the base environment, so execution used `python3 -m unittest`.
- Live backend verification used the official Godot 4.5.1 Linux binary via `GODOT_PATH`.
- Executable export verification used the official Godot 4.5.1 export templates installed under `/root/.local/share/godot/export_templates/4.5.1.stable`.

Command output:

```text
$ GODOT_PATH=/root/tool-downloads-20260402/godot-runtime/Godot_v4.5.1-stable_linux.x86_64 .venv/bin/python -m unittest cli_anything.godot.tests.test_core cli_anything.godot.tests.test_cli_entrypoint cli_anything.godot.tests.test_full_e2e -v
Ran 19 tests in 11.086s
OK
```

```text
$ python3 -m compileall cli_anything/godot
Compilation completed successfully.
```

```text
$ .venv/bin/python -m pip install -e .
Successfully installed cli-anything-godot-0.1.0 click-8.3.1
```

```text
$ .venv/bin/cli-anything-godot --help
Usage: cli-anything-godot [OPTIONS] COMMAND [ARGS]...
```

```text
$ GODOT_PATH=/root/tool-downloads-20260402/godot-runtime/Godot_v4.5.1-stable_linux.x86_64 .venv/bin/cli-anything-godot --json --project /tmp/cli-anything-godot-live3 export pack "Linux/X11" /tmp/cli-anything-godot-live3/build/live3.pck --overwrite
ok: true
output: /tmp/cli-anything-godot-live3/build/live3.pck
```

```text
$ GODOT_PATH=/root/tool-downloads-20260402/godot-runtime/Godot_v4.5.1-stable_linux.x86_64 .venv/bin/cli-anything-godot --json --project /tmp/cli-anything-godot-live3 export release "Linux/X11" /tmp/cli-anything-godot-live3/build/live3.x86_64 --overwrite
ok: true
output: /tmp/cli-anything-godot-live3/build/live3.x86_64
file_size: 70158584
```

```text
$ xvfb-run -a Godot_v4.5.1-stable_linux.x86_64 --editor --path /tmp/cli-bridge-check --quit-after 1800
$ .venv/bin/cli-anything-godot --json --project /tmp/cli-bridge-check editor ping
ok: true
```

## Summary Statistics

- Total tests run: 19
- Passed: 19
- Skipped: 0
- Failed: 0

## Coverage Notes

- Covered:
  - Project scaffold generation
  - Input map and autoload edits
  - Scene creation and node append
  - GDScript generation and singleton-safe autoload generation
  - Procedural PNG and WAV asset generation
  - CLI help, REPL exit, bridge installation, and file workflow smoke
  - Editable install into a local virtual environment
  - Live Godot backend probe, import, headless run, pack export, and release export
  - Live editor-bridge request/response handling inside an actual Godot editor session
