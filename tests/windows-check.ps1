# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
<#
.SYNOPSIS
  QGSDK's check on Windows: from nothing, each profile gives this machine what it promises.

.DESCRIPTION
  Run it on a clean Windows 10/11 machine or VM (nothing installed beforehand, no admin rights needed):

  1. installs QGSDK with the profiles (bootstrap\install.ps1); default: every profile;
  logger:
  2. builds the small Qt test program in tests\fixture with `qgsdk build`, and runs it;
  3. builds it again with plain CMake, without QGSDK's wrapper (the deletion test: the wrapper must stay
     optional, so a developer can use CMake directly or their IDE);
  4. checks NSIS (makensis), which CPack uses to make an installer, runs;
  mcp:
  5. runs each Python the MCP servers test against, through uv, and git; uv's Pythons are in the prefix.

  Prints "== PASS" and exits 0 when everything works; otherwise prints "== FAIL: <what>" and exits 1.
  Programs are started with --smoke (they quit once their window is up) on Qt's offscreen platform, so
  this also works over SSH, with no desktop.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tests\windows-check.ps1 -Profiles logger,mcp
#>
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
param(
    [string]$Prefix = (Join-Path (Split-Path -Parent $PSScriptRoot) "prefix"),
    [string[]]$Profiles = @("logger", "mcp")
)
$Profiles = @($Profiles | ForEach-Object { $_ -split "," } | Where-Object { $_ })

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
    Write-Host "== 1. Install QGSDK: $($Profiles -join ' ')"
    Run "powershell -NoProfile -ExecutionPolicy Bypass -File `"$Repo\bootstrap\install.ps1`" -Prefix `"$Prefix`" -Profiles $($Profiles -join ',')"
    $Prefix = (Resolve-Path $Prefix).Path
    $Qgsdk = Join-Path $Prefix "venv\Scripts\qgsdk.exe"
    . (Join-Path $Prefix "qgsdk-env.ps1")  # the tools on PATH (and Qt's DLLs, for running what was built)

    if ($Profiles -contains "logger") {
        Write-Host "== 2. Build the fixture with qgsdk build, and run it"
        Run "`"$Qgsdk`" --prefix `"$Prefix`" build release --source `"$Fixture`""
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
    }

    if ($Profiles -contains "mcp") {
        Write-Host "== 5. uv, the MCP servers' Pythons, and git"
        $Uv = (Get-Command uv).Source
        if (-not $Uv.StartsWith($Prefix)) { throw "uv is not the prefix's: $Uv" }
        foreach ($v in "3.11", "3.12", "3.13") {
            $Found = (& uv python find --managed-python $v)
            if ($LASTEXITCODE -ne 0) { throw "uv has no Python $v" }
            if (-not $Found.StartsWith($Prefix)) { throw "Python $v is not the prefix's: $Found" }
            Run "`"$Found`" -c `"import sys, ssl; print(sys.version.split()[0], ssl.OPENSSL_VERSION)`""
        }
        $Git = (Get-Command git).Source
        if (-not $Git.StartsWith($Prefix)) { throw "git is not the prefix's: $Git" }
        Run "git --version"
    }

    Write-Host "== PASS: QGSDK installed $($Profiles -join ' '), and each did what it promises"
    exit 0
} catch {
    Write-Host "== FAIL: $_"
    exit 1
}
