# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""QGSDK: one command to the tools for the QSO Graph software you work on, chosen by profile (desktop, logger, mcp).

The pieces:
- manifest.py  reads manifest.json, the single list of pinned versions, grouped by profile.
- layout.py    where everything lives under the SDK's prefix, and the environment the profiles need.
- provision.py installs Qt and its tools with aqtinstall, the other downloads, and uv's Pythons.
- cli.py       the `qgsdk` command: profiles, select, install, env, build, doctor.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    # Read from the installed distribution, so pyproject.toml is the only place the version is written.
    __version__ = version("qgsdk")
except PackageNotFoundError:  # source tree without dist metadata
    __version__ = "0.0.0-dev"
