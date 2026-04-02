# GODOT.md

## Backend

- Real backend: official Godot editor executable
- Runtime env var: `GODOT_PATH`
- Expected command surface: `--headless`, `--import`, `--export-release`,
  `--export-debug`, `--export-pack`, `--path`, `--scene`, `--script`

## Primary authoring surfaces

- `project.godot`
- `export_presets.cfg`
- `*.import`
- `*.tscn`
- `*.tres`
- `.uid`
- `*.gd`

## Explicitly excluded as primary edit targets

- `.godot/imported/*`
- `.godot/uid_cache.bin`
- `.scn`
- `.res`

## First-pass command groups

- `project`
- `scene`
- `script`
- `asset`
- `run`
- `import`
- `export`
- `editor`
- `inspect`
- `session`
