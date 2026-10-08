# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
"""__version__ is the installed distribution's version, not a second copy of it."""

from importlib.metadata import version

import qgsdk


def test_version_matches_distribution():
    assert qgsdk.__version__ == version("qgsdk")
