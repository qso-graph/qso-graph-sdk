# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""The manifest and what QGSDK derives from it. These run anywhere (no Qt needed)."""

import json
import re
from pathlib import Path

from qgsdk import manifest as m
from qgsdk.layout import build_environment, qt_dir
from qgsdk.provision import aqt_commands


def test_the_manifest_pins_everything_exactly():
    data = json.loads(m.DEFAULT_MANIFEST.read_text())
    assert re.fullmatch(r"[0-9a-f]{64}", data["python"]["windows"]["sha256"])
    assert re.search(r"/archive/[0-9a-f]{40}\.zip$", data["aqtinstall"]["requirement"])  # a commit, not a branch
    loaded = m.load()
    assert re.fullmatch(r"\d+\.\d+\.\d+", loaded.qt_version)
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", t.version) for t in loaded.platform("windows").tools)
    for d in loaded.platform("windows").downloads:  # every download: https, and a SHA-256 to check
        assert d.url.startswith("https://") and re.fullmatch(r"[0-9a-f]{64}", d.sha256)


def test_qt_is_at_or_above_the_floor():
    loaded = m.load()
    version = tuple(int(x) for x in loaded.qt_version.split("."))
    floor = tuple(int(x) for x in loaded.qt_floor.split("."))
    assert version[: len(floor)] >= floor


def test_windows_uses_mingw_and_its_tools():
    windows = m.load().platform("windows")
    assert windows.arch == "win64_mingw"
    assert [t.name for t in windows.tools] == ["MinGW", "CMake", "Ninja"]
    assert [d.name for d in windows.downloads] == ["NSIS"]  # QGLogger's installer


def test_linux_uses_the_system_compiler_and_qts_tools():
    linux = m.load().platform("linux")
    assert linux.arch == "linux_gcc_64" and linux.directory == "gcc_64"
    assert [t.name for t in linux.tools] == ["CMake", "Ninja"]  # GCC comes from the system
    assert linux.downloads == ()


def test_python_is_pinned_for_every_platform():
    data = json.loads(m.DEFAULT_MANIFEST.read_text())
    for name in ("windows", "linux"):
        assert data["python"][name]["url"].startswith("https://")
        assert re.fullmatch(r"[0-9a-f]{64}", data["python"][name]["sha256"])


def test_aqtinstall_commands():
    loaded = m.load()
    commands = aqt_commands(Path("/sdk"), loaded, loaded.platform("windows"))
    assert commands[0][2:7] == ["aqt", "install-qt", "windows", "desktop", loaded.qt_version]
    assert commands[0][-1] == str(Path("/sdk/Qt"))
    assert [c[6] for c in commands[1:]] == ["tools_mingw1310", "tools_cmake", "tools_ninja"]  # python -m aqt install-tool windows desktop <tool>


def test_the_build_environment_puts_qt_and_the_tools_first():
    loaded = m.load()
    windows = loaded.platform("windows")
    env = build_environment(Path("/sdk"), loaded, windows, base={"PATH": "/usr/bin"})
    parts = env["PATH"].split(__import__("os").pathsep)
    assert parts[0] == str(qt_dir(Path("/sdk"), loaded, windows) / "bin")
    assert parts[-1] == "/usr/bin"
    assert parts[-2] == str(Path("/sdk/tools/NSIS/nsis-3.13"))  # makensis, for CPack
    assert env["CMAKE_PREFIX_PATH"] == str(Path(f"/sdk/Qt/{loaded.qt_version}/mingw_64"))


def test_an_unsupported_platform_says_so():
    import pytest

    with pytest.raises(SystemExit, match="doesn't support"):
        m.load().platform("amiga")


def test_install_skips_what_matches_the_record(tmp_path):
    from qgsdk.provision import RECORD, components, needed

    loaded = m.load()
    windows = loaded.platform("windows")
    assert len(needed(tmp_path, loaded, windows)) == 5  # nothing installed: Qt, MinGW, CMake, Ninja, NSIS

    for c in components(tmp_path, loaded, windows):  # as if installed
        c.path.mkdir(parents=True)
    record = {c.key: c.identity for c in components(tmp_path, loaded, windows)}
    (tmp_path / "Qt" / RECORD).write_text(json.dumps(record))
    assert needed(tmp_path, loaded, windows) == []
    assert len(needed(tmp_path, loaded, windows, force=True)) == 5

    record["tools_cmake"] = "qt.tools.cmake 3.29.0"  # the manifest moved CMake on
    (tmp_path / "Qt" / RECORD).write_text(json.dumps(record))
    assert [c.key for c in needed(tmp_path, loaded, windows)] == ["tools_cmake"]  # same folder, still reinstalled


def test_a_download_is_checked_before_it_is_unpacked(tmp_path, monkeypatch):
    import io
    import zipfile

    import pytest

    from qgsdk import provision
    from qgsdk.manifest import Download

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("tool-1.0/tool.exe", b"x")
    payload = buf.getvalue()
    monkeypatch.setattr(provision.urllib.request, "urlopen", lambda url, timeout, context: io.BytesIO(payload))

    good = Download("Tool", "1.0", "https://example.org/tool-1.0.zip", __import__("hashlib").sha256(payload).hexdigest(), "tool-1.0")
    provision.fetch(tmp_path, good)
    assert (tmp_path / "tools" / "Tool" / "tool-1.0" / "tool.exe").is_file()

    bad = Download("Bad", "1.0", "https://example.org/bad-1.0.zip", "0" * 64, "bad-1.0")
    with pytest.raises(SystemExit, match="SHA-256 mismatch"):
        provision.fetch(tmp_path, bad)
    assert not (tmp_path / "tools" / "Bad").exists()  # nothing unpacked
