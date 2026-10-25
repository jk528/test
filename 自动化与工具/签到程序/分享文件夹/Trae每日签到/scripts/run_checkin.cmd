@echo off & chcp 65001 >nul
setlocal

:: ============================================
:: Trae daily check-in entry (shareable template).
::
:: Auto-detects the Node.js runtime; no hardcoded paths.
:: Log redirection is done by the scheduled task (logs\checkin.log),
:: so a manual run prints to console.
::
:: IMPORTANT: keep this file pure ASCII, and keep "chcp 65001" on
::   line 1 - switching the codepage mid-file risks cmd re-reading
::   the batch from a shifted offset (ghost parse errors).
:: ============================================

set "SCRIPT_DIR=%~dp0"
set "NODE_EXE="

:: 1) Node from PATH.
where node >nul 2>nul
if %ERRORLEVEL%==0 set "NODE_EXE=node"

:: 2) Common Node.js install location.
if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"

if defined NODE_EXE goto :run

:: 3) Fall back to the Trae CN EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    Install location is auto-detected from the registry.
set "TRAE_INSTALL="
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Trae" /d 2^>nul ^| findstr /i "InstallLocation"') do set "TRAE_INSTALL=%%b"
set "TRAE_EXE="
if defined TRAE_INSTALL if exist "%TRAE_INSTALL%Trae CN.exe" set "TRAE_EXE=%TRAE_INSTALL%Trae CN.exe"
if not defined TRAE_EXE if exist "%LOCALAPPDATA%\Programs\Trae CN\Trae CN.exe" set "TRAE_EXE=%LOCALAPPDATA%\Programs\Trae CN\Trae CN.exe"

if defined TRAE_EXE goto :trae

echo ERROR: No Node.js runtime found. Install Node.js 18+ or the Trae CN client.
exit /b 1

:run
"%NODE_EXE%" "%SCRIPT_DIR%trae_checkin.js" %*
exit /b %ERRORLEVEL%

:trae
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%TRAE_EXE%" "%SCRIPT_DIR%trae_checkin.js" %*
exit /b %ERRORLEVEL%
