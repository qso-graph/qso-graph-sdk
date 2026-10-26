# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""Where QGSDK puts things under its prefix, and the environment the chosen profiles need.

Everything lives under one directory (the prefix), so removing QGSDK is deleting a folder: nothing is
written into the system, and no admin rights are needed.

    <prefix>/python/                    QGSDK's own Python (from the bootstrap)
    <prefix>/qgsdk-profiles.json        the profiles installed here
    <prefix>/qgsdk-installed.json       what was installed, component by component
    <prefix>/Qt/<qt version>/<dir>/     Qt, as aqtinstall lays it out (logger)
    <prefix>/Qt/Tools/...               the compiler, CMake and Ninja (logger)
    <prefix>/tools/<name>/              tools from elsewhere: NSIS, uv, Node.js, Go, ... (manifest.json's "downloads")
    <prefix>/uv/                        the Pythons and cache uv uses (mcp)
    <prefix>/rust/                      rustup and cargo, and the Rust toolchain (desktop)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .manifest import Profile, Qt

PROFILES = "qgsdk-profiles.json"


def qt_root(prefix: Path) -> Path:
    return prefix / "Qt"


def qt_dir(prefix: Path, qt: Qt) -> Path:
    """The Qt installation CMake finds Qt6 in (CMAKE_PREFIX_PATH)."""
    return qt_root(prefix) / qt.version / qt.directory


def download_dir(prefix: Path, name: str) -> Path:
    return prefix / "tools" / name


def uv_dir(prefix: Path) -> Path:
    return prefix / "uv"


def rust_dir(prefix: Path) -> Path:
    return prefix / "rust"


def sdk_path(prefix: Path, profiles: list[Profile]) -> list[Path]:
    """The directories QGSDK puts first on PATH, profile by profile: Qt's bin, the compiler, CMake and
    Ninja, then the downloaded tools (NSIS, uv, git)."""
    out: list[Path] = []
    for p in profiles:
        if p.qt:
            out.append(qt_dir(prefix, p.qt) / "bin")
        out += [qt_root(prefix) / tool.bin for tool in p.tools]
        out += [download_dir(prefix, d.name) / d.bin for d in p.downloads if d.name != "rustup-init"]
        if p.rust:
            out.append(rust_dir(prefix) / "cargo" / "bin")
    return list(dict.fromkeys(out))  # once each, in order


def sdk_variables(prefix: Path, profiles: list[Profile]) -> dict[str, str]:
    """The variables besides PATH: Qt for CMake (logger); uv's Pythons and cache inside the prefix (mcp);
    rustup, cargo and Go kept to the prefix and their pinned versions, and libclang for bindgen (desktop)."""
    env = {"QGSDK_PREFIX": str(prefix)}
    for p in profiles:
        if p.qt:
            env["CMAKE_PREFIX_PATH"] = str(qt_dir(prefix, p.qt))
        if p.python_versions:
            env["UV_PYTHON_INSTALL_DIR"] = str(uv_dir(prefix) / "python")
            env["UV_CACHE_DIR"] = str(uv_dir(prefix) / "cache")
        if p.rust:
            env["RUSTUP_HOME"] = str(rust_dir(prefix) / "rustup")
            env["CARGO_HOME"] = str(rust_dir(prefix) / "cargo")
        for d in p.downloads:
            if d.name == "Go":
                env["GOTOOLCHAIN"] = "local"  # the pinned Go, never one it would download for itself
            for name, rel in d.env:
                env[name] = str(download_dir(prefix, d.name) / rel)
    return env


def build_environment(prefix: Path, profiles: list[Profile], base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for working with these profiles: their tools first on PATH, and their variables.
    Nothing else: a build itself is the application's own (plain CMake for the logger)."""
    env = dict(os.environ if base is None else base)
    first = sdk_path(prefix, profiles)
    env["PATH"] = os.pathsep.join([str(p) for p in first] + ([env["PATH"]] if env.get("PATH") else []))
    env.update(sdk_variables(prefix, profiles))
    return env


def read_profiles(prefix: Path) -> list[str]:
    """The profiles installed in this prefix, in the order they were chosen."""
    try:
        names = json.loads((prefix / PROFILES).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [n for n in names if isinstance(n, str)] if isinstance(names, list) else []


def write_profiles(prefix: Path, names: list[str]) -> None:
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / PROFILES).write_text(json.dumps(names) + "\n", encoding="utf-8")


def default_prefix() -> Path:
    """QGSDK_PREFIX if set; otherwise ./prefix beside this checkout."""
    from .manifest import REPO_ROOT

    return Path(os.environ.get("QGSDK_PREFIX") or REPO_ROOT / "prefix").resolve()
