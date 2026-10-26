# QSO Graph SDK (QGSDK)

The build kit for QSO Graph's applications: the tools it takes to compile and package them, installed
with one command, at pinned versions. Part of the [qso-graph](https://github.com/qso-graph) family of
amateur-radio tools; sister to JTSDK (WSJT-X) and FLSDK (fldigi).

**Choose what you work on, and get exactly its tools.** Each kind of work is a *profile*:

| Profile | For | Installs |
|---|---|---|
| `logger` | QSO Graph Logger, the Qt application | Qt, its compiler, CMake, Ninja; NSIS on Windows for the installer |
| `mcp` | qso-graph's MCP servers | uv, and the Pythons the servers test against (3.11 to 3.13); git on Windows |

Install one or several; run the installer again with another profile to add it. A QSO Graph Desktop
profile is planned ([#4](https://github.com/qso-graph/qso-graph-sdk/issues/4)).

**Why it exists.** A program nobody else can build is a program nobody else can keep alive. QGSDK writes
down, as code, everything it takes to build an application, so a new maintainer starts from one command
instead of from someone's memory.

QGSDK is the tooling; an application is compiled and packaged from its own checkout, with these tools.

## What each profile installs

| | Version | Windows | Linux | macOS | For |
|---|---|---|---|---|---|
| **logger** | | | | | |
| Qt | 6.12.0 | MinGW build | GCC build | universal build (Apple silicon and Intel) | the framework the logger is written in |
| Compiler | | MinGW 13.1.0, Qt's own, matched to Qt's libraries | the system's GCC | Apple's clang (Xcode command-line tools) | |
| CMake | 3.30.5 | ✓ | ✓ | ✓ | configures and builds; CPack makes the packages |
| Ninja | 1.12.1 | ✓ | ✓ | ✓ | runs the build |
| NSIS | 3.13 | ✓ | | | the Windows installer |
| **mcp** | | | | | |
| uv | 0.13.5 | ✓ | ✓ | ✓ | the servers' environments, tests and builds |
| Python | 3.11 to 3.13 | ✓ | ✓ | ✓ | installed by uv, inside the prefix |
| git | | MinGit 2.56.0 | the system's | the Xcode command-line tools' | |
| **every profile** | | | | | |
| Python | 3.13.16 | ✓ | ✓ | ✓ | QGSDK's own scripts only; never part of an application |

What QGSDK can't install without root or admin rights comes from the system, and the installer checks
for it first: on Linux a C++ compiler and the libraries Qt uses (logger) and git (mcp); on macOS Apple's
Xcode command-line tools (both). It names what's missing, with the one command that installs it.

Every version is pinned, and every download checked, in [`manifest.json`](manifest.json): the one
place to change them.

## Developer setup (Windows)

You need nothing installed first: no Python, no git, no Visual Studio, no Qt account, no admin rights.

1. Get QGSDK: clone this repository, or download it as a zip and unpack it.
2. Install the tools for your profiles (once; the logger is about 2 GB and a few minutes):

   ```powershell
   powershell -ExecutionPolicy Bypass -File bootstrap\install.ps1 -Profiles logger,mcp
   ```

   Leave out `-Profiles` and it asks. Everything goes into `.\prefix` beside this checkout. Running it
   again installs only what's missing or changed. Removing QGSDK is deleting the folder.
3. Load the tools into your shell, whenever you open a new one:

   ```powershell
   . .\prefix\qgsdk-env.ps1        # PowerShell
   prefix\qgsdk-env.cmd            # cmd
   ```

4. Work in the application's checkout: build the logger with CMake; work on an MCP server with `uv`.

`qgsdk doctor` shows what's installed and where; `qgsdk profiles` lists the profiles. `qgsdk build
--source <logger checkout>` is a shortcut for the logger's configure-and-build step; you never need it.

## Developer setup (Linux)

Tested on Rocky Linux 9, Debian 12 and Ubuntu 24.04; any x86-64 distribution of that age or newer
should work.

1. Install what your profiles need from your distribution (the one step that needs root). For both
   profiles:

   ```sh
   # Fedora / RHEL / Rocky / Alma
   sudo dnf install gcc-c++ mesa-libGL-devel mesa-libEGL-devel libxkbcommon-devel tar dbus-libs fontconfig freetype libbrotli glib2 libwayland-cursor libxkbcommon-x11 xcb-util xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm git
   # Debian / Ubuntu
   sudo apt install g++ libgl-dev libegl-dev libxkbcommon-dev curl tar libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0 libwayland-cursor0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-util1 libxcb-xkb1 git
   ```

   The `mcp` profile alone needs only `git`, `curl` and `tar`. The installer checks for everything its
   profiles need and prints the line for you if anything is missing.
2. Get QGSDK: clone this repository, or download and unpack it.
3. Install the tools for your profiles (once; the logger is about 2 GB, under a minute on a fast line).
   No root:

   ```sh
   bootstrap/install.sh --profile logger --profile mcp
   ```

4. Load the tools into your shell, whenever you open a new one:

   ```sh
   . ./prefix/qgsdk-env.sh
   ```

5. Work in the application's checkout, as on Windows.

## Developer setup (macOS)

macOS 14 or newer, Apple silicon or Intel.

1. Install Apple's Xcode command-line tools, if you haven't (the one step that needs an administrator):

   ```sh
   xcode-select --install
   ```

2. Get QGSDK: clone this repository, or download and unpack it.
3. Install the tools for your profiles (once). No root:

   ```sh
   bootstrap/install.sh --profile logger --profile mcp
   ```

   Leave out `--profile` and it asks. Everything goes into `./prefix`; running it again installs only
   what's missing or changed.
4. Load the tools into your shell, whenever you open a new one:

   ```sh
   . ./prefix/qgsdk-env.sh
   ```

5. Work in the application's checkout, as on Windows.

## Checking it works

On a clean machine (a fresh VM or container is best):

```powershell
powershell -ExecutionPolicy Bypass -File tests\windows-check.ps1     # Windows
```

```sh
tests/check.sh                                                        # Linux and macOS
```

Each installs QGSDK from nothing with every profile (or those named with `-Profiles` / `--profile`).
For the logger it builds a small Qt program, builds it again with plain CMake, and runs both (on
Windows it also checks NSIS runs); for mcp it runs each of the servers' Pythons through uv, and git,
and checks they are the prefix's. It ends with `== PASS` or `== FAIL: <what>`. CI runs them on
Windows, Linux and both kinds of Mac whenever the installer changes, and weekly.

## What it downloads, and their licences

None of these is part of this repository; each is downloaded from its publisher and used under its own
licence.

| Tool | Profile | Licence |
|---|---|---|
| Python (python.org's Windows build; python-build-standalone on Linux and macOS) | every profile | PSF-2.0 |
| aqtinstall, and its Python dependencies | every profile | MIT (each dependency its own) |
| Qt | logger | LGPL-3.0-only (open-source edition) |
| MinGW-w64 and GCC (Windows) | logger | GPL-3.0 with the GCC Runtime Library Exception; MinGW-w64's runtime ZPL-2.1 |
| CMake | logger | BSD-3-Clause |
| Ninja | logger | Apache-2.0 |
| NSIS (Windows) | logger | zlib/libpng, with parts under bzip2 and CPL-1.0 |
| uv | mcp | MIT OR Apache-2.0 |
| MinGit, from Git for Windows (Windows) | mcp | GPL-2.0-only |

## Learn more

- [docs/](docs/): how QGSDK works, and the decisions behind it (MinGW, aqtinstall, CMake presets, profiles)
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose a change
- Licence: **GPL-3.0-or-later** ([LICENSE](LICENSE), [NOTICE](NOTICE)), like JTSDK and FLSDK
