# Contributing to QGSDK

Thank you for helping. QGSDK exists so that building QSO Graph's software never depends on one person,
so the most useful contributions make it simpler, clearer, or work on one more machine.

**The short version, and the hard rules:** [AGENTS.md](AGENTS.md). Written for AI coding agents, and the quickest
start for anyone.

## How a change gets in

1. Open an issue describing the problem or idea, unless it's a small fix.
2. Make a branch named for the change: `fix-...`, `feat-...` or `docs-...`.
3. Open a pull request. CI runs the Python tests and, when the installer, the manifest or the checks
   change, the platform checks on Windows, Linux and macOS (`tests\windows-check.ps1`,
   `tests/check.sh`; see [Checking it works](README.md#checking-it-works)).
4. Another maintainer reviews it. Nobody merges their own pull request.

## Ground rules

- **Pin, don't float.** Every version lives in `manifest.json`. A change of version is a change to that
  file, with a reason in the pull request.
- **Nothing outside the prefix.** QGSDK never writes into the system, never needs admin rights, and
  never needs an account.
- **The wrappers stay optional.** The logger must build with plain CMake once the environment is loaded. The
  Windows check proves it (the "deletion test").
- **Record decisions.** A choice someone might later question (a tool, a version policy) gets a short
  record in `docs/decisions/`: what was decided, and why.
- **Write for the next maintainer.** Plain language; say why, not only what.

## Running the tests

With [uv](https://docs.astral.sh/uv/):

```sh
uv sync --group dev
uv run ruff check .
uv run mypy src
uv run pytest
```

## Licence

QGSDK is **GPL-3.0-or-later** ([LICENSE](LICENSE)). By contributing, you agree your contribution is
licensed the same way, and you keep the copyright in what you wrote. New files start with the licence
header in that file's comment style:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) <year> the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
```

Add yourself to [AUTHORS](AUTHORS) with your first contribution.
