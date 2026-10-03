<#
.SYNOPSIS
  QGSDK's check: from nothing, it gives this Windows machine a working Qt build and packaging toolchain.

.DESCRIPTION
  Run it on a clean Windows 10/11 machine or VM (nothing installed beforehand, no admin rights needed):

  1. installs QGSDK (bootstrap\install.ps1): Python, the tooling, Qt, MinGW, CMake, Ninja, NSIS;
  2. builds the small Qt test program in tests\fixture with `qgsdk build`, and runs it;
  3. builds it again with plain CMake, without QGSDK's wrapper (the deletion test: the wrapper must stay
     optional, so a developer can use CMake directly or their IDE);
  4. checks NSIS (makensis), which CPack uses to make an installer, runs.

  QGLogger itself is built and packaged from the QGLogger checkout: see QGLogger's README.

  Prints "== PASS" and exits 0 when everything works; otherwise prints "== FAIL: <what>" and exits 1.
  Programs are started with --smoke (they quit once their window is up) on Qt's offscreen platform, so
  this also works over SSH, with no desktop.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tests\windows-check.ps1
#>
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
param(
    [string]$Prefix = (Join-Path (Split-Path -Parent $PSScriptRoot) "prefix")
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Fixture = Join-Path $Repo "tests\fixture"

# Runs a program and shows its output. cmd merges stderr into stdout, so Windows PowerShell 5.1 doesn't
# treat a compiler's warnings as errors, and the output passes through PowerShell, so a transcript
# (Start-Transcript) records it.
function Run([string]$line) {
    cmd /c "$line 2>&1" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE`: $line" }
}

# Starts a built program with --smoke and checks it exits 0.
function Smoke([string]$exe) {
    $env:QT_QPA_PLATFORM = "offscreen"
    $p = Start-Process -FilePath $exe -ArgumentList "--smoke" -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { throw "$exe exited with $($p.ExitCode)" }
    Write-Host "$exe started and exited cleanly"
}

try {
    Write-Host "== 1. Install QGSDK"
    Run "powershell -NoProfile -ExecutionPolicy Bypass -File `"$Repo\bootstrap\install.ps1`" -Prefix `"$Prefix`""
    $Prefix = (Resolve-Path $Prefix).Path
    $Qgsdk = Join-Path $Prefix "venv\Scripts\qgsdk.exe"

    Write-Host "== 2. Build the fixture with qgsdk build, and run it"
    Run "`"$Qgsdk`" --prefix `"$Prefix`" build release --source `"$Fixture`""
    . (Join-Path $Prefix "qgsdk-env.ps1")  # Qt's DLLs on PATH, for running what was built
    Smoke (Join-Path $Fixture "build\release\qgsdk-fixture.exe")

    Write-Host "== 3. The deletion test: the same program with plain CMake, no QGSDK wrapper"
    Push-Location $Fixture
    try {
        Run "cmake --preset debug"
        Run "cmake --build --preset debug"
    } finally { Pop-Location }
    Smoke (Join-Path $Fixture "build\debug\qgsdk-fixture.exe")

    Write-Host "== 4. NSIS, for installers"
    Run "makensis /VERSION"

    Write-Host "== PASS: QGSDK installed; the fixture built with and without its wrapper, and ran; NSIS runs"
    exit 0
} catch {
    Write-Host "== FAIL: $_"
    exit 1
}
