@echo off & chcp 65001 >nul
setlocal

:: ============================================
:: TeleAgent daily check-in entry (shareable template).
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

:: 3) Node runtime bundled with the TeleAgent client (preferred over the EXE fallback).
if not defined NODE_EXE if exist "%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe" set "NODE_EXE=%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe"

if defined NODE_EXE goto :run

:: 4) Fall back to the TeleAgent EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    Install location is auto-detected from the registry.
set "TA_INSTALL="
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "TeleAgent" /d 2^>nul ^| findstr /i "InstallLocation"') do set "TA_INSTALL=%%b"
set "TA_EXE="
if defined TA_INSTALL if exist "%TA_INSTALL%TeleAgent.exe" set "TA_EXE=%TA_INSTALL%TeleAgent.exe"
if not defined TA_EXE if exist "%LOCALAPPDATA%\Programs\TeleAgent\TeleAgent.exe" set "TA_EXE=%LOCALAPPDATA%\Programs\TeleAgent\TeleAgent.exe"
if not defined TA_EXE if exist "C:\Program Files\TeleAgent\TeleAgent.exe" set "TA_EXE=C:\Program Files\TeleAgent\TeleAgent.exe"

if defined TA_EXE goto :teleagent

echo ERROR: No Node.js runtime found. Install Node.js 18+ or the TeleAgent client.
exit /b 1

:run
"%NODE_EXE%" "%SCRIPT_DIR%teleagent_checkin.js" %*
exit /b %ERRORLEVEL%

:teleagent
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%TA_EXE%" "%SCRIPT_DIR%teleagent_checkin.js" %*
exit /b %ERRORLEVEL%
