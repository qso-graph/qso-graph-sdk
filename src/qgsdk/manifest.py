# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""manifest.json: every version QGSDK installs, pinned in one place and grouped by profile (docs/manifest.md).

A profile is what one kind of work needs: `logger` (QSO Graph Logger: Qt and its tools), `mcp` (the MCP
servers: uv and git). A developer installs the profiles they work on, and only those.
"""

from __future__ import annotations

import json
import platform as host
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "manifest.json"


def current_platform() -> str:
    system = host.system()
    return {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(system, system.lower())


def current_machine() -> str:
    """uname -m, normalised: "arm64" (Apple silicon, aarch64) or "x86_64" (AMD64)."""
    machine = host.machine().lower()
    return {"aarch64": "arm64", "amd64": "x86_64", "x64": "x86_64"}.get(machine, machine)


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
    url: str       # the publisher's archive (a zip, or a .tar.gz)
    sha256: str    # checked before anything is unpacked
    bin: str       # its bin directory, relative to <prefix>/tools/<name>


@dataclass(frozen=True)
class Qt:
    version: str
    floor: str      # the oldest Qt the application supports
    host: str       # aqtinstall host: "windows"
    target: str     # aqtinstall target: "desktop"
    arch: str       # aqtinstall arch: "win64_mingw"
    directory: str  # the directory Qt installs into under <version>/: "mingw_64"


@dataclass(frozen=True)
class Profile:
    """One profile, on one platform: what it installs there."""

    name: str
    description: str
    qt: Qt | None = None
    tools: tuple[Tool, ...] = ()
    downloads: tuple[Download, ...] = ()
    python_versions: tuple[str, ...] = ()  # installed with uv (the mcp profile)


@dataclass(frozen=True)
class Manifest:
    aqtinstall: str
    aqtinstall_version: str
    profiles: dict[str, dict]  # name -> its manifest.json entry; resolved per platform by profile()

    def names(self) -> list[str]:
        return sorted(self.profiles)

    def profile(self, name: str, platform: str | None = None, machine: str | None = None) -> Profile:
        """`name` as it applies on `platform` and `machine` (default: this computer)."""
        if name not in self.profiles:
            raise SystemExit(f"QGSDK has no profile {name!r} (profiles: {', '.join(self.names())})")
        platform = platform or current_platform()
        machine = machine or current_machine()
        spec = self.profiles[name]
        qt = None
        if "qt" in spec:
            q = spec["qt"]
            if platform not in q:
                raise SystemExit(f"The {name} profile doesn't support {platform!r} yet")
            p = q[platform]
            qt = Qt(q["version"], q["floor"], p["host"], p["target"], p["arch"], p["directory"])
        tools = tuple(
            Tool(name=t["name"], tool=t["tool"], variant=t["variant"], version=t["version"], bin=t["bin"])
            for t in spec.get("tools", {}).get(platform, [])
        )
        downloads = tuple(
            Download(name=d["name"], version=d["version"], url=d["url"], sha256=d["sha256"].lower(), bin=d["bin"])
            for d in spec.get("downloads", {}).get(platform, [])
            if d.get("machine", machine) == machine
        )
        if not (qt or tools or downloads):
            raise SystemExit(f"The {name} profile doesn't support {platform!r} on {machine!r} yet")
        return Profile(name, spec["description"], qt, tools, downloads, tuple(spec.get("python_versions", ())))


def load(path: Path = DEFAULT_MANIFEST) -> Manifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Manifest(aqtinstall=data["aqtinstall"]["requirement"], aqtinstall_version=data["aqtinstall"]["version"],
                    profiles=data["profiles"])
