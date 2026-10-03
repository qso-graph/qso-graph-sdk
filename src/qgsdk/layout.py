# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""Where QGSDK puts things under its prefix, and the environment a build needs.

Everything lives under one directory (the prefix), so removing QGSDK is deleting a folder: nothing is
written into the system, and no admin rights are needed.

    <prefix>/python/                    QGSDK's own Python (Windows; from the bootstrap)
    <prefix>/Qt/<qt version>/<dir>/     Qt, as aqtinstall lays it out
    <prefix>/Qt/Tools/...               the compiler, CMake and Ninja
    <prefix>/tools/<name>/              tools from elsewhere (NSIS), as manifest.json's "downloads"
"""

from __future__ import annotations

import os
from pathlib import Path

from .manifest import Manifest, Platform


def qt_root(prefix: Path) -> Path:
    return prefix / "Qt"


def qt_dir(prefix: Path, manifest: Manifest, platform: Platform) -> Path:
    """The Qt installation CMake finds Qt6 in (CMAKE_PREFIX_PATH)."""
    return qt_root(prefix) / manifest.qt_version / platform.directory


def download_dir(prefix: Path, name: str) -> Path:
    return prefix / "tools" / name


def sdk_path(prefix: Path, manifest: Manifest, platform: Platform) -> list[Path]:
    """The directories QGSDK puts first on PATH: Qt's bin, the compiler, CMake and Ninja, then the
    downloaded tools (NSIS)."""
    return ([qt_dir(prefix, manifest, platform) / "bin"] + [qt_root(prefix) / tool.bin for tool in platform.tools]
            + [download_dir(prefix, d.name) / d.bin for d in platform.downloads])


def build_environment(prefix: Path, manifest: Manifest, platform: Platform, base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for configuring, building and running QGLogger: the tools and Qt first on PATH, and
    Qt on CMAKE_PREFIX_PATH. Nothing else: the build itself is plain CMake."""
    env = dict(os.environ if base is None else base)
    qt = qt_dir(prefix, manifest, platform)
    first = sdk_path(prefix, manifest, platform)
    env["PATH"] = os.pathsep.join([str(p) for p in first] + ([env["PATH"]] if env.get("PATH") else []))
    env["CMAKE_PREFIX_PATH"] = str(qt)
    env["QGSDK_PREFIX"] = str(prefix)
    return env


def default_prefix() -> Path:
    """QGSDK_PREFIX if set; otherwise ./prefix beside this checkout."""
    from .manifest import REPO_ROOT

    return Path(os.environ.get("QGSDK_PREFIX") or REPO_ROOT / "prefix").resolve()
