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
