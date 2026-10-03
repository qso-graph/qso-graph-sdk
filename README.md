# QSO Graph SDK (QGSDK)

The build kit for [QSO Graph Logger](https://github.com/qso-graph/qso-graph-logger) (QGLogger): the
tools it takes to compile and package it, installed with one command, at pinned versions. Part of the
[qso-graph](https://github.com/qso-graph) family of amateur-radio tools; sister to JTSDK (WSJT-X) and
FLSDK (fldigi).

**Why it exists.** A program nobody else can build is a program nobody else can keep alive. QGSDK writes
down, as code, everything it takes to build QGLogger, so a new maintainer starts from one command instead
of from someone's memory.

QGSDK is the tooling. QGLogger is compiled and packaged from its own checkout, with these tools: see
[QGLogger's README](https://github.com/qso-graph/qso-graph-logger#readme).

## What it installs

| | Version | For |
|---|---|---|
| Qt | 6.12.0 (MinGW build on Windows, GCC build on Linux) | the framework QGLogger is written in |
| MinGW | 13.1.0 | Windows: the C++ compiler, Qt's own, matched to Qt's libraries |
| CMake | 3.30.5 | configures and builds QGLogger; CPack makes its packages |
| Ninja | 1.12.1 | runs the build |
| NSIS | 3.13 | Windows: makes QGLogger's installer |
| Python | 3.13.16 | QGSDK's own scripts only; never part of QGLogger |

On Linux the compiler is the system's GCC (Qt's Linux build is made with GCC), and a few system
libraries Qt needs come from your distribution: see the Linux setup.

Every version is pinned, and every download checked, in [`manifest.json`](manifest.json): the one
place to change them.

## Developer setup (Windows)

You need nothing installed first: no Python, no git, no Visual Studio, no Qt account, no admin rights.

1. Get QGSDK: clone this repository, or download it as a zip and unpack it.
2. Install the tools (once; about 2 GB, a few minutes):

   ```powershell
   powershell -ExecutionPolicy Bypass -File bootstrap\install.ps1
   ```

   Everything goes into `.\prefix` beside this checkout. Running it again installs only what's missing
   or changed. Removing QGSDK is deleting the folder.
3. Load the tools into your shell, whenever you open a new one:

   ```powershell
   . .\prefix\qgsdk-env.ps1        # PowerShell
   prefix\qgsdk-env.cmd            # cmd
   ```

4. Compile and package QGLogger from its checkout: [QGLogger's README](https://github.com/qso-graph/qso-graph-logger#readme).

`qgsdk doctor` shows what's installed and where. `qgsdk build --source <logger checkout>` is a shortcut
for QGLogger's configure-and-build step; you never need it.

## Developer setup (Linux)

Tested on Rocky Linux 9 and Debian 12; any x86-64 distribution of that age or newer should work.

1. Install what QGSDK needs from your distribution (the one step that needs root): a C++ compiler,
   the OpenGL headers, and the libraries Qt's Linux build uses. A desktop install has most of them.

   ```sh
   # Fedora / RHEL / Rocky / Alma
   sudo dnf install gcc-c++ mesa-libGL-devel mesa-libEGL-devel libxkbcommon-devel tar dbus-libs fontconfig freetype libbrotli glib2 libwayland-cursor libxkbcommon-x11 xcb-util xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm
   # Debian / Ubuntu
   sudo apt install g++ libgl-dev libegl-dev libxkbcommon-dev curl tar libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0 libwayland-cursor0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-util1 libxcb-xkb1
   ```

   The installer checks for all of these and prints this line for you if anything is missing.
2. Get QGSDK: clone this repository, or download and unpack it.
3. Install the tools (once; about 2 GB, under a minute on a fast line). No root:

   ```sh
   bootstrap/install.sh
   ```

   Everything goes into `./prefix`; running it again installs only what's missing or changed.
4. Load the tools into your shell, whenever you open a new one:

   ```sh
   . ./prefix/qgsdk-env.sh
   ```

5. Compile and package QGLogger from its checkout: [QGLogger's README](https://github.com/qso-graph/qso-graph-logger#readme).

macOS comes later.

## Checking it works

On a clean machine (a fresh VM or container is best):

```powershell
powershell -ExecutionPolicy Bypass -File tests\windows-check.ps1     # Windows
```

```sh
tests/linux-check.sh                                                  # Linux
```

Each installs QGSDK from nothing, builds a small Qt program with it, builds it again with plain CMake,
and runs both (on Windows it also checks NSIS runs). It ends with `== PASS` or `== FAIL: <what>`.

## Learn more

- [docs/](docs/): how QGSDK works, and the decisions behind it (MinGW, aqtinstall, CMake presets)
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose a change
- Licence: **GPL-3.0-or-later** ([LICENSE](LICENSE), [NOTICE](NOTICE)), like JTSDK and FLSDK
