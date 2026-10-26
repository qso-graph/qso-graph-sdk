# QSO Graph SDK (QGSDK)

The build kit for QSO Graph's applications: the tools it takes to compile and package them, installed
with one command, at pinned versions. Part of the [qso-graph](https://github.com/qso-graph) family of
amateur-radio tools; sister to JTSDK (WSJT-X) and FLSDK (fldigi).

**Choose what you work on, and get exactly its tools.** Each kind of work is a *profile*:

| Profile | For | Installs |
|---|---|---|
| `desktop` | QSO Graph Desktop, the Electron hub | Node.js, Rust, and Go and CMake for its FIPS crypto module; on Windows also Ninja, NASM, libclang and git |
| `logger` | QSO Graph Logger, the Qt application | Qt, its compiler, CMake, Ninja; NSIS on Windows for the installer |
| `mcp` | qso-graph's MCP servers | uv, and the Pythons the servers test against (3.11 to 3.13); git on Windows |

Install one or several; run the installer again with another profile to add it.

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
| **desktop** | | | | | |
| Node.js | 26.9.0 | ✓ | ✓ | ✓ | the application, and its build |
| Rust | 1.99.1 | ✓ | ✓ | ✓ | the credential core; installed with rustup, inside the prefix |
| Go | 1.27.3 | ✓ | ✓ | ✓ | building AWS-LC's FIPS module |
| CMake | 4.4.4 | ✓ | ✓ | ✓ | building AWS-LC's FIPS module |
| Ninja, NASM | 1.13.2, 3.02 | ✓ | | | building AWS-LC's FIPS module on Windows |
| libclang | 23.1.4 | ✓ | | | bindgen, which the FIPS module needs on Windows (only libclang and its headers are unpacked) |
| C/C++ compiler | | Microsoft's C++ Build Tools (needs an administrator) | the system's GCC | Apple's clang (Xcode command-line tools) | |
| git | | MinGit 2.56.0 | the system's | the Xcode command-line tools' | |
| **mcp** | | | | | |
| uv | 0.13.5 | ✓ | ✓ | ✓ | the servers' environments, tests and builds |
| Python | 3.11 to 3.13 | ✓ | ✓ | ✓ | installed by uv, inside the prefix |
| git | | MinGit 2.56.0 | the system's | the Xcode command-line tools' | |
| **every profile** | | | | | |
| Python | 3.13.16 | ✓ | ✓ | ✓ | QGSDK's own scripts only; never part of an application |

What QGSDK can't install without root or admin rights comes from the system, and the installer checks
for it first: on Windows Microsoft's C++ Build Tools (desktop); on Linux a C++ compiler and the
libraries Qt uses (logger), a C/C++ compiler, make, unzip and libatomic (desktop), and git (desktop, mcp); on
macOS Apple's Xcode command-line tools (every profile). It names what's missing, with the one command
that installs it. Linux arm64 (a Raspberry Pi 5) has the desktop and mcp profiles; Qt's Linux build,
and so the logger, is x86-64 only.

Every version is pinned, and every download checked, in [`manifest.json`](manifest.json): the one
place to change them.

## Developer setup (Windows)

You need nothing installed first: no Python, no git, no Visual Studio, no Qt account, no admin rights.
The one exception is the desktop profile: Rust on Windows links with Microsoft's C++ Build Tools, which
only Microsoft's installer can install, as an administrator. The installer checks and, if they're
missing, prints the one command:

```powershell
winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

1. Get QGSDK: clone this repository, or download it as a zip and unpack it.
2. Install the tools for your profiles (once; the logger is about 2 GB and a few minutes):

   ```powershell
   powershell -ExecutionPolicy Bypass -File bootstrap\install.ps1 -Profiles desktop,mcp
   ```

   Leave out `-Profiles` and it asks. Everything goes into `.\prefix` beside this checkout. Running it
   again installs only what's missing or changed. Removing QGSDK is deleting the folder.
3. Load the tools into your shell, whenever you open a new one:

   ```powershell
   . .\prefix\qgsdk-env.ps1        # PowerShell
   prefix\qgsdk-env.cmd            # cmd
   ```

4. Work in the application's checkout: QSO Graph Desktop with `npm` (its README); the logger with
   CMake; an MCP server with `uv`.

`qgsdk doctor` shows what's installed and where; `qgsdk profiles` lists the profiles. `qgsdk build
--source <logger checkout>` is a shortcut for the logger's configure-and-build step; you never need it.

## Developer setup (Linux)

Tested on Rocky Linux 9, Debian 12 and Ubuntu 24.04; any x86-64 distribution of that age or newer
should work.

1. Install what your profiles need from your distribution (the one step that needs root). For every
   profile:

   ```sh
   # Fedora / RHEL / Rocky / Alma
   sudo dnf install gcc-c++ mesa-libGL-devel mesa-libEGL-devel libxkbcommon-devel tar dbus-libs fontconfig freetype libbrotli glib2 libwayland-cursor libxkbcommon-x11 xcb-util xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm git gcc make unzip libatomic
   # Debian / Ubuntu
   sudo apt install g++ libgl-dev libegl-dev libxkbcommon-dev curl tar libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0 libwayland-cursor0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-util1 libxcb-xkb1 git build-essential unzip libatomic1
   ```

   The `desktop` profile alone needs a C/C++ compiler, `make`, `git`, `unzip` and libatomic
   (`build-essential git unzip libatomic1` on Debian); the `mcp` profile alone needs only `git`, `curl`
   and `tar`. The installer checks for everything its profiles need and prints the line for you if
   anything is missing.
2. Get QGSDK: clone this repository, or download and unpack it.
3. Install the tools for your profiles (once; the logger is about 2 GB, under a minute on a fast line).
   No root:

   ```sh
   bootstrap/install.sh --profile desktop --profile mcp
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
   bootstrap/install.sh --profile desktop --profile mcp
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
and checks they are the prefix's; for desktop it clones QSO Graph Desktop, checks the Node.js and Rust
it pins are the ones installed, and runs its setup, build and fast check. It ends with `== PASS` or
`== FAIL: <what>`. CI runs them on Windows, Linux (x86-64 and arm64) and both kinds of Mac whenever the
installer changes, and weekly, so a moved download, or a QSO Graph Desktop pin QGSDK doesn't match, is
found within a week.

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
| MinGit, from Git for Windows (Windows) | desktop, mcp | GPL-2.0-only |
| Node.js | desktop | MIT |
| Rust, and rustup | desktop | MIT OR Apache-2.0 |
| Go | desktop | BSD-3-Clause |
| CMake (Kitware's build) | desktop | BSD-3-Clause |
| Ninja (Windows) | desktop | Apache-2.0 |
| NASM (Windows) | desktop | BSD-2-Clause |
| libclang, from LLVM (Windows) | desktop | Apache-2.0 WITH LLVM-exception |

## Learn more

- [docs/](docs/): how QGSDK works, and the decisions behind it (MinGW, aqtinstall, CMake presets, profiles)
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose a change
- Licence: **GPL-3.0-or-later** ([LICENSE](LICENSE), [NOTICE](NOTICE)), like JTSDK and FLSDK
