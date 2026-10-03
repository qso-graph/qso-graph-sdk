# Working on QSO Graph SDK

Instructions for anyone, human or AI agent, changing this repository. The hard rules first, then how to
build and check. When a rule here and your task disagree, stop and ask.

## What this is

**QSO Graph SDK (QGSDK): the build kit for [QSO Graph Logger](https://github.com/qso-graph/qso-graph-logger).**
One command installs the tools it takes to compile and package the logger, at pinned versions, on a
clean machine. It is tooling only: the logger is compiled and packaged from its own repository.

## Rules (each one has a test you can apply)

- **Every version is pinned in `manifest.json`, and nowhere else.** A version change is a change to that
  file, with the reason in the pull request. *Test: is any version or URL written anywhere but there?*
- **Every download is checked before it is used** (SHA-256 in the manifest; the tooling's Python
  packages come from the hash-locked `bootstrap/tooling-requirements.txt`). *Test: could a changed
  file be installed without failing?*
- **Nothing outside the prefix, no admin rights, no accounts.** Everything goes under one folder;
  removing QGSDK is deleting it. On Linux, system packages are checked and named, never installed.
- **Zero prerequisites on Windows.** `bootstrap\install.ps1` needs nothing installed first: no Python,
  git, Visual Studio or Qt account. **MinGW, never MSVC.**
- **The wrappers stay optional.** With the environment loaded, plain CMake builds the logger. *Test:
  `tests/windows-check.ps1` and `tests/linux-check.sh` build the fixture both ways.*
- **Nothing ships that we cannot build from source,** and every downloaded tool is named in the README
  with its licence.
- **House rules:** every new file starts with the SPDX header (`GPL-3.0-or-later`, see
  `CONTRIBUTING.md`); changes go in by pull request; branches are `feat-…`, `fix-…` or `docs-…`;
  match the code around you, and do not rename or reformat what your task doesn't need.

## Build and check

```sh
bootstrap/install.sh                      # Linux; Windows: powershell -File bootstrap\install.ps1
uv run --extra test pytest                # the Python tests (or: python -m pytest)
tests/linux-check.sh                      # the full check, on a clean machine or container
```

- **What CI checks:** the Python tests only. **It does not check** a clean-machine install on Windows or
  Linux; maintainers run `tests/windows-check.ps1` and `tests/linux-check.sh` on fresh machines. A pull
  request that changes the installer, the manifest or the bootstrap says where it ran them.

## Where the real documents are

- **How it works and why:** [`docs/`](docs/), and the decisions in [`docs/decisions/`](docs/decisions/).
- **Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md). **Using it:** [`README.md`](README.md).
