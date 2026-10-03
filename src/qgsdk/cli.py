# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""The `qgsdk` command.

    qgsdk install [--force]     install Qt, the compiler, CMake, Ninja and NSIS into the prefix (what's missing)
    qgsdk env [--shell S]       print the environment a build needs (to load it into your shell)
    qgsdk build [PRESET]        configure and build QGLogger with CMake (presets: release, debug)
    qgsdk doctor                show what's installed where

Every command is optional: with the environment loaded, `cmake --preset release` and
`cmake --build --preset release` build QGLogger without QGSDK (docs/decisions/0003).
"""

from __future__ import annotations

import argparse
import platform as host
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, manifest as manifest_mod
from .layout import build_environment, default_prefix, download_dir, qt_dir, qt_root, sdk_path
from .provision import install


def current_platform() -> str:
    system = host.system()
    return {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(system, system.lower())


def shell_lines(env: dict[str, str], names: list[str], shell: str, path_first: list[str] | None = None) -> list[str]:
    """Lines that set `names` in a shell. PATH, if given as `path_first`, is prepended to whatever PATH
    the shell has when the lines run, so loading them later never drops the user's own PATH."""
    lines = []
    if path_first is not None:
        if shell == "powershell":
            lines.append(f'$env:PATH = "{";".join(path_first)};" + $env:PATH')
        elif shell == "cmd":
            lines.append(f'set "PATH={";".join(path_first)};%PATH%"')
        else:
            lines.append(f"export PATH='{':'.join(path_first)}':\"$PATH\"")
    if shell == "powershell":
        return lines + [f'$env:{n} = "{env[n]}"' for n in names]
    if shell == "cmd":
        return lines + [f'set "{n}={env[n]}"' for n in names]
    return lines + [f"export {n}='{env[n]}'" for n in names]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qgsdk", description="The QGLogger build SDK.")
    parser.add_argument("--version", action="version", version=f"QGSDK {__version__}")
    parser.add_argument("--prefix", type=Path, default=None, help="where QGSDK installs things (default: QGSDK_PREFIX, or ./prefix)")
    parser.add_argument("--manifest", type=Path, default=manifest_mod.DEFAULT_MANIFEST, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    install_p = sub.add_parser("install", help="install Qt and the build and packaging tools (only what's missing or changed)")
    install_p.add_argument("--force", action="store_true", help="reinstall everything")
    env_p = sub.add_parser("env", help="print the build environment for your shell")
    env_p.add_argument("--shell", choices=["powershell", "cmd", "sh"], default="powershell" if current_platform() == "windows" else "sh")
    build_p = sub.add_parser("build", help="configure and build QGLogger with CMake")
    build_p.add_argument("preset", nargs="?", default="release", choices=["release", "debug"])
    build_p.add_argument("--source", type=Path, default=Path.cwd(), help="the QGLogger checkout (default: the current directory)")
    sub.add_parser("doctor", help="show what's installed where")
    args = parser.parse_args(argv)

    prefix = (args.prefix or default_prefix()).resolve()
    manifest = manifest_mod.load(args.manifest)
    plat = manifest.platform(current_platform())

    if args.command == "install":
        install(prefix, manifest, plat, force=args.force)
        print(f"QGSDK: Qt {manifest.qt_version} and the tools are in {prefix}")
        return 0
    env = build_environment(prefix, manifest, plat)
    if args.command == "env":
        first = [str(p) for p in sdk_path(prefix, manifest, plat)]
        print("\n".join(shell_lines(env, ["CMAKE_PREFIX_PATH", "QGSDK_PREFIX"], args.shell, path_first=first)))
        return 0
    if args.command == "doctor":
        print(f"QGSDK {__version__}  prefix {prefix}")
        print(f"Qt {manifest.qt_version} ({plat.arch}): {qt_dir(prefix, manifest, plat)}  {'ok' if qt_dir(prefix, manifest, plat).is_dir() else 'MISSING: run qgsdk install'}")
        for tool in plat.tools:
            where = qt_root(prefix) / tool.bin
            print(f"{tool.name} {tool.version}: {where}  {'ok' if where.is_dir() else 'MISSING: run qgsdk install'}")
        for d in plat.downloads:
            where = download_dir(prefix, d.name) / d.bin
            print(f"{d.name} {d.version}: {where}  {'ok' if where.is_dir() else 'MISSING: run qgsdk install'}")
        return 0
    if args.command == "build":
        source = args.source.resolve()
        if not (source / "CMakePresets.json").is_file():
            raise SystemExit(f"{source} has no CMakePresets.json: point --source at an QGLogger checkout")
        # Find CMake on the build environment's PATH: on Windows a child process is looked up on the
        # parent's PATH, which could find some other CMake.
        cmake = shutil.which("cmake", path=env["PATH"])
        if cmake is None:
            raise SystemExit("CMake isn't installed in the prefix: run qgsdk install")
        for step in ([cmake, "--preset", args.preset], [cmake, "--build", "--preset", args.preset]):
            print("+", " ".join(["cmake"] + step[1:]), flush=True)
            subprocess.run(step, cwd=source, env=env, check=True)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
