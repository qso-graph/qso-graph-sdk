#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
# QGSDK's check on Linux and macOS: from nothing, each profile gives this machine what it promises.
#
# Run it on a clean machine or container (with only what bootstrap/install.sh asks the system for):
#   1. installs QGSDK with the profiles (bootstrap/install.sh); default: every profile;
#   logger:
#   2. builds the small Qt test program in tests/fixture with `qgsdk build`, and runs it;
#   3. builds it again with plain CMake, without QGSDK's wrapper (the deletion test: the wrapper must
#      stay optional, so a developer can use CMake directly or their IDE), and runs it;
#   mcp:
#   4. runs each Python the MCP servers test against, through uv, and git; uv's Pythons are in the prefix;
#   desktop:
#   5. clones QSO Graph Desktop (QGSDK_DESKTOP_REF, default main), checks its pinned Node.js and Rust are
#      the versions QGSDK installed, and runs its setup and its fast check (make setup, make check).
#
# Prints "== PASS" and exits 0 when everything works; otherwise "== FAIL: <what>" and exits 1. Programs
# run with --smoke (they quit once their window is up) on Qt's offscreen platform: no display needed.
#
#   tests/check.sh [--prefix DIR] [--profile desktop|logger|mcp ...]
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$repo/prefix"
profiles=()
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --profile) profiles+=("$2"); shift 2 ;;
        *) echo "check.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done
[ ${#profiles[@]} -gt 0 ] || profiles=(desktop logger mcp)
fixture="$repo/tests/fixture"

fail() { echo "== FAIL: $*"; exit 1; }
smoke() {
    # macOS has no `timeout`; there the program is trusted to quit once its window is up.
    local limit=()
    command -v timeout >/dev/null 2>&1 && limit=(timeout 60)
    QT_QPA_PLATFORM=offscreen ${limit[@]+"${limit[@]}"} "$1" --smoke || fail "$1 --smoke exited with $?"
    echo "$1 started and exited cleanly"
}
has() { case " ${profiles[*]} " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

echo "== 1. Install QGSDK: ${profiles[*]}"
args=()
for p in "${profiles[@]}"; do args+=(--profile "$p"); done
"$repo/bootstrap/install.sh" --prefix "$prefix" "${args[@]}" </dev/null || fail "bootstrap/install.sh"
prefix="$(cd "$prefix" && pwd)"

if has logger; then
    echo "== 2. Build the fixture with qgsdk build, and run it"
    "$prefix/venv/bin/qgsdk" --prefix "$prefix" build release --source "$fixture" || fail "qgsdk build"
    smoke "$fixture/build/release/qgsdk-fixture"

    echo "== 3. The deletion test: the same program with plain CMake, no QGSDK wrapper"
    (
        # shellcheck disable=SC1091
        . "$prefix/qgsdk-env.sh" || exit 1
        cd "$fixture" && cmake --preset debug && cmake --build --preset debug
    ) || fail "plain CMake build"
    smoke "$fixture/build/debug/qgsdk-fixture"
fi

if has mcp; then
    echo "== 4. uv, the MCP servers' Pythons, and git"
    (
        # shellcheck disable=SC1091
        . "$prefix/qgsdk-env.sh" || exit 1
        case "$(command -v uv)" in "$prefix"/*) ;; *) echo "uv is not the prefix's: $(command -v uv)"; exit 1 ;; esac
        for v in 3.11 3.12 3.13; do
            found="$(uv python find --managed-python "$v")" || { echo "uv has no Python $v"; exit 1; }
            case "$found" in "$prefix"/*) ;; *) echo "Python $v is not the prefix's: $found"; exit 1 ;; esac
            "$found" -c 'import sys, ssl; print(sys.version.split()[0], ssl.OPENSSL_VERSION)' || exit 1
        done
        git --version || exit 1
    ) || fail "the mcp profile"
fi

if has desktop; then
    echo "== 5. QSO Graph Desktop: its pins match, it builds, and its fast check passes"
    work="$(mktemp -d)"
    git clone -q --depth 1 --branch "${QGSDK_DESKTOP_REF:-main}" https://github.com/qso-graph/qso-graph-desktop.git "$work/desktop" \
        || fail "cloning QSO Graph Desktop"
    (
        # shellcheck disable=SC1091
        . "$prefix/qgsdk-env.sh" || exit 1
        cd "$work/desktop" || exit 1
        for tool in node npm cargo rustc go cmake; do
            case "$(command -v "$tool")" in "$prefix"/*) ;; *) echo "$tool is not the prefix's: $(command -v "$tool")"; exit 1 ;; esac
        done
        want="$(tr -d ' \n' < .node-version)"
        [ "$(node --version)" = "v$want" ] || { echo "Node.js $(node --version), but QSO Graph Desktop pins $want"; exit 1; }
        if [ -f rust-toolchain.toml ]; then
            want="$(sed -n 's/^channel *= *"\(.*\)"/\1/p' rust-toolchain.toml)"
            have="$("$prefix/venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["profiles"]["desktop"]["rust"])' "$repo/manifest.json")"
            [ "$have" = "$want" ] || { echo "QGSDK installs Rust $have, but QSO Graph Desktop pins $want"; exit 1; }
        fi
        rustc --version && go version && cmake --version | head -1
        # make setup, then make check. Chained with &&: bash ignores `set -e` inside ( ... ) || fail, so a failed step would not stop
        # the ones after it, and the last one alone would decide the result.
        npm ci && node scripts/fetch-adif.mjs && node scripts/fetch-counties.mjs && npm run build && node scripts/fetch-pota.mjs && npm run check
    ) || fail "QSO Graph Desktop with the desktop profile"
    rm -rf "$work"
fi

echo "== PASS: QGSDK installed ${profiles[*]}, and each did what it promises"
