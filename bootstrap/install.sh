#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
# QGSDK for Linux and macOS: one command to the tools for the QSO Graph software you work on.
#
# Choose profiles with --profile (repeat for more); with none, it asks. `logger` is Qt and its tools for
# QSO Graph Logger; `mcp` is uv and the Pythons the MCP servers test against; `desktop` is Node.js, Rust,
# Go and CMake for QSO Graph Desktop. Running it again with another profile adds it.
#
# Needs from the system what QGSDK can't install without root. Always: curl and tar. logger on Linux: a
# C++17 compiler (GCC), the OpenGL, EGL and xkbcommon headers and the libraries Qt's Linux build loads;
# desktop on Linux: a C/C++ compiler, make, git, unzip and libatomic; mcp on Linux: git; every profile on macOS: Apple's
# Xcode command-line tools (clang, make, git). It checks
# for them and, if any is missing, prints the command that installs them and stops before installing
# the profile. No root, no Qt account, no system Python.
#
# Everything goes under one folder (the prefix, default ./prefix beside this checkout); removing QGSDK
# is deleting that folder.
#
#   1. QGSDK's own Python (python-build-standalone, pinned and checked by SHA-256)
#   2. aqtinstall and QGSDK's tooling into a virtual environment (hash-locked)
#   3. the profiles: what each needs, at the versions in manifest.json
#
# Safe to run again: it skips what's already there.
#
#   bootstrap/install.sh [--prefix DIR] [--profile desktop|logger|mcp ...]
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$repo/prefix"
profiles=()
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --prefix=*) prefix="${1#*=}"; shift ;;
        --profile) profiles+=("$2"); shift 2 ;;
        --profile=*) profiles+=("${1#*=}"); shift ;;
        -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
        *) echo "install.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done

case "$(uname -s)" in
    Linux) os=linux ;;
    Darwin) os=macos ;;
    *) echo "QGSDK's install.sh is for Linux and macOS; on Windows use bootstrap\\install.ps1" >&2; exit 1 ;;
esac
machine="$(uname -m)"
[ "$machine" = aarch64 ] && machine=arm64

# --- 0. What every profile needs from the system ---------------------------------------------------
missing=()
for tool in curl tar; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [ ${#missing[@]} -gt 0 ]; then
    echo "QGSDK needs these from your system first: ${missing[*]}" >&2
    exit 1
fi
sha256() {  # sha256 FILE -> its SHA-256 (sha256sum on Linux, shasum on macOS)
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -c1-64; else shasum -a 256 "$1" | cut -c1-64; fi
}

python_value() {  # python_value KEY -> python.<os>-<machine>.KEY from manifest.json, read without Python (none yet)
    sed -n "/\"$os-$machine\": {/,/}/s/.*\"$1\": *\"\([^\"]*\)\".*/\1/p" "$repo/manifest.json" | head -1
}

mkdir -p "$prefix"
prefix="$(cd "$prefix" && pwd)"
downloads="$prefix/downloads"
mkdir -p "$downloads"

# --- 1. QGSDK's own Python -------------------------------------------------------------------------
python="$prefix/python/bin/python3"
if [ ! -x "$python" ]; then
    url="$(python_value url)"
    sha="$(python_value sha256)"
    if [ -z "$url" ]; then
        echo "QGSDK doesn't support $os on $machine yet. Nothing was installed." >&2
        exit 1
    fi
    archive="$downloads/python-$os-$machine.tar.gz"
    echo "QGSDK: downloading Python"
    curl -fsSL -o "$archive" "$url"
    got="$(sha256 "$archive")"
    if [ "$got" != "$sha" ]; then
        rm -f "$archive"
        echo "Python download doesn't match manifest.json (got $got). Nothing was installed." >&2
        exit 1
    fi
    tar -xzf "$archive" -C "$prefix"  # unpacks to $prefix/python
fi

# --- 2. aqtinstall and QGSDK's tooling, in a virtual environment ---------------------------------
venv="$prefix/venv"
if [ ! -x "$venv/bin/python" ]; then
    echo "QGSDK: creating the tooling environment"
    "$python" -m venv "$venv"
fi
pip=("$venv/bin/python" -m pip install --disable-pip-version-check --quiet)
# Every dependency comes from the hash-locked list; nothing else is fetched (bootstrap/tooling-requirements.txt).
"${pip[@]}" --require-hashes -r "$repo/bootstrap/tooling-requirements.txt"
# aqtinstall itself: pinned by commit (decision 0002), built with the locked build tools above.
aqt_requirement="$("$python" -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["aqtinstall"]["requirement"])' "$repo/manifest.json")"
aqt_version="$("$python" -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["aqtinstall"]["version"])' "$repo/manifest.json")"
SETUPTOOLS_SCM_PRETEND_VERSION="$aqt_version" "${pip[@]}" --no-deps --no-build-isolation "$aqt_requirement"
"${pip[@]}" --no-deps --no-build-isolation --editable "$repo"
qgsdk="$venv/bin/qgsdk"

# --- 3. The profiles: chosen (asked, if none are), each one's system check, then installed ---------
select_args=()
for p in ${profiles[@]+"${profiles[@]}"}; do select_args+=(--profile "$p"); done
chosen="$("$qgsdk" --prefix "$prefix" select ${select_args[@]+"${select_args[@]}"})"
echo "QGSDK: profiles $chosen"

# One install line per family; keep these in step with the README. (No curl on the dnf line: every system
# in that family has curl or curl-minimal, and asking for curl where curl-minimal is installed conflicts.)
dnf_logger="gcc-c++ mesa-libGL-devel mesa-libEGL-devel libxkbcommon-devel dbus-libs fontconfig freetype libbrotli glib2 libwayland-cursor libxkbcommon-x11 xcb-util xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm"
apt_logger="g++ libgl-dev libegl-dev libxkbcommon-dev libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0 libwayland-cursor0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-util1 libxcb-xkb1"
# The libraries Qt's Linux build (and its xcb platform plugin) load from the system.
qt_system_libs="libdbus-1.so.3 libfontconfig.so.1 libfreetype.so.6 libglib-2.0.so.0 libgthread-2.0.so.0
  libwayland-cursor.so.0 libxkbcommon-x11.so.0 libxcb-cursor.so.0 libxcb-icccm.so.4 libxcb-image.so.0
  libxcb-keysyms.so.1 libxcb-render-util.so.0 libxcb-render.so.0 libxcb-shape.so.0 libxcb-util.so.1 libxcb-xkb.so.1"
missing=()
dnf=""; apt=""
needs_xcode=no
for profile in $chosen; do
    case "$os:$profile" in
        linux:logger)
            dnf="$dnf $dnf_logger"; apt="$apt $apt_logger"
            command -v g++ >/dev/null 2>&1 || missing+=(g++)
            # The headers, as the compiler finds them (not by guessing paths).
            if command -v g++ >/dev/null 2>&1; then
                for header in GL/gl.h EGL/egl.h xkbcommon/xkbcommon.h; do
                    echo "#include <$header>" | g++ -E -x c++ - >/dev/null 2>&1 || missing+=("$header")
                done
                echo 'int main() { return __cplusplus >= 201703L ? 0 : 1; }' | g++ -std=c++17 -x c++ -o /dev/null - 2>/dev/null \
                    || missing+=("a C++17 compiler")
            fi
            ldconfig_cmd="$(command -v ldconfig || echo /sbin/ldconfig)"
            known_libs="$("$ldconfig_cmd" -p 2>/dev/null || true)"
            for lib in $qt_system_libs; do
                grep -q "^[[:space:]]*$lib " <<<"$known_libs" || missing+=("$lib")
            done ;;
        linux:mcp)
            dnf="$dnf git"; apt="$apt git"
            command -v git >/dev/null 2>&1 || missing+=(git) ;;
        linux:desktop)
            # The credential core's C parts (AWS-LC's FIPS module) and npm's native builds; and libatomic,
            # which Node.js's own Linux build loads (a minimal install lacks it).
            # unzip: its setup unpacks ADIF's release with it.
            dnf="$dnf gcc gcc-c++ make git unzip libatomic"; apt="$apt build-essential git unzip libatomic1"
            for tool in cc c++ make git unzip; do
                command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
            done
            ldconfig_cmd="$(command -v ldconfig || echo /sbin/ldconfig)"
            "$ldconfig_cmd" -p 2>/dev/null | grep -q "^[[:space:]]*libatomic.so.1 " || missing+=(libatomic.so.1) ;;
        macos:*)
            # clang (logger, desktop), make and git all come with Apple's Xcode command-line tools. On a Mac
            # without them, /usr/bin/git and clang++ exist but only offer to install them, so ask
            # xcode-select whether they are really there.
            needs_xcode=yes ;;
    esac
done
if [ "$needs_xcode" = yes ] && ! xcode-select -p >/dev/null 2>&1; then
    missing+=("the Xcode command-line tools")
fi
if [ ${#missing[@]} -gt 0 ]; then
    echo "QGSDK needs these from your system first: ${missing[*]}" >&2
    echo "Install them with:" >&2
    if [ "$os" = linux ]; then
        echo "  Fedora / RHEL / Rocky / Alma:  sudo dnf install $(tr ' ' '\n' <<<"$dnf" | awk 'NF && !seen[$0]++' | xargs)" >&2
        echo "  Debian / Ubuntu:               sudo apt install $(tr ' ' '\n' <<<"$apt" | awk 'NF && !seen[$0]++' | xargs)" >&2
    else
        echo "  xcode-select --install" >&2
    fi
    echo "Nothing more was installed." >&2
    exit 1
fi

"$qgsdk" --prefix "$prefix" install
"$qgsdk" --prefix "$prefix" env --shell sh > "$prefix/qgsdk-env.sh"
"$qgsdk" --prefix "$prefix" doctor

echo
echo "QGSDK is ready. Load its environment in each new shell:"
echo "  . $prefix/qgsdk-env.sh"
case " $chosen " in
    *" logger "*) echo "Then, in the logger's checkout: cmake --preset release && cmake --build --preset release && cpack --preset release" ;;
esac
case " $chosen " in
    *" mcp "*) echo "Then, in an MCP server's checkout: uv sync --group dev && uv run pytest" ;;
esac
case " $chosen " in
    *" desktop "*) echo "Then, in QSO Graph Desktop's checkout: make setup && make check" ;;
esac
