# cli-anything-godot

`cli-anything-godot` is a first-pass CLI-Anything harness for Godot focused on
agent-driven 2D GDScript game workflows.

Current scope:

- Create and inspect Godot projects
- Generate text scenes and scripts
- Create simple procedural placeholder assets
- Run import, play, and export flows through the real Godot executable
- Scaffold an editor bridge plugin for editor-only automation

This harness follows the CLI-Anything pattern:

- one-shot subcommands
- default REPL
- `--json` machine-readable output
- namespace packaging under `cli_anything.godot`

## Install

```bash
cd /root/tool-downloads-20260402/CLI-Anything/godot/agent-harness
pip install -e .
```

## Verify

```bash
cli-anything-godot --help
```

## Backend requirement

The real Godot editor binary is a hard dependency for import, run, and export
operations. Set `GODOT_PATH` if the executable is not already on `PATH`.

Executable exports also require official Godot export templates installed under
the standard Godot export templates directory for the matching version.
