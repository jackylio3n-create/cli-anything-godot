# cli-anything-godot

`cli-anything-godot` is an agent-facing command-line harness for building and
testing Godot 2D GDScript projects. It turns common Godot editor workflows into
structured CLI commands so AI agents can create projects, generate scenes and
scripts, produce placeholder assets, run the real Godot backend, and export
build artifacts in a repeatable way.

## Why This Exists

Godot is powerful, but many game-development steps normally happen inside the
graphical editor. That makes it hard for an AI agent to reliably perform long
multi-step work such as:

- creating a new project with the expected `project.godot` files;
- generating text-based `.tscn` scenes and `.gd` scripts;
- adding input actions, autoload singletons, and nodes;
- creating temporary art/audio assets for early prototypes;
- importing, running, and exporting through the official Godot executable;
- coordinating editor-only automation through a simple bridge protocol.

This project exposes those operations as deterministic commands with optional
JSON output, making Godot projects easier for agents, scripts, and CI jobs to
inspect and modify.

## Core Features

- `project`: create and inspect Godot projects, input actions, and autoloads.
- `scene`: create text scenes and append nodes.
- `script`: generate GDScript files and autoload singleton templates.
- `asset`: create lightweight procedural PNG sprites and WAV tones.
- `import`: run Godot import flows.
- `run`: launch a project or scene through Godot.
- `export`: export releases, debug builds, or packs using Godot export presets.
- `editor`: install and call an editor bridge plugin.
- `inspect`: list project files and metadata.
- `session`: preserve local REPL state for multi-step agent workflows.

## Agent Workflow

The typical agent flow is:

1. Probe the Godot backend.
2. Create a new project scaffold.
3. Generate scenes, scripts, and placeholder assets.
4. Configure project inputs and autoloads.
5. Run import and play/test flows through Godot.
6. Export the project when templates are available.

Because commands can emit machine-readable JSON, an agent can chain these steps,
inspect each result, and recover from failures without relying on brittle editor
UI automation.

## Install

From the repository root:

```bash
pip install -e .
```

Then verify the entrypoint:

```bash
cli-anything-godot --help
```

## Godot Backend Requirement

The official Godot editor executable is required for import, run, and export
operations. If the executable is not discoverable on `PATH`, set `GODOT_PATH`:

```bash
export GODOT_PATH=/path/to/Godot
```

Executable exports also require the official Godot export templates for the
matching Godot version.

## Quick Start

Create a project:

```bash
cli-anything-godot --json project new /tmp/demo_game --name "Demo Game"
```

Generate a scene:

```bash
cli-anything-godot --json scene new /tmp/demo_game/scenes/main.tscn --root-type Node2D
```

Generate a player script:

```bash
cli-anything-godot --json script new /tmp/demo_game/scripts/player.gd --extends CharacterBody2D --class Player
```

Create a placeholder sprite and matching import sidecar:

```bash
cli-anything-godot --json asset sprite /tmp/demo_game/assets/player.png --shape circle --project-dir /tmp/demo_game
```

Run Godot import:

```bash
cli-anything-godot --json --project /tmp/demo_game import run
```

Run the project headlessly:

```bash
cli-anything-godot --json --project /tmp/demo_game run game --headless --quit
```

## REPL

Running the command without arguments starts the interactive REPL:

```bash
cli-anything-godot
```

Useful REPL commands include:

- `use-project <path>`: persist the current project path.
- `current-project`: show the active project.
- `status`: show session state.
- `history [limit]`: show recent commands.
- `state-path`: show where session state is stored.

The REPL also supports `@project` path expansion after `use-project` is set.

## Editor Bridge

The repository includes a scaffolded Godot editor plugin at:

```text
cli_anything/godot/bridge/addons/cli_anything_godot_bridge
```

The bridge uses JSON request and response files. It is intended for editor-only
automation that cannot be handled by direct text-file edits or normal Godot CLI
flags.

Install the bridge into a project:

```bash
cli-anything-godot --json --project /tmp/demo_game editor install-bridge
```

## Development

Run the test suite with:

```bash
python -m unittest discover cli_anything/godot/tests
```

The tests cover project creation, scene/script generation, procedural assets,
the CLI entrypoint, REPL behavior, and editor bridge installation.

## Current Scope

This is a first-pass Godot harness focused on 2D GDScript workflows and
agent-driven automation. It intentionally edits text-first Godot project files
and treats generated/imported Godot cache files as derived outputs.
