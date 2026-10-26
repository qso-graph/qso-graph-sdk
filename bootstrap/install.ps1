# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
<#
.SYNOPSIS
  QGSDK for Windows: one command to the tools for the QSO Graph software you work on.

.DESCRIPTION
  Choose profiles with -Profiles (several: -Profiles logger,mcp); with none, it asks. `logger` is Qt
  and its tools for QSO Graph Logger; `mcp` is uv, the Pythons the MCP servers test against, and git;
  `desktop` is Node.js, Rust, Go, CMake, Ninja, NASM and libclang for QSO Graph Desktop.
  Running it again with another profile adds it.

  Needs nothing installed first: no Python, no git, no Visual Studio, no Qt account, no admin rights.
  The one exception is the desktop profile: Rust on Windows links with Microsoft's C++ Build Tools,
  which only Microsoft's installer can install, with an administrator. It checks, and names the command.
  Everything goes under one folder (the prefix, default .\prefix beside this checkout); removing QGSDK
  is deleting that folder.

  1. QGSDK's own Python (the official python.org build, pinned and checked by SHA-256)
  2. aqtinstall and QGSDK's tooling into a virtual environment
  3. the profiles: logger is Qt, the matched MinGW compiler, CMake, Ninja, and NSIS for installers;
     mcp is uv, its Pythons and MinGit (all versions from manifest.json)

  Safe to run again: it skips what's already there.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File bootstrap\install.ps1 -Profiles logger,mcp
#>
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
param(
    [string]$Prefix = (Join-Path (Split-Path -Parent $PSScriptRoot) "prefix"),
    [string[]]$Profiles = @()  # not -Profile: $PROFILE is PowerShell's own
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # the progress bar makes Invoke-WebRequest very slow

$Repo = Split-Path -Parent $PSScriptRoot
$Manifest = Get-Content (Join-Path $Repo "manifest.json") -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
$Prefix = (Resolve-Path $Prefix).Path
$Downloads = Join-Path $Prefix "downloads"
New-Item -ItemType Directory -Force -Path $Downloads | Out-Null

# --- 1. QGSDK's own Python -------------------------------------------------------------------------
$Python = Join-Path $Prefix "python\python.exe"
if (-not (Test-Path $Python)) {
    $py = $Manifest.python
    $zip = Join-Path $Downloads "python-$($py.version).zip"
    Write-Host "QGSDK: downloading Python $($py.version)"
    Invoke-WebRequest -Uri $py.windows.url -OutFile $zip
    $hash = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLower()
    if ($hash -ne $py.windows.sha256) {
        Remove-Item $zip
        throw "Python download doesn't match manifest.json (got $hash). Nothing was installed."
    }
    $unpacked = Join-Path $Downloads "python-unpacked"
    if (Test-Path $unpacked) { Remove-Item -Recurse -Force $unpacked }
    Expand-Archive -Path $zip -DestinationPath $unpacked
    Move-Item (Join-Path $unpacked "tools") (Join-Path $Prefix "python")
    Remove-Item -Recurse -Force $unpacked
}

# --- 2. aqtinstall and QGSDK's tooling, in a virtual environment ---------------------------------
$Venv = Join-Path $Prefix "venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "QGSDK: creating the tooling environment"
    & $Python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed" }
}
# Every dependency comes from the hash-locked list; nothing else is fetched (bootstrap\tooling-requirements.txt).
$Pip = @("-m", "pip", "install", "--disable-pip-version-check", "--quiet")
& $VenvPython @Pip --require-hashes -r (Join-Path $Repo "bootstrap\tooling-requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "installing the locked tooling dependencies failed" }
# aqtinstall itself: pinned by commit (decision 0002), built with the locked build tools above.
$env:SETUPTOOLS_SCM_PRETEND_VERSION = $Manifest.aqtinstall.version  # a source zip carries no git version
& $VenvPython @Pip --no-deps --no-build-isolation $Manifest.aqtinstall.requirement
if ($LASTEXITCODE -ne 0) { throw "installing aqtinstall failed" }
Remove-Item Env:SETUPTOOLS_SCM_PRETEND_VERSION
& $VenvPython @Pip --no-deps --no-build-isolation --editable $Repo
if ($LASTEXITCODE -ne 0) { throw "installing QGSDK's tooling failed" }

# --- 3. The profiles: chosen (asked, if none are), each one's system check, then installed ---------
$Qgsdk = Join-Path $Venv "Scripts\qgsdk.exe"
# `powershell -File ... -Profiles logger,mcp` passes "logger,mcp" as one string: split it.
$Profiles = @($Profiles | ForEach-Object { $_ -split "," } | Where-Object { $_ })
$ProfileArgs = @($Profiles | ForEach-Object { "--profile"; $_ })
$Chosen = (& $Qgsdk --prefix $Prefix select @ProfileArgs) -split " "
if ($LASTEXITCODE -ne 0) { throw "choosing the profiles failed" }
Write-Host "QGSDK: profiles $($Chosen -join ' ')"

# desktop: Rust links with Microsoft's C++ Build Tools (the MSVC compiler and a Windows SDK). Everything
# else on Windows comes from the manifest. vswhere ships with every Visual Studio installer.
if ($Chosen -contains "desktop") {
    $Vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    $Msvc = if (Test-Path $Vswhere) {
        & $Vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    }
    if (-not $Msvc) {
        Write-Host "The desktop profile needs Microsoft's C++ Build Tools, which need an administrator to install." -ForegroundColor Yellow
        Write-Host "Install them with Microsoft's own installer (in a terminal run as administrator):"
        Write-Host '  winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"'
        Write-Host "then run this again. Nothing more was installed."
        exit 1
    }
}

& $Qgsdk --prefix $Prefix install
if ($LASTEXITCODE -ne 0) { throw "qgsdk install failed" }
& $Qgsdk --prefix $Prefix env --shell powershell | Set-Content -Encoding utf8 (Join-Path $Prefix "qgsdk-env.ps1")
& $Qgsdk --prefix $Prefix env --shell cmd | Set-Content -Encoding ascii (Join-Path $Prefix "qgsdk-env.cmd")
& $Qgsdk --prefix $Prefix doctor

Write-Host ""
Write-Host ""
Write-Host "QGSDK is ready. Load its environment in each new shell:"
Write-Host "  . $Prefix\qgsdk-env.ps1"
if ($Chosen -contains "logger") {
    Write-Host "Then, in the logger's checkout: cmake --preset release; cmake --build --preset release; cpack --preset release"
}
if ($Chosen -contains "mcp") {
    Write-Host "Then, in an MCP server's checkout: uv sync --group dev; uv run pytest"
}
if ($Chosen -contains "desktop") {
    Write-Host "Then, in QSO Graph Desktop's checkout: npm ci, then its README's build steps"
}
