# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""manifest.json: every version QGSDK installs, pinned in one place (docs/manifest.md)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "manifest.json"


@dataclass(frozen=True)
class Tool:
    name: str      # what people call it: "MinGW"
    tool: str      # aqtinstall's tool name: "tools_mingw1310"
    variant: str   # aqtinstall's variant: "qt.tools.win64_mingw1310"
    version: str   # the version that variant installs, for checking and for people
    bin: str       # its bin directory, relative to the Qt install root


@dataclass(frozen=True)
class Download:
    name: str      # "NSIS"
    version: str   # "3.13"
    url: str       # the publisher's archive (a zip)
    sha256: str    # checked before anything is unpacked
    bin: str       # its bin directory, relative to <prefix>/tools/<name>


@dataclass(frozen=True)
class Platform:
    host: str       # aqtinstall host: "windows"
    target: str     # aqtinstall target: "desktop"
    arch: str       # aqtinstall arch: "win64_mingw"
    directory: str  # the directory Qt installs into under <version>/: "mingw_64"
    tools: tuple[Tool, ...]
    downloads: tuple[Download, ...] = ()


@dataclass(frozen=True)
class Manifest:
    qt_version: str
    qt_floor: str
    aqtinstall: str
    aqtinstall_version: str
    platforms: dict[str, Platform]

    def platform(self, name: str) -> Platform:
        if name not in self.platforms:
            raise SystemExit(f"QGSDK doesn't support {name!r} yet (supported: {', '.join(sorted(self.platforms))})")
        return self.platforms[name]


def load(path: Path = DEFAULT_MANIFEST) -> Manifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    qt = data["qt"]
    platforms = {}
    for name, spec in qt.items():
        if not isinstance(spec, dict):
            continue  # "version", "floor"
        tools = tuple(
            Tool(name=t["name"], tool=t["tool"], variant=t["variant"], version=t["version"], bin=t["bin"])
            for t in data.get("tools", {}).get(name, [])
        )
        downloads = tuple(
            Download(name=d["name"], version=d["version"], url=d["url"], sha256=d["sha256"].lower(), bin=d["bin"])
            for d in data.get("downloads", {}).get(name, [])
        )
        platforms[name] = Platform(spec["host"], spec["target"], spec["arch"], spec["directory"], tools, downloads)
    return Manifest(qt_version=qt["version"], qt_floor=qt["floor"], aqtinstall=data["aqtinstall"]["requirement"],
                    aqtinstall_version=data["aqtinstall"]["version"], platforms=platforms)
