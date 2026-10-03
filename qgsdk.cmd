@echo off
@rem SPDX-License-Identifier: GPL-3.0-or-later
@rem Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
rem QGSDK's command, from a checkout installed with bootstrap\install.ps1 (default prefix).
if not exist "%~dp0prefix\venv\Scripts\qgsdk.exe" (
  echo QGSDK isn't installed yet: run  powershell -ExecutionPolicy Bypass -File "%~dp0bootstrap\install.ps1"
  exit /b 1
)
"%~dp0prefix\venv\Scripts\qgsdk.exe" %*
