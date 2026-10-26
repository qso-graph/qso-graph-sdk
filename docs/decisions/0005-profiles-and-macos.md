# 0005: Profiles, and macOS

**Decided (KI7MT, 2026-10-26):** QGSDK installs by **profile**, one per kind of work, and every profile
supports Windows, Linux and macOS. The first two:

- **`logger`**: QSO Graph Logger. Qt and its tools, as QGSDK installed them from the start. The logger is
  a grid-heavy application (SOTA, POTA, DX, nets): dense tables, keyboard speed, a lot on screen at once.
  That is what Qt is good at and Electron is not, so the logger stays Qt, and so does this profile.
- **`mcp`**: qso-graph's MCP servers. uv, and the Pythons their CI tests against (3.11 to 3.13), installed
  by uv into the prefix; git where the system has none (MinGit on Windows).

- **`desktop`**: QSO Graph Desktop. Node.js and Rust at the versions Desktop pins (`.node-version`,
  `rust-toolchain.toml`), and Go and CMake for AWS-LC's FIPS module, which the credential core links. On
  Windows the FIPS build also needs Ninja, NASM, Perl (Strawberry's portable build: GitHub's runners carry it preinstalled, which hid the need until a clean Windows built it) and bindgen, which loads libclang: QGSDK unpacks just
  libclang and clang's headers from LLVM's release. And there Rust links with Microsoft's C++ Build
  Tools, which need an administrator: the one prerequisite QGSDK checks for on Windows rather than
  installs (Microsoft's installer, never a copy of ours). On Linux arm64 (a Raspberry Pi 5) too.

  Its check builds Desktop itself: clone, `npm ci`, build (which compiles the credential core) and its
  fast check. It also fails if Desktop's pins and QGSDK's differ, so the two cannot drift for longer
  than a week.

**Why profiles:** one person works on the logger, another on an MCP server, a third on both. Installing
Qt (about 2 GB) for someone who works only on MCP servers is waste, and a kit that installs everything
for everyone grows with every application. A profile installs only what its work needs; running the
installer again with another adds it. The choice is remembered in the prefix (`qgsdk-profiles.json`), so
`qgsdk env` and `qgsdk doctor` know what's there.

**Why macOS now:** much of the work on QSO Graph is done on Macs. A build kit that leaves them out isn't
one.

- **Qt's own macOS build** (`clang_64`, universal: Apple silicon and Intel), with CMake and Ninja from
  Qt's tools, as on the other platforms.
- **The compiler is Apple's clang**, from the Xcode command-line tools. Installing them needs an
  administrator, which QGSDK never asks for, so the installer checks for them (`xcode-select -p`) and,
  if they're missing, names the one command (`xcode-select --install`) and stops. They bring git too.
- **QGSDK's own Python** is python-build-standalone, as on Linux, pinned per machine (`macos-arm64`,
  `macos-x86_64`).

**How it's checked:** `tests/check.sh` (Linux and macOS) and `tests/windows-check.ps1` install the chosen
profiles from nothing and prove each: the logger builds and runs a small Qt program with and without
QGSDK's wrapper; for mcp, each Python runs through uv, and uv, its Pythons and git are the prefix's own.
CI runs them on Windows, Linux, and Apple-silicon and Intel Macs whenever the installer changes, and
weekly, so a download that moves or changes is found within a week.
