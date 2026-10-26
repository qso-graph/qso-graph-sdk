# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""The manifest and what QGSDK derives from it. These run anywhere (no Qt needed)."""

import json
import os
import re
from pathlib import Path

import pytest

from qgsdk import manifest as m
from qgsdk.layout import build_environment, qt_dir
from qgsdk.provision import aqt_commands

PLATFORMS = [("windows", "x86_64"), ("linux", "x86_64"), ("linux", "arm64"), ("macos", "arm64"), ("macos", "x86_64")]


def logger(platform="windows", machine="x86_64"):
    return m.load().profile("logger", platform, machine)


def mcp(platform="windows", machine="x86_64"):
    return m.load().profile("mcp", platform, machine)


def desktop(platform="windows", machine="x86_64"):
    return m.load().profile("desktop", platform, machine)


def supported(name, platform, machine):
    return not (name == "logger" and (platform, machine) == ("linux", "arm64"))  # no Qt for it yet


def test_the_profiles():
    assert m.load().names() == ["desktop", "logger", "mcp"]


def test_the_manifest_pins_everything_exactly():
    data = json.loads(m.DEFAULT_MANIFEST.read_text())
    assert re.search(r"/archive/[0-9a-f]{40}\.zip$", data["aqtinstall"]["requirement"])  # a commit, not a branch
    for platform, machine in PLATFORMS:
        for name in m.load().names():
            if not supported(name, platform, machine):
                continue
            p = m.load().profile(name, platform, machine)
            if p.qt:
                assert re.fullmatch(r"\d+\.\d+\.\d+", p.qt.version)
            assert all(re.fullmatch(r"\d+\.\d+\.\d+", t.version) for t in p.tools)
            for d in p.downloads:  # every download: https, and a SHA-256 to check
                assert d.url.startswith("https://") and re.fullmatch(r"[0-9a-f]{64}", d.sha256)


def test_python_is_pinned_for_every_platform():
    data = json.loads(m.DEFAULT_MANIFEST.read_text())
    for key in ("windows", "linux-x86_64", "linux-arm64", "macos-arm64", "macos-x86_64"):
        assert data["python"][key]["url"].startswith("https://")
        assert re.fullmatch(r"[0-9a-f]{64}", data["python"][key]["sha256"])


def test_qt_is_at_or_above_the_floor():
    q = logger().qt
    version = tuple(int(x) for x in q.version.split("."))
    floor = tuple(int(x) for x in q.floor.split("."))
    assert version[: len(floor)] >= floor


def test_logger_on_windows_uses_mingw_and_its_tools():
    windows = logger("windows")
    assert windows.qt.arch == "win64_mingw"
    assert [t.name for t in windows.tools] == ["MinGW", "CMake", "Ninja"]
    assert [d.name for d in windows.downloads] == ["NSIS"]  # the installer


def test_logger_on_linux_uses_the_system_compiler_and_qts_tools():
    linux = logger("linux")
    assert linux.qt.arch == "linux_gcc_64" and linux.qt.directory == "gcc_64"
    assert [t.name for t in linux.tools] == ["CMake", "Ninja"]  # GCC comes from the system
    assert linux.downloads == ()


def test_logger_on_macos_is_one_universal_qt_for_both_machines():
    assert logger("macos", "arm64") == logger("macos", "x86_64")
    mac = logger("macos", "arm64")
    assert mac.qt.host == "mac" and mac.qt.arch == "clang_64" and mac.qt.directory == "macos"
    assert [t.name for t in mac.tools] == ["CMake", "Ninja"]  # clang comes from the Xcode command-line tools


def test_mcp_is_uv_and_its_pythons_with_git_on_windows():
    assert [d.name for d in mcp("windows").downloads] == ["uv", "MinGit"]
    assert [d.name for d in mcp("linux").downloads] == ["uv"]  # git from the system
    assert mcp("windows").python_versions == ("3.11", "3.12", "3.13")
    assert mcp("windows").qt is None


def test_a_download_for_one_machine_is_only_used_on_it():
    arm, intel = mcp("macos", "arm64").downloads, mcp("macos", "x86_64").downloads
    assert [d.bin for d in arm] == ["uv-aarch64-apple-darwin"]
    assert [d.bin for d in intel] == ["uv-x86_64-apple-darwin"]
    assert [d.bin for d in mcp("linux", "arm64").downloads] == ["uv-aarch64-unknown-linux-gnu"]
    with pytest.raises(SystemExit, match="doesn't support 'linux' on 'arm64'"):
        logger("linux", "arm64")  # Qt's Linux build here is x86-64 only


def test_unknown_profiles_and_platforms_say_so():
    with pytest.raises(SystemExit, match="no profile 'desktop2'"):
        m.load().profile("desktop2")
    with pytest.raises(SystemExit, match="doesn't support 'amiga'"):
        logger("amiga")


def test_aqtinstall_commands():
    p = logger("windows")
    commands = aqt_commands(Path("/sdk"), [p, mcp("windows")])  # mcp adds no aqtinstall command
    assert commands[0][2:7] == ["aqt", "install-qt", "windows", "desktop", p.qt.version]
    assert commands[0][-1] == str(Path("/sdk/Qt"))
    assert [c[6] for c in commands[1:]] == ["tools_mingw1310", "tools_cmake", "tools_ninja"]


def test_the_environment_puts_qt_and_the_tools_first():
    p = logger("windows")
    env = build_environment(Path("/sdk"), [p], base={"PATH": "/usr/bin"})
    parts = env["PATH"].split(os.pathsep)
    assert parts[0] == str(qt_dir(Path("/sdk"), p.qt) / "bin")
    assert parts[-1] == "/usr/bin"
    assert parts[-2] == str(Path("/sdk/tools/NSIS/nsis-3.13"))  # makensis, for CPack
    assert env["CMAKE_PREFIX_PATH"] == str(Path(f"/sdk/Qt/{p.qt.version}/mingw_64"))
    assert "UV_PYTHON_INSTALL_DIR" not in env


def test_the_mcp_environment_keeps_uv_inside_the_prefix():
    env = build_environment(Path("/sdk"), [mcp("linux")], base={"PATH": "/usr/bin"})
    assert env["PATH"].split(os.pathsep)[0] == str(Path("/sdk/tools/uv/uv-x86_64-unknown-linux-gnu"))
    assert env["UV_PYTHON_INSTALL_DIR"] == str(Path("/sdk/uv/python"))
    assert env["UV_CACHE_DIR"] == str(Path("/sdk/uv/cache"))
    assert "CMAKE_PREFIX_PATH" not in env


def test_install_skips_what_matches_the_record(tmp_path):
    from qgsdk.provision import RECORD, components, needed

    profiles = [logger("windows")]
    assert len(needed(tmp_path, profiles)) == 5  # nothing installed: Qt, MinGW, CMake, Ninja, NSIS

    for c in components(tmp_path, profiles):  # as if installed
        c.path.mkdir(parents=True)
    record = {c.key: c.identity for c in components(tmp_path, profiles)}
    (tmp_path / RECORD).write_text(json.dumps(record))
    assert needed(tmp_path, profiles) == []
    assert len(needed(tmp_path, profiles, force=True)) == 5

    record["tools_cmake"] = "qt.tools.cmake 3.29.0"  # the manifest moved CMake on
    (tmp_path / RECORD).write_text(json.dumps(record))
    assert [c.key for c in needed(tmp_path, profiles)] == ["tools_cmake"]  # same folder, still reinstalled

    both = profiles + [mcp("windows")]  # adding a profile installs only what it adds
    assert [c.key for c in needed(tmp_path, both)] == ["tools_cmake", "download:uv", "download:MinGit", "uv-python"]


def test_uv_installs_its_pythons_after_uv_itself(tmp_path):
    from qgsdk.provision import components

    keys = [c.key for c in components(tmp_path, [mcp("macos", "arm64")])]
    assert keys == ["download:uv", "uv-python"]
    command = components(tmp_path, [mcp("macos", "arm64")])[-1].command
    assert command == [str(tmp_path / "tools/uv/uv-aarch64-apple-darwin/uv"), "python", "install", "3.11", "3.12", "3.13"]


def _serve(monkeypatch, payload):
    import io

    from qgsdk import provision

    monkeypatch.setattr(provision.urllib.request, "urlopen", lambda url, timeout, context: io.BytesIO(payload))


def test_a_download_is_checked_before_it_is_unpacked(tmp_path, monkeypatch):
    import hashlib
    import io
    import zipfile

    from qgsdk import provision
    from qgsdk.manifest import Download

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("tool-1.0/tool.exe", b"x")
    payload = buf.getvalue()
    _serve(monkeypatch, payload)

    good = Download("Tool", "1.0", "https://example.org/tool-1.0.zip", hashlib.sha256(payload).hexdigest(), "tool-1.0")
    provision.fetch(tmp_path, good)
    assert (tmp_path / "tools" / "Tool" / "tool-1.0" / "tool.exe").is_file()

    bad = Download("Bad", "1.0", "https://example.org/bad-1.0.zip", "0" * 64, "bad-1.0")
    with pytest.raises(SystemExit, match="SHA-256 mismatch"):
        provision.fetch(tmp_path, bad)
    assert not (tmp_path / "tools" / "Bad").exists()  # nothing unpacked


def test_a_tarball_unpacks_and_cannot_escape_its_folder(tmp_path, monkeypatch):
    import hashlib
    import io
    import tarfile

    from qgsdk import provision
    from qgsdk.manifest import Download

    def tarball(name):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as t:
            info = tarfile.TarInfo(name)
            info.size = 1
            t.addfile(info, io.BytesIO(b"x"))
        return buf.getvalue()

    payload = tarball("uv-x/uv")
    _serve(monkeypatch, payload)
    provision.fetch(tmp_path, Download("uv", "1", "https://example.org/uv.tar.gz", hashlib.sha256(payload).hexdigest(), "uv-x"))
    assert (tmp_path / "tools" / "uv" / "uv-x" / "uv").is_file()

    evil = tarball("../../escaped")
    _serve(monkeypatch, evil)
    with pytest.raises(tarfile.OutsideDestinationError):
        provision.fetch(tmp_path, Download("evil", "1", "https://example.org/e.tar.gz", hashlib.sha256(evil).hexdigest(), "."))
    assert not (tmp_path / "escaped").exists()


def test_desktop_on_every_platform_and_machine():
    for platform, machine in PLATFORMS:
        p = desktop(platform, machine)
        names = [d.name for d in p.downloads]
        assert names[:4] == ["Node.js", "rustup-init", "Go", "CMake"]
        assert p.rust and p.qt is None
    assert [d.name for d in desktop("windows").downloads][4:] == ["Ninja", "NASM", "libclang", "MinGit"]
    assert [d.name for d in desktop("linux", "arm64").downloads] == ["Node.js", "rustup-init", "Go", "CMake"]
    assert all("arm64" in d.url or "aarch64" in d.url for d in desktop("linux", "arm64").downloads)


def test_desktop_pins_match_the_desktop_repository_format():
    p = desktop()
    assert re.fullmatch(r"\d+\.\d+\.\d+", p.rust)  # rust-toolchain.toml's channel, exactly
    node = next(d for d in p.downloads if d.name == "Node.js")
    assert f"/v{node.version}/" in node.url  # .node-version's version, exactly


def test_the_desktop_environment_keeps_rust_and_go_to_the_prefix():
    env = build_environment(Path("/sdk"), [desktop("windows")], base={"PATH": "/usr/bin"})
    assert env["RUSTUP_HOME"] == str(Path("/sdk/rust/rustup"))
    assert env["CARGO_HOME"] == str(Path("/sdk/rust/cargo"))
    assert env["GOTOOLCHAIN"] == "local"
    assert env["LIBCLANG_PATH"] == str(Path("/sdk/tools/libclang/clang+llvm-23.1.4-x86_64-pc-windows-msvc/bin"))
    parts = env["PATH"].split(os.pathsep)
    assert str(Path("/sdk/rust/cargo/bin")) in parts
    assert not any("rustup-init" in part for part in parts)  # the installer, not a tool to run


def test_rustup_installs_the_pinned_toolchain_after_rustup_init(tmp_path):
    from qgsdk.provision import components

    items = components(tmp_path, [desktop("linux")])
    assert [c.key for c in items][-1] == "rust"
    assert items[-1].command == [str(tmp_path / "tools/rustup-init/./rustup-init"), "-y", "--no-modify-path",
                                 "--profile", "minimal", "--default-toolchain", desktop().rust]


def test_only_the_listed_members_are_unpacked(tmp_path, monkeypatch):
    import hashlib
    import io
    import tarfile

    from qgsdk import provision
    from qgsdk.manifest import Download

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for name in ("llvm/bin/libclang.dll", "llvm/bin/clang.exe", "llvm/lib/clang/23/include/stddef.h"):
            info = tarfile.TarInfo(name)
            info.size = 1
            t.addfile(info, io.BytesIO(b"x"))
    payload = buf.getvalue()
    _serve(monkeypatch, payload)
    provision.fetch(tmp_path, Download("libclang", "23", "https://example.org/llvm.tar.xz", hashlib.sha256(payload).hexdigest(),
                                       "llvm/bin", members=("*/bin/libclang.dll", "*/lib/clang/*/include/*")))
    root = tmp_path / "tools" / "libclang" / "llvm"
    assert (root / "bin" / "libclang.dll").is_file() and (root / "lib/clang/23/include/stddef.h").is_file()
    assert not (root / "bin" / "clang.exe").exists()


def test_a_single_program_is_kept_and_made_runnable(tmp_path, monkeypatch):
    import hashlib

    from qgsdk import provision
    from qgsdk.manifest import Download

    _serve(monkeypatch, b"#!/bin/sh\n")
    provision.fetch(tmp_path, Download("rustup-init", "1", "https://example.org/x/rustup-init",
                                       hashlib.sha256(b"#!/bin/sh\n").hexdigest(), "."))
    program = tmp_path / "tools" / "rustup-init" / "rustup-init"
    assert program.is_file() and os.access(program, os.X_OK)


def test_rustup_inits_output_goes_to_a_log_and_a_failure_names_it(tmp_path, monkeypatch, capsys):
    import sys

    from qgsdk import provision
    from qgsdk.provision import Component

    def rust(code):
        script = f"print('cargo:rerun-if-env-changed=CC'); raise SystemExit({code})"
        return Component("rust", "Rust 1.99.1 (rustup 1.29.2)", tmp_path / "rust" / "cargo" / "bin", [sys.executable, "-c", script])

    log = tmp_path / "rust" / "rustup-init.log"

    def made(code):
        def components(prefix, profiles):
            return [rust(code)]
        return components

    monkeypatch.setattr(provision, "components", made(3))
    with pytest.raises(SystemExit, match="rustup-init failed \\(exit 3\\)"):
        provision.install(tmp_path, [desktop("linux")])
    assert "cargo:rerun-if-env-changed" in log.read_text()

    capsys.readouterr()
    monkeypatch.setattr(provision, "components", made(0))
    (tmp_path / "rust" / "cargo" / "bin").mkdir(parents=True)
    provision.install(tmp_path, [desktop("linux")])
    out = capsys.readouterr().out
    assert "rerun-if-env-changed" not in out  # the noise stays in the log
    assert "rustup-init (its output:" in out
