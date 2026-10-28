# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""Every Python QGSDK ships or tests on is a release past the eMudhra CA advisory."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

# The first releases that reject the compromised eMudhra intermediate CAs
# (2026-10). Raise these when an advisory moves them; never lower them.
PATCHED = {(3, 11): 18, (3, 12): 16, (3, 13): 18, (3, 14): 10, (3, 15): 2}
VERSION = re.compile(r"""python-version:\s*(\[[^\]]*\]|["']?[^"'\s#,}]+["']?)""")


def _check(where: str, v: str) -> None:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
    assert m, f"{where} asks for Python {v!r}; ask for an exact patch release"
    major, minor, patch = map(int, m.groups())
    floor = PATCHED.get((major, minor))
    assert floor is not None, f"{where}: Python {v} is a line this test does not know"
    assert patch >= floor, f"{where}: Python {v} is older than {major}.{minor}.{floor}"


def test_the_python_qgsdk_ships() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    python = manifest["python"]
    _check("manifest.json", python["version"])
    for platform, entry in python.items():
        if isinstance(entry, dict):
            assert python["version"] in entry["url"], f"{platform}'s download is not {python['version']}"


def test_the_pythons_ci_asks_for() -> None:
    """"3.12" means "any 3.12", which on ubuntu-latest was 3.12.3: unpatched."""
    found = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        for m in VERSION.finditer(wf.read_text()):
            for v in re.findall(r"[\w.${}\-]+", m.group(1)):
                if not v.startswith("$"):  # ${{ matrix.python-version }}
                    found.append(v)
                    _check(wf.name, v)
    assert found, "the pattern found no python-version: this test is broken"
