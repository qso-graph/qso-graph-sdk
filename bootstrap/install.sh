#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
# QGSDK for Linux: one command to a working Qt build environment for QGLogger.
#
# Needs from the system what QGSDK can't install without root: a C++17 compiler (GCC), the OpenGL, EGL and
# xkbcommon headers Qt's CMake files look for, the system libraries Qt's Linux build links against (Qt's
# documented X11 requirements: D-Bus, fontconfig, FreeType, the xcb utility libraries, ...), and curl and
# tar. A desktop install usually has most of them. It checks for all of them first and, if any is
# missing, prints the command that installs them and stops before downloading anything. No root, no Qt
# account, no system Python.
#
# Everything goes under one folder (the prefix, default ./prefix beside this checkout); removing QGSDK
# is deleting that folder.
#
#   1. QGSDK's own Python (python-build-standalone, pinned and checked by SHA-256)
#   2. aqtinstall and QGSDK's tooling into a virtual environment (hash-locked)
#   3. Qt, CMake and Ninja (all versions from manifest.json)
#
# Safe to run again: it skips what's already there.
#
#   bootstrap/install.sh [--prefix DIR]
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$repo/prefix"
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --prefix=*) prefix="${1#*=}"; shift ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "install.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done

# --- 0. What the system must provide ---------------------------------------------------------------
# One install line per family; keep these in step with the README. (No curl on the dnf line: every system
# in that family has curl or curl-minimal, and asking for curl where curl-minimal is installed conflicts.)
dnf_line="sudo dnf install gcc-c++ mesa-libGL-devel mesa-libEGL-devel libxkbcommon-devel tar dbus-libs fontconfig freetype libbrotli glib2 libwayland-cursor libxkbcommon-x11 xcb-util xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm"
apt_line="sudo apt install g++ libgl-dev libegl-dev libxkbcommon-dev curl tar libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0 libwayland-cursor0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-util1 libxcb-xkb1"
# The libraries Qt's Linux build (and its xcb platform plugin) load from the system.
qt_system_libs="libdbus-1.so.3 libfontconfig.so.1 libfreetype.so.6 libglib-2.0.so.0 libgthread-2.0.so.0
  libwayland-cursor.so.0 libxkbcommon-x11.so.0 libxcb-cursor.so.0 libxcb-icccm.so.4 libxcb-image.so.0
  libxcb-keysyms.so.1 libxcb-render-util.so.0 libxcb-render.so.0 libxcb-shape.so.0 libxcb-util.so.1 libxcb-xkb.so.1"
missing=()
for tool in curl tar sha256sum g++; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
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
done
if [ ${#missing[@]} -gt 0 ]; then
    echo "QGSDK needs these from your system first: ${missing[*]}" >&2
    echo "Install them with:" >&2
    echo "  Fedora / RHEL / Rocky / Alma:  $dnf_line" >&2
    echo "  Debian / Ubuntu:               $apt_line" >&2
    echo "Nothing was installed." >&2
    exit 1
fi

manifest_value() {  # manifest_value python.linux.url -> the value, read without Python (none yet)
    sed -n '/"python"/,/^  }/p' "$repo/manifest.json" | sed -n "/\"linux\"/,/}/s/.*\"$1\": *\"\([^\"]*\)\".*/\1/p" | head -1
}

mkdir -p "$prefix"
prefix="$(cd "$prefix" && pwd)"
downloads="$prefix/downloads"
mkdir -p "$downloads"

# --- 1. QGSDK's own Python -------------------------------------------------------------------------
python="$prefix/python/bin/python3"
if [ ! -x "$python" ]; then
    url="$(manifest_value url)"
    sha="$(manifest_value sha256)"
    archive="$downloads/python-linux.tar.gz"
    echo "QGSDK: downloading Python"
    curl -fsSL -o "$archive" "$url"
    got="$(sha256sum "$archive" | cut -c1-64)"
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

# --- 3. Qt and the build tools ---------------------------------------------------------------------
qgsdk="$venv/bin/qgsdk"
"$qgsdk" --prefix "$prefix" install
"$qgsdk" --prefix "$prefix" env --shell sh > "$prefix/qgsdk-env.sh"
"$qgsdk" --prefix "$prefix" doctor

echo
echo "QGSDK is ready. In your QGLogger checkout, load its environment, then build and package with CMake:"
echo "  . $prefix/qgsdk-env.sh"
echo "  cmake --preset release && cmake --build --preset release && cpack --preset release"
