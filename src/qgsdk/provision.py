# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""Install what the chosen profiles need, at the versions manifest.json pins: Qt and its tools with
aqtinstall, the other tools listed under "downloads", the Pythons uv installs, and the Rust toolchain
rustup installs.

aqtinstall downloads from Qt's own repositories (no Qt account), checks every archive against Qt's
published hashes, and unpacks into the prefix. A download (NSIS, uv, MinGit) comes from its publisher and
is checked against the SHA-256 in the manifest before it is unpacked. Unattended; no admin rights.

Running it again installs only what is missing or has changed in the manifest: what was installed is
recorded, component by component, in <prefix>/qgsdk-installed.json. A folder alone isn't proof (CMake
installs into the same folder whatever its version), so a component is skipped only when its record
matches the manifest and its files are there. `force` reinstalls everything.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .layout import build_environment, download_dir, qt_dir, qt_root, rust_dir, uv_dir
from .manifest import Download, Profile

RECORD = "qgsdk-installed.json"


@dataclass(frozen=True)
class Component:
    key: str        # "qt", the tool name ("tools_cmake"), "download:<name>", "uv-python" or "rust"
    identity: str   # what the manifest pins for it: "6.12.0 win64_mingw", "qt.tools.cmake 3.30.5"
    path: Path      # the folder that must exist once it's installed
    command: list[str]              # the command that installs it (empty for a download)
    download: Download | None = None


def components(prefix: Path, profiles: list[Profile]) -> list[Component]:
    """Everything the profiles install, in order and once each: Qt, then each Qt tool, then the downloads,
    then the Pythons uv installs and the Rust toolchain rustup installs (uv and rustup must be there first)."""
    out = str(qt_root(prefix))
    aqt = [sys.executable, "-m", "aqt"]
    items: dict[str, Component] = {}
    for p in profiles:
        if p.qt:
            q = p.qt
            items.setdefault("qt", Component(
                "qt", f"{q.version} {q.arch}", qt_dir(prefix, q),
                aqt + ["install-qt", q.host, q.target, q.version, q.arch, "--outputdir", out],
            ))
            for tool in p.tools:
                items.setdefault(tool.tool, Component(
                    tool.tool, f"{tool.variant} {tool.version}", qt_root(prefix) / tool.bin,
                    aqt + ["install-tool", q.host, q.target, tool.tool, tool.variant, "--outputdir", out],
                ))
        for d in p.downloads:
            key = f"download:{d.name}"
            items.setdefault(key, Component(key, f"{d.name} {d.version}", download_dir(prefix, d.name) / d.bin, [], d))
    for p in profiles:
        if p.python_versions:
            uv = next(d for d in p.downloads if d.name == "uv")
            exe = download_dir(prefix, uv.name) / uv.bin / ("uv.exe" if sys.platform == "win32" else "uv")
            items.setdefault("uv-python", Component(
                "uv-python", f"uv {uv.version}: Python {' '.join(p.python_versions)}", uv_dir(prefix) / "python",
                [str(exe), "python", "install", *p.python_versions],
            ))
        if p.rust:
            init = next(d for d in p.downloads if d.name == "rustup-init")
            exe = download_dir(prefix, init.name) / init.bin / init.url.rsplit("/", 1)[-1]
            items.setdefault("rust", Component(
                "rust", f"Rust {p.rust} (rustup {init.version})", rust_dir(prefix) / "cargo" / "bin",
                [str(exe), "-y", "--no-modify-path", "--profile", "minimal", "--default-toolchain", p.rust],
            ))
    return list(items.values())


def aqt_commands(prefix: Path, profiles: list[Profile]) -> list[list[str]]:
    """The aqtinstall commands, in order: Qt, then each tool."""
    return [c.command for c in components(prefix, profiles) if c.command[1:3] == ["-m", "aqt"]]


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

    def wanted(name: str) -> bool:
        return not d.members or any(fnmatch.fnmatch(name, pattern) for pattern in d.members)

    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(target, members=[n for n in z.namelist() if wanted(n)])
    elif archive.name.endswith((".tar.gz", ".tgz", ".tar.xz")):
        with tarfile.open(archive, "r:*") as t:
            # Streamed, member by member, so a large archive is never held whole; the "data" filter
            # keeps everything inside the target, with no device files or links out of it.
            for member in t:
                if wanted(member.name):
                    t.extract(member, target, filter="data")
    else:  # a single program (rustup-init), kept as it is
        target.mkdir(parents=True)
        shutil.copy2(archive, target / archive.name)
        os.chmod(target / archive.name, 0o755)


def read_record(prefix: Path) -> dict[str, str]:
    try:
        return json.loads((prefix / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def needed(prefix: Path, profiles: list[Profile], force: bool = False) -> list[Component]:
    """The components to install: all of them with `force`, otherwise those missing or changed."""
    record = read_record(prefix)
    return [c for c in components(prefix, profiles)
            if force or record.get(c.key) != c.identity or not c.path.is_dir()]


def install(prefix: Path, profiles: list[Profile], force: bool = False) -> None:
    prefix.mkdir(parents=True, exist_ok=True)
    todo = needed(prefix, profiles, force)
    record = read_record(prefix)
    env = build_environment(prefix, profiles)  # uv installs its Pythons into the prefix
    for component in components(prefix, profiles):
        if component not in todo:
            print(f"= {component.identity}: already installed", flush=True)
            continue
        if component.download:
            fetch(prefix, component.download)
        elif component.key == "rust":
            # rustup-init's output is a page of its own advice (add cargo to PATH, which QGSDK's
            # environment does) and compiler-detection debug lines: kept in a log, shown on failure.
            log = rust_dir(prefix) / "rustup-init.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            print(f"+ {component.identity}: rustup-init (its output: {log})", flush=True)
            with log.open("w", encoding="utf-8") as out:
                done = subprocess.run(component.command, check=False, env=env, stdout=out, stderr=subprocess.STDOUT)
            if done.returncode != 0:
                print("".join(log.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[-30:]), flush=True)
                raise SystemExit(f"{component.identity}: rustup-init failed (exit {done.returncode}); its output is in {log}")
        else:
            print("+", " ".join(component.command[1:]), flush=True)
            subprocess.run(component.command, check=True, env=env)
        if not component.path.is_dir():
            raise SystemExit(f"{component.identity} installed, but {component.path} is missing")
        record[component.key] = component.identity
        (prefix / RECORD).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
