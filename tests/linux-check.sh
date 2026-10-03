#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
# QGSDK's check on Linux: from nothing, it gives this machine a working Qt build toolchain.
#
# Run it on a clean machine or container (with only the system packages bootstrap/install.sh asks for):
#   1. installs QGSDK (bootstrap/install.sh): Python, the tooling, Qt, CMake, Ninja;
#   2. builds the small Qt test program in tests/fixture with `qgsdk build`, and runs it;
#   3. builds it again with plain CMake, without QGSDK's wrapper (the deletion test: the wrapper must
#      stay optional, so a developer can use CMake directly or their IDE), and runs it.
#
# QGLogger itself is built and packaged from the QGLogger checkout: see QGLogger's README.
# Prints "== PASS" and exits 0 when everything works; otherwise "== FAIL: <what>" and exits 1. Programs
# run with --smoke (they quit once their window is up) on Qt's offscreen platform: no display needed.
#
#   tests/linux-check.sh [--prefix DIR]
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$repo/prefix"
[ "${1:-}" = "--prefix" ] && prefix="$2"
fixture="$repo/tests/fixture"

fail() { echo "== FAIL: $*"; exit 1; }
smoke() {
    QT_QPA_PLATFORM=offscreen timeout 60 "$1" --smoke || fail "$1 --smoke exited with $?"
    echo "$1 started and exited cleanly"
}

echo "== 1. Install QGSDK"
"$repo/bootstrap/install.sh" --prefix "$prefix" || fail "bootstrap/install.sh"
prefix="$(cd "$prefix" && pwd)"

echo "== 2. Build the fixture with qgsdk build, and run it"
"$prefix/venv/bin/qgsdk" --prefix "$prefix" build release --source "$fixture" || fail "qgsdk build"
smoke "$fixture/build/release/qgsdk-fixture"

echo "== 3. The deletion test: the same program with plain CMake, no QGSDK wrapper"
# shellcheck disable=SC1091
. "$prefix/qgsdk-env.sh"
(cd "$fixture" && cmake --preset debug && cmake --build --preset debug) || fail "plain CMake build"
smoke "$fixture/build/debug/qgsdk-fixture"

echo "== PASS: QGSDK installed; the fixture built with and without its wrapper, and ran"
