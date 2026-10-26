# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""The `qgsdk` command.

    qgsdk profiles                  list the profiles, and which are installed here
    qgsdk select [--profile P ...]  choose profiles (added to those already chosen; asks if none are)
    qgsdk install [--profile P ...] [--force]
                                    install what the chosen profiles need (only what's missing or changed)
    qgsdk env [--shell S]           print the environment they need (to load it into your shell)
    qgsdk build [PRESET]            configure and build the logger with CMake (presets: release, debug)
    qgsdk doctor                    show what's installed where

Every command is optional once the environment is loaded: with the logger profile, `cmake --preset
release` and `cmake --build --preset release` build without QGSDK (docs/decisions/0003).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import manifest as manifest_mod
from .layout import (
    build_environment,
    default_prefix,
    download_dir,
    qt_dir,
    qt_root,
    read_profiles,
    rust_dir,
    sdk_path,
    sdk_variables,
    uv_dir,
    write_profiles,
)
from .manifest import current_platform
from .provision import install


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


def ask(manifest: manifest_mod.Manifest) -> list[str]:
    """Ask which profiles to install, at a terminal. Answers by number or name; several at once."""
    names = manifest.names()
    say = sys.stderr  # the question goes to stderr: `qgsdk select`'s stdout is the answer, which scripts read
    print("What are you working on? Choose one or more (for example: 1 2), or 'all'.", file=say)
    for i, name in enumerate(names, 1):
        print(f"  {i}) {name:8} {manifest.profiles[name]['description']}", file=say)
    while True:
        print("> ", end="", file=say, flush=True)
        answer = input().replace(",", " ").split()
        if answer == ["all"]:
            return names
        chosen = [names[int(a) - 1] if a.isdigit() and 0 < int(a) <= len(names) else a for a in answer]
        if chosen and all(c in names for c in chosen):
            return list(dict.fromkeys(chosen))
        print(f"Choose from 1-{len(names)} or {', '.join(names)}.", file=say)


def select(prefix: Path, manifest: manifest_mod.Manifest, wanted: list[str]) -> list[str]:
    """The profiles for this prefix: those already chosen plus `wanted`. With neither, ask at a terminal;
    elsewhere (CI, a script), say how to choose."""
    for name in wanted:
        manifest.profile(name)  # an unknown profile, or one this platform lacks, stops here
    chosen = list(dict.fromkeys(read_profiles(prefix) + wanted))
    if not chosen:
        if not sys.stdin.isatty():
            raise SystemExit(f"Choose a profile with --profile ({', '.join(manifest.names())})")
        chosen = ask(manifest)
        for name in chosen:
            manifest.profile(name)
    write_profiles(prefix, chosen)
    return chosen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qgsdk", description="The QSO Graph SDK: the tools to build QSO Graph's software.")
    parser.add_argument("--version", action="version", version=f"QGSDK {__version__}")
    parser.add_argument("--prefix", type=Path, default=None, help="where QGSDK installs things (default: QGSDK_PREFIX, or ./prefix)")
    parser.add_argument("--manifest", type=Path, default=manifest_mod.DEFAULT_MANIFEST, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles", help="list the profiles, and which are installed here")
    select_p = sub.add_parser("select", help="choose profiles (added to those already chosen); prints them")
    select_p.add_argument("--profile", action="append", default=[], metavar="P", help="a profile; repeat for more")
    install_p = sub.add_parser("install", help="install what the chosen profiles need (only what's missing or changed)")
    install_p.add_argument("--profile", action="append", default=[], metavar="P", help="add a profile; repeat for more")
    install_p.add_argument("--force", action="store_true", help="reinstall everything")
    env_p = sub.add_parser("env", help="print the environment for your shell")
    env_p.add_argument("--shell", choices=["powershell", "cmd", "sh"], default="powershell" if current_platform() == "windows" else "sh")
    build_p = sub.add_parser("build", help="configure and build the logger with CMake")
    build_p.add_argument("preset", nargs="?", default="release", choices=["release", "debug"])
    build_p.add_argument("--source", type=Path, default=Path.cwd(), help="the logger checkout (default: the current directory)")
    sub.add_parser("doctor", help="show what's installed where")
    args = parser.parse_args(argv)

    prefix = (args.prefix or default_prefix()).resolve()
    manifest = manifest_mod.load(args.manifest)

    if args.command == "profiles":
        installed = read_profiles(prefix)
        for name in manifest.names():
            print(f"{'*' if name in installed else ' '} {name:8} {manifest.profiles[name]['description']}")
        return 0
    if args.command in ("select", "install"):
        names = select(prefix, manifest, args.profile)
        if args.command == "select":
            print(" ".join(names))
            return 0
        profiles = [manifest.profile(n) for n in names]
        install(prefix, profiles, force=args.force)
        print(f"QGSDK: {', '.join(names)} installed in {prefix}")
        return 0

    names = read_profiles(prefix)
    if not names:
        raise SystemExit(f"No profile is installed in {prefix}: run qgsdk install --profile ({', '.join(manifest.names())})")
    profiles = [manifest.profile(n) for n in names]
    if args.command == "env":
        first = [str(p) for p in sdk_path(prefix, profiles)]
        variables = sdk_variables(prefix, profiles)
        print("\n".join(shell_lines(variables, sorted(variables), args.shell, path_first=first)))
        return 0
    if args.command == "doctor":
        def state(where: Path) -> str:
            return "ok" if where.is_dir() else "MISSING: run qgsdk install"

        print(f"QGSDK {__version__}  prefix {prefix}  profiles {', '.join(names)}")
        for p in profiles:
            print(f"[{p.name}]")
            if p.qt:
                print(f"  Qt {p.qt.version} ({p.qt.arch}): {qt_dir(prefix, p.qt)}  {state(qt_dir(prefix, p.qt))}")
            for tool in p.tools:
                print(f"  {tool.name} {tool.version}: {qt_root(prefix) / tool.bin}  {state(qt_root(prefix) / tool.bin)}")
            for d in p.downloads:
                if d.name == "rustup-init":
                    continue  # the installer; Rust itself is below
                where = download_dir(prefix, d.name) / d.bin
                print(f"  {d.name} {d.version}: {where}  {state(where)}")
            if p.rust:
                cargo = rust_dir(prefix) / "cargo" / "bin"
                print(f"  Rust {p.rust} (rustup): {cargo}  {state(cargo)}")
            if p.python_versions:
                print(f"  Python {' '.join(p.python_versions)} (uv): {uv_dir(prefix) / 'python'}  {state(uv_dir(prefix) / 'python')}")
        return 0
    if args.command == "build":
        if "logger" not in names:
            raise SystemExit("qgsdk build builds the logger: run qgsdk install --profile logger first")
        env = build_environment(prefix, profiles)
        source = args.source.resolve()
        if not (source / "CMakePresets.json").is_file():
            raise SystemExit(f"{source} has no CMakePresets.json: point --source at a logger checkout")
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
