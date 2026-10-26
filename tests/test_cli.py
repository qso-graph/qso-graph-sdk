# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
from qgsdk.cli import shell_lines


def test_path_is_prepended_not_replaced():
    first = [r"C:\sdk\Qt\6.12.0\mingw_64\bin", r"C:\sdk\Qt\Tools\Ninja"]
    assert shell_lines({}, [], "powershell", path_first=first) == [r'$env:PATH = "C:\sdk\Qt\6.12.0\mingw_64\bin;C:\sdk\Qt\Tools\Ninja;" + $env:PATH']
    assert shell_lines({}, [], "cmd", path_first=first) == [r'set "PATH=C:\sdk\Qt\6.12.0\mingw_64\bin;C:\sdk\Qt\Tools\Ninja;%PATH%"']
    assert shell_lines({}, [], "sh", path_first=["/sdk/bin", "/sdk/ninja"]) == ["export PATH='/sdk/bin:/sdk/ninja':\"$PATH\""]


def test_env_lines_for_each_shell():
    env = {"CMAKE_PREFIX_PATH": r"C:\sdk\Qt\6.12.0\mingw_64"}
    assert shell_lines(env, ["CMAKE_PREFIX_PATH"], "powershell") == [r'$env:CMAKE_PREFIX_PATH = "C:\sdk\Qt\6.12.0\mingw_64"']
    assert shell_lines(env, ["CMAKE_PREFIX_PATH"], "cmd") == [r'set "CMAKE_PREFIX_PATH=C:\sdk\Qt\6.12.0\mingw_64"']
    assert shell_lines(env, ["CMAKE_PREFIX_PATH"], "sh") == [r"export CMAKE_PREFIX_PATH='C:\sdk\Qt\6.12.0\mingw_64'"]


def test_select_adds_to_what_was_chosen_and_remembers_it(tmp_path, monkeypatch):
    import pytest

    from qgsdk import manifest
    from qgsdk.cli import select

    loaded = manifest.load()
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit, match="Choose a profile with --profile"):
        select(tmp_path, loaded, [])  # nothing chosen, nobody to ask
    assert select(tmp_path, loaded, ["mcp"]) == ["mcp"]
    assert select(tmp_path, loaded, ["logger", "mcp"]) == ["mcp", "logger"]
    assert select(tmp_path, loaded, []) == ["mcp", "logger"]
    with pytest.raises(SystemExit, match="no profile 'nope'"):
        select(tmp_path, loaded, ["nope"])


def test_asking_takes_numbers_names_or_all(monkeypatch, capsys):
    from qgsdk import manifest
    from qgsdk.cli import ask

    loaded = manifest.load()
    answers = iter(["9", "2 1"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))
    assert ask(loaded) == ["mcp", "logger"]  # "9" refused, then asked again
    assert "Choose from 1-2" in capsys.readouterr().err
    monkeypatch.setattr("builtins.input", lambda: "all")
    assert ask(loaded) == ["logger", "mcp"]
    monkeypatch.setattr("builtins.input", lambda: "mcp,logger")
    assert ask(loaded) == ["mcp", "logger"]
