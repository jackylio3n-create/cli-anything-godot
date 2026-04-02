---
name: "cli-anything-godot"
description: "Use when an agent needs to create, inspect, run, or export a Godot 2D GDScript project through a structured CLI."
---

# cli-anything-godot

## Purpose

`cli-anything-godot` exposes Godot project authoring and runtime workflows to
AI agents through a REPL-first CLI with JSON output.

## Requirements

- Official Godot editor binary installed
- `GODOT_PATH` set when the executable is not discoverable on `PATH`
- Official export templates installed for executable exports

## Command groups

- `probe`: inspect backend availability and version
- `project`: create and configure a project
- `scene`: create scenes and append nodes
- `script`: generate GDScript files
- `asset`: create simple procedural placeholder assets
- `import`: run Godot import flows
- `run`: launch the game or specific scenes
- `export`: export builds and packs with Godot
- `editor`: install and call the editor bridge scaffold
- `inspect`: list scenes, scripts, and project metadata
- `session`: inspect local CLI session state

## Agent guidance

- Prefer `--json` for programmatic usage.
- Use `project new` before mutating project state.
- Treat `.godot/imported/*` and other derived files as read-only outputs.
- Use `editor install-bridge` before calling editor-only operations.

## Examples

```bash
cli-anything-godot --json probe backend
cli-anything-godot --json project new /tmp/demo_game --name "Demo Game"
cli-anything-godot --json scene new /tmp/demo_game/scenes/main.tscn --root-type Node2D
cli-anything-godot --json script new /tmp/demo_game/scripts/player.gd --class Player --extends CharacterBody2D
cli-anything-godot --json script autoload /tmp/demo_game/scripts/game_state.gd
cli-anything-godot --json asset sprite /tmp/demo_game/assets/player.png --shape circle --project-dir /tmp/demo_game
cli-anything-godot --json --project /tmp/demo_game import run
cli-anything-godot --json --project /tmp/demo_game run game --headless --quit
```
