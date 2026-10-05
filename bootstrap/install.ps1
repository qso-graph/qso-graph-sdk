# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
<#
.SYNOPSIS
  QGSDK for Windows: one command to a working Qt build environment for QGLogger.

.DESCRIPTION
  Needs nothing installed first: no Python, no git, no Visual Studio, no Qt account, no admin rights.
  Everything goes under one folder (the prefix, default .\prefix beside this checkout); removing QGSDK
  is deleting that folder.

  1. QGSDK's own Python (the official python.org build, pinned and checked by SHA-256)
  2. aqtinstall and QGSDK's tooling into a virtual environment
  3. Qt, the matched MinGW compiler, CMake, Ninja, and NSIS for installers (all versions from manifest.json)

  Safe to run again: it skips what's already there.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File bootstrap\install.ps1
#>
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
param(
    [string]$Prefix = (Join-Path (Split-Path -Parent $PSScriptRoot) "prefix")
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

# --- 3. Qt and the build tools ---------------------------------------------------------------------
$Qgsdk = Join-Path $Venv "Scripts\qgsdk.exe"
& $Qgsdk --prefix $Prefix install
if ($LASTEXITCODE -ne 0) { throw "qgsdk install failed" }
& $Qgsdk --prefix $Prefix env --shell powershell | Set-Content -Encoding utf8 (Join-Path $Prefix "qgsdk-env.ps1")
& $Qgsdk --prefix $Prefix env --shell cmd | Set-Content -Encoding ascii (Join-Path $Prefix "qgsdk-env.cmd")
& $Qgsdk --prefix $Prefix doctor

Write-Host ""
Write-Host "QGSDK is ready. In your QGLogger checkout, load its environment, then build and package with CMake:"
Write-Host "  . $Prefix\qgsdk-env.ps1"
Write-Host "  cmake --preset release; cmake --build --preset release; cpack --preset release"
