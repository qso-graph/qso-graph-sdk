# Working on QSO Graph SDK

Instructions for anyone, human or AI agent, changing this repository. The hard rules first, then how to
build and check. When a rule here and your task disagree, stop and ask.

## What this is

**QSO Graph SDK (QGSDK): the build kit for QSO Graph's applications.** One command installs the tools it
takes to compile and package them, at pinned versions, on a clean machine. It is tooling only: an
application is compiled and packaged from its own repository.

**It installs by profile**, so a developer gets the tools for what they work on: `desktop` (QSO Graph
Desktop: Node.js, Rust, Go, CMake), `logger` (QSO Graph Logger, the Qt application: a grid-heavy native
program, so Qt is its framework) and `mcp` (the MCP servers: uv and their Pythons). Windows, Linux and
macOS for every profile; Linux arm64 for desktop and mcp.

## Rules (each one has a test you can apply)

- **Every version is pinned in `manifest.json`, and nowhere else.** A version change is a change to that
  file, with the reason in the pull request. *Test: is any version or URL written anywhere but there?*
- **Every download is checked before it is used** (SHA-256 in the manifest; the tooling's Python
  packages come from the hash-locked `bootstrap/tooling-requirements.txt`). *Test: could a changed
  file be installed without failing?*
- **Nothing outside the prefix, no admin rights, no accounts.** Everything goes under one folder;
  removing QGSDK is deleting it. On Linux and macOS, what must come from the system (packages, Apple's
  Xcode command-line tools) is checked and named, never installed.
- **A profile installs only what its work needs**, on every platform it lists. *Test: does
  `tests/check.sh --profile <one>` pass on a machine with only that profile's system requirements?*
- **Zero prerequisites on Windows**, but one: `bootstrap\install.ps1` needs nothing installed first (no
  Python, git, Visual Studio or Qt account) except, for the desktop profile, Microsoft's C++ Build
  Tools, which Rust on Windows links with and only Microsoft's installer (as an administrator) can
  install: checked and named, never installed or redistributed. **The logger uses MinGW, never MSVC.**
- **Desktop's pins are Desktop's.** The `desktop` profile's Node.js and Rust are the versions QSO Graph
  Desktop's `.node-version` and `rust-toolchain.toml` name. *Test: `tests/check.sh --profile desktop`
  fails when they differ.*
- **The wrappers stay optional.** With the environment loaded, plain CMake builds the logger. *Test:
  `tests/windows-check.ps1` and `tests/check.sh` build the fixture both ways.*
- **Nothing ships that we cannot build from source,** and every downloaded tool is named in the README
  with its licence.
- **House rules:** every new file starts with the SPDX header (`GPL-3.0-or-later`, see
  `CONTRIBUTING.md`); changes go in by pull request; branches are `feat-…`, `fix-…` or `docs-…`;
  match the code around you, and do not rename or reformat what your task doesn't need.

## Build and check

```sh
bootstrap/install.sh --profile logger    # Linux and macOS; Windows: powershell -File bootstrap\install.ps1 -Profiles logger
uv sync --group dev && uv run pytest      # the Python tests; also uv run ruff check . and uv run mypy src
tests/check.sh                            # the full check, on a clean machine or container
```

- **What CI checks:** ruff, mypy, the Python tests on 3.11 to 3.13, an audit of the locked
  dependencies, and, when the installer, the manifest or the checks change (and weekly), the full check
  with every profile on Windows, Linux, Apple-silicon and Intel Macs. **It does not check** a truly
  fresh machine: GitHub's runners carry tools of their own, so a release is also checked on a clean VM
  (`docs/m0.md`).

## Where the real documents are

- **How it works and why:** [`docs/`](docs/), and the decisions in [`docs/decisions/`](docs/decisions/).
- **Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md). **Using it:** [`README.md`](README.md).
