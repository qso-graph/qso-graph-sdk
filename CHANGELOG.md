# Changelog

All notable changes to QSO Graph SDK (QGSDK) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-28

### Security

- **QGSDK's own Python is 3.14.10** (was 3.13.16), for the eMudhra CA advisory: 3.13.16 and the pip it
  carries still trust intermediate CAs with trivially weak keys. 3.13.18 is the fixed 3.13, but
  QGSDK takes its Windows Python from python.org (the NuGet package), and python.org publishes no
  Windows build of 3.13.18: 3.13 is in its source-only phase. 3.14.10 is on python.org for Windows
  and on python-build-standalone for the rest, bundles pip 26.2.2, and is supported longer. Every download is checked against the SHA-256 its publisher lists. The locked tooling
  list drops `backports-zstd`, needed only before 3.14.
- **CI asks for exact patch releases** (3.11.18, 3.12.16, 3.13.18, 3.14.10) instead of "3.13", which
  accepts whatever the runner already has. `tests/test_pythons.py` fails a minor version or a patch
  older than the advisory's, in the workflows and in `manifest.json`.

### Changed

- **uv 0.13.6** in the `mcp` profile, the version the lab uses, so a server is built with the same uv
  everywhere. Each download is checked against the SHA-256 uv publishes for it. (#21)

## [0.1.0] - 2026-10-26

The first release.

### Added

- **Choose what you work on, and get exactly its tools.** Three profiles: `desktop` (QSO Graph
  Desktop: Node.js, Rust, and Go and CMake for its FIPS crypto module), `logger` (QSO Graph Logger: Qt
  and its compiler, CMake, Ninja, NSIS) and `mcp` (qso-graph's MCP servers: uv, Python 3.11 to 3.13,
  git). The installer asks when none is given; running it again with another adds it. (#4, #11, #12)
- **Windows, Linux and macOS for every profile**, Apple silicon and Intel; Linux arm64 (a Raspberry
  Pi 5) for desktop and mcp. (#13)
- **What must come from the system is checked first and named**, with the one command that installs
  it: Microsoft's C++ Build Tools on Windows (desktop), the distribution's packages on Linux, Apple's
  Xcode command-line tools on macOS. Nothing outside the prefix is touched.
- **Every profile is proven on every platform** by `tests/check.sh` and `tests/windows-check.ps1`, run
  by CI whenever the installer changes and weekly; the desktop check builds QSO Graph Desktop itself.
- **Releases** (this one is the first): versioned archives, SHA256SUMS, and GitHub's signed record that
  this repository's Release workflow made them. (#15)

### Security

- The tooling QGSDK installs for itself was locked to certifi, brotli and setuptools versions with
  published advisories (one critical); all three are upgraded, and CI now audits that lock. (#8, #9)
