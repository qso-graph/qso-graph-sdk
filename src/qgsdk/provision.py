# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""Install Qt and its tools with aqtinstall, and the other tools manifest.json lists under "downloads",
at the versions it pins.

aqtinstall downloads from Qt's own repositories (no Qt account), checks every archive against Qt's
published hashes, and unpacks into the prefix. A download (NSIS) comes from its publisher and is checked
against the SHA-256 in the manifest before it is unpacked. Unattended; no admin rights.

Running it again installs only what is missing or has changed in the manifest: what was installed is
recorded, component by component, in <prefix>/Qt/qgsdk-installed.json. A folder alone isn't proof (CMake
installs into the same folder whatever its version), so a component is skipped only when its record
matches the manifest and its files are there. `force` reinstalls everything.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .layout import download_dir, qt_dir, qt_root
from .manifest import Download, Manifest, Platform

RECORD = "qgsdk-installed.json"


@dataclass(frozen=True)
class Component:
    key: str        # "qt", or the tool name: "tools_cmake"
    identity: str   # what the manifest pins for it: "6.12.0 win64_mingw", "qt.tools.cmake 3.30.5"
    path: Path      # the folder that must exist once it's installed
    command: list[str]              # the aqtinstall command that installs it (empty for a download)
    download: Download | None = None


def components(prefix: Path, manifest: Manifest, platform: Platform) -> list[Component]:
    """Qt, then each tool, with the aqtinstall command that installs it."""
    out = str(qt_root(prefix))
    aqt = [sys.executable, "-m", "aqt"]
    items = [Component(
        "qt", f"{manifest.qt_version} {platform.arch}", qt_dir(prefix, manifest, platform),
        aqt + ["install-qt", platform.host, platform.target, manifest.qt_version, platform.arch, "--outputdir", out],
    )]
    for tool in platform.tools:
        items.append(Component(
            tool.tool, f"{tool.variant} {tool.version}", qt_root(prefix) / tool.bin,
            aqt + ["install-tool", platform.host, platform.target, tool.tool, tool.variant, "--outputdir", out],
        ))
    for d in platform.downloads:
        items.append(Component(f"download:{d.name}", f"{d.name} {d.version}", download_dir(prefix, d.name) / d.bin, [], d))
    return items


def aqt_commands(prefix: Path, manifest: Manifest, platform: Platform) -> list[list[str]]:
    """The aqtinstall commands, in order: Qt, then each tool."""
    return [c.command for c in components(prefix, manifest, platform) if c.command]


def tls_context() -> ssl.SSLContext:
    """Certificate checking with certifi's CA bundle (installed with aqtinstall's dependencies). A fresh
    Windows holds only part of its root certificates and fetches the rest on demand, which Python's own
    TLS never triggers, so the system store alone can fail on a clean machine."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def fetch(prefix: Path, d: Download) -> None:
    """Download `d`, check its SHA-256, and unpack it into <prefix>/tools/<name> (replacing what's there)."""
    downloads = prefix / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / d.url.rsplit("/", 1)[-1]
    print(f"+ download {d.name} {d.version}: {d.url}", flush=True)
    with urllib.request.urlopen(d.url, timeout=300, context=tls_context()) as response, archive.open("wb") as f:
        shutil.copyfileobj(response, f)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != d.sha256:
        archive.unlink()
        raise SystemExit(f"{d.name}: SHA-256 mismatch for {d.url}\n  expected {d.sha256}\n  got      {digest}")
    target = download_dir(prefix, d.name)
    if target.exists():
        shutil.rmtree(target)
    with zipfile.ZipFile(archive) as z:
        z.extractall(target)


def read_record(prefix: Path) -> dict[str, str]:
    try:
        return json.loads((qt_root(prefix) / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def needed(prefix: Path, manifest: Manifest, platform: Platform, force: bool = False) -> list[Component]:
    """The components to install: all of them with `force`, otherwise those missing or changed."""
    record = read_record(prefix)
    return [c for c in components(prefix, manifest, platform)
            if force or record.get(c.key) != c.identity or not c.path.is_dir()]


def install(prefix: Path, manifest: Manifest, platform: Platform, force: bool = False) -> None:
    prefix.mkdir(parents=True, exist_ok=True)
    todo = needed(prefix, manifest, platform, force)
    record = read_record(prefix)
    for component in components(prefix, manifest, platform):
        if component not in todo:
            print(f"= {component.identity}: already installed", flush=True)
            continue
        if component.download:
            fetch(prefix, component.download)
        else:
            print("+", " ".join(component.command[1:]), flush=True)
            subprocess.run(component.command, check=True)
        if not component.path.is_dir():
            raise SystemExit(f"{component.identity} installed, but {component.path} is missing")
        record[component.key] = component.identity
        qt_root(prefix).mkdir(parents=True, exist_ok=True)
        (qt_root(prefix) / RECORD).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
