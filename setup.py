from __future__ import annotations

import sys


PACKAGE_NAME = "cli-anything-godot"
PACKAGE_VERSION = "0.1.0"


def _handle_metadata_query(argv: list[str]) -> bool:
    if len(argv) != 2:
        return False
    if argv[1] == "--name":
        print(PACKAGE_NAME)
        return True
    if argv[1] == "--version":
        print(PACKAGE_VERSION)
        return True
    return False


if __name__ == "__main__" and _handle_metadata_query(sys.argv):
    raise SystemExit(0)

try:
    from setuptools import find_namespace_packages, setup
except ModuleNotFoundError as exc:
    raise SystemExit("setuptools is required for packaging commands; use `pip install setuptools`.") from exc


setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    description="Agent-oriented CLI harness for Godot game development workflows",
    install_requires=["click>=8.0"],
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    package_data={
        "cli_anything.godot": ["README.md"],
        "cli_anything.godot.bridge": ["README.md", "addons/cli_anything_godot_bridge/*"],
        "cli_anything.godot.tests": ["TEST.md"],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-godot=cli_anything.godot.godot_cli:entrypoint",
        ]
    },
)
