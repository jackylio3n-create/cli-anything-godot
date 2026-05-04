# cli-anything-godot

> Agent-ready Godot automation for 2D GDScript projects.
>
> 面向 AI Agent 的 Godot 自动化开发工具，聚焦 2D GDScript 项目创建、编辑、运行与导出。

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Godot](https://img.shields.io/badge/Godot-4.x-478CBF?style=flat-square&logo=godot-engine&logoColor=white)](https://godotengine.org/)
[![CLI](https://img.shields.io/badge/Interface-CLI%20%2B%20JSON-222222?style=flat-square)](#quick-start--快速开始)
[![Agent Workflow](https://img.shields.io/badge/Built%20for-AI%20Agents-2F855A?style=flat-square)](#agent-workflow--agent-工作流)

`cli-anything-godot` turns common Godot editor workflows into deterministic CLI
commands. It lets agents and scripts create projects, generate scenes and
GDScript files, produce placeholder assets, run the real Godot backend, and
export builds through a machine-readable command surface.

`cli-anything-godot` 将 Godot 编辑器里的常见工作流封装成可重复执行的命令行能力。AI
Agent 可以通过它创建项目、生成场景和 GDScript 脚本、制作占位素材、调用真实 Godot
后端运行项目，并以 JSON 结果继续编排后续步骤。

## Contents / 目录

- [Why This Exists / 项目定位](#why-this-exists--项目定位)
- [Core Features / 核心能力](#core-features--核心能力)
- [Agent Workflow / Agent 工作流](#agent-workflow--agent-工作流)
- [Install / 安装](#install--安装)
- [Quick Start / 快速开始](#quick-start--快速开始)
- [REPL](#repl)
- [Editor Bridge / 编辑器桥接](#editor-bridge--编辑器桥接)
- [Development / 开发验证](#development--开发验证)

## Why This Exists / 项目定位

Godot is powerful, but many game-development tasks normally rely on editor UI
operations. That is inconvenient for AI agents because UI automation is fragile,
hard to inspect, and difficult to compose into long chains.

Godot 很强，但很多开发动作默认依赖图形编辑器。对 AI Agent 来说，这类 UI 操作不稳定，
也不容易检查执行结果，更难串成连续的长链任务。

This project solves that by exposing a text-first command layer for common
Godot 2D workflows.

这个项目的核心目标是提供一个面向文本和命令行的 Godot 自动化层。

| English | 中文 |
| --- | --- |
| Create a valid Godot project scaffold. | 创建可用的 Godot 项目结构。 |
| Generate `.tscn` scenes and `.gd` scripts. | 生成 `.tscn` 场景和 `.gd` 脚本。 |
| Add nodes, input actions, and autoload singletons. | 添加节点、输入动作和 autoload 单例。 |
| Create temporary PNG/WAV assets for prototypes. | 生成用于原型开发的 PNG/WAV 占位素材。 |
| Import, run, and export through the official Godot executable. | 通过官方 Godot 可执行文件执行导入、运行和导出。 |
| Use JSON output so agents can reason over each step. | 输出 JSON，便于 Agent 读取结果并继续推理。 |

## Core Features / 核心能力

| Command group | English | 中文 |
| --- | --- | --- |
| `probe` | Inspect Godot backend availability and version. | 检查 Godot 后端是否可用以及版本信息。 |
| `project` | Create projects and configure inputs/autoloads. | 创建项目，并配置输入动作与 autoload。 |
| `scene` | Create text scenes and append nodes. | 创建文本场景并追加节点。 |
| `script` | Generate GDScript files and singleton templates. | 生成 GDScript 文件和单例模板。 |
| `asset` | Create lightweight procedural sprites and tones. | 生成轻量级程序化图片和音频占位资源。 |
| `import` | Run Godot import flows. | 执行 Godot 导入流程。 |
| `run` | Launch a project or scene through Godot. | 通过 Godot 启动项目或场景。 |
| `export` | Export builds and packs from presets. | 基于导出预设生成构建或资源包。 |
| `editor` | Install and call the editor bridge plugin. | 安装并调用编辑器桥接插件。 |
| `inspect` | List project files and metadata. | 查看项目文件和元数据。 |
| `session` | Preserve local REPL state. | 保存本地 REPL 会话状态。 |

## Agent Workflow / Agent 工作流

A typical long-chain agent task can follow this sequence:

一个典型的长链 Agent 任务可以按下面流程执行：

```text
Probe Godot
  -> Create project
  -> Generate scenes/scripts/assets
  -> Configure inputs and autoloads
  -> Import project
  -> Run or test scene
  -> Export build
```

Because each command can return structured JSON, an agent can inspect success
states, paths, errors, and generated artifacts before choosing the next action.
This makes the project suitable for multi-step AI workflows and for splitting
work across specialized agents, such as one agent for scene structure, one for
GDScript generation, and one for verification/export.

由于命令支持结构化 JSON 输出，Agent 可以在每一步读取成功状态、路径、错误和产物信息，
再决定下一步操作。这让它适合长链 AI 工作流，也适合多 Agent 协作，例如一个 Agent
负责场景结构，一个 Agent 负责脚本逻辑，另一个 Agent 负责运行验证和导出。

## Install / 安装

From the repository root:

在仓库根目录执行：

```bash
pip install -e .
```

Verify the CLI:

验证命令入口：

```bash
cli-anything-godot --help
```

### Godot Backend / Godot 后端

The official Godot editor executable is required for import, run, and export
operations. If it is not on `PATH`, set `GODOT_PATH`:

执行导入、运行和导出时需要官方 Godot 编辑器可执行文件。如果系统 `PATH` 找不到 Godot，
请设置 `GODOT_PATH`：

```bash
export GODOT_PATH=/path/to/Godot
```

Executable exports also require official Godot export templates for the matching
Godot version.

导出可执行文件还需要安装与 Godot 版本匹配的官方导出模板。

## Quick Start / 快速开始

Create a project:

创建项目：

```bash
cli-anything-godot --json project new /tmp/demo_game --name "Demo Game"
```

Generate a main scene:

生成主场景：

```bash
cli-anything-godot --json scene new /tmp/demo_game/scenes/main.tscn --root-type Node2D
```

Generate a player script:

生成玩家脚本：

```bash
cli-anything-godot --json script new /tmp/demo_game/scripts/player.gd --extends CharacterBody2D --class Player
```

Create a placeholder sprite and matching import sidecar:

生成占位图片和对应的导入配置：

```bash
cli-anything-godot --json asset sprite /tmp/demo_game/assets/player.png --shape circle --project-dir /tmp/demo_game
```

Run Godot import:

执行 Godot 导入：

```bash
cli-anything-godot --json --project /tmp/demo_game import run
```

Run the project headlessly:

以无界面方式运行项目：

```bash
cli-anything-godot --json --project /tmp/demo_game run game --headless --quit
```

## REPL

Running the command without arguments starts the interactive REPL:

不带参数运行会进入交互式 REPL：

```bash
cli-anything-godot
```

Useful REPL commands / 常用 REPL 命令：

| Command | English | 中文 |
| --- | --- | --- |
| `use-project <path>` | Persist the current project path. | 保存当前项目路径。 |
| `current-project` | Show the active project. | 查看当前项目。 |
| `status` | Show session state. | 查看会话状态。 |
| `history [limit]` | Show recent commands. | 查看最近命令。 |
| `state-path` | Show where session state is stored. | 查看会话状态文件路径。 |

The REPL supports `@project` path expansion after `use-project` is set.

设置 `use-project` 后，REPL 支持使用 `@project` 展开当前项目路径。

## Editor Bridge / 编辑器桥接

The repository includes a scaffolded Godot editor plugin:

仓库内包含一个 Godot 编辑器插件脚手架：

```text
cli_anything/godot/bridge/addons/cli_anything_godot_bridge
```

The bridge uses JSON request and response files. It is intended for editor-only
automation that cannot be handled by direct text-file edits or normal Godot CLI
flags.

桥接插件通过 JSON 请求/响应文件通信，适合处理无法仅靠文本编辑或普通 Godot CLI 参数完成的
编辑器侧自动化任务。

Install the bridge into a project:

安装桥接插件到项目中：

```bash
cli-anything-godot --json --project /tmp/demo_game editor install-bridge
```

## Development / 开发验证

Run the test suite:

运行测试：

```bash
python3 -m unittest discover cli_anything/godot/tests
```

The tests cover project creation, scene/script generation, procedural assets,
the CLI entrypoint, REPL behavior, and editor bridge installation.

测试覆盖项目创建、场景/脚本生成、程序化素材、CLI 入口、REPL 行为和编辑器桥接安装。

## Current Scope / 当前范围

This is a first-pass Godot harness focused on 2D GDScript workflows and
agent-driven automation. It intentionally edits text-first Godot project files
and treats generated/imported Godot cache files as derived outputs.

这是一个面向 2D GDScript 和 Agent 自动化的第一版 Godot 工具层。它优先编辑文本形式的
Godot 项目文件，并把 Godot 生成的导入缓存视为派生产物。
