# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""QGSDK: one command to a working Qt build environment for QGLogger, and thin wrappers over its CMake build.

The pieces:
- manifest.py  reads manifest.json, the single list of pinned versions.
- layout.py    where everything lives under the SDK's prefix, and the environment a build needs.
- provision.py installs Qt and its tools with aqtinstall.
- cli.py       the `qgsdk` command: install, env, build, doctor.
"""

__version__ = "0.1.0"
