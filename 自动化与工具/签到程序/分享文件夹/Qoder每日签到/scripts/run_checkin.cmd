@echo off & chcp 65001 >nul
setlocal

:: ============================================
:: Qoder daily check-in entry (shareable template).
::
:: Auto-detects the Node.js runtime; no hardcoded paths.
:: Log redirection is done by the scheduled task (logs\checkin.log),
:: so a manual run prints to console.
::
:: IMPORTANT: keep this file pure ASCII, and keep "chcp 65001" on
::   line 1 - switching the codepage mid-file risks cmd re-reading
::   the batch from a shifted offset (ghost parse errors).
::
:: NOTE: the Qoder campaign refreshes at 10:00 (UTC+8) daily.
::   Schedule the task at 10:30 or later (default 10:40).
:: ============================================

set "SCRIPT_DIR=%~dp0"
set "NODE_EXE="

:: 1) Node from PATH.
where node >nul 2>nul
if %ERRORLEVEL%==0 set "NODE_EXE=node"

:: 2) Common Node.js install location.
if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"

if defined NODE_EXE goto :run

:: 3) Fall back to the Qoder client EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    Install location is auto-detected from the registry, then common paths.
set "QODER_INSTALL="
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Qoder" /d 2^>nul ^| findstr /i "InstallLocation"') do set "QODER_INSTALL=%%b"
set "QODER_EXE="
if defined QODER_INSTALL if exist "%QODER_INSTALL%Qoder CN.exe" set "QODER_EXE=%QODER_INSTALL%Qoder CN.exe"
if not defined QODER_EXE if exist "%LOCALAPPDATA%\Programs\Qoder CN\Qoder CN.exe" set "QODER_EXE=%LOCALAPPDATA%\Programs\Qoder CN\Qoder CN.exe"
if not defined QODER_EXE if exist "%LOCALAPPDATA%\Programs\Qoder\Qoder.exe" set "QODER_EXE=%LOCALAPPDATA%\Programs\Qoder\Qoder.exe"

if defined QODER_EXE goto :qoder

echo ERROR: No Node.js runtime found. Install Node.js 18+ or the Qoder client.
exit /b 1

:run
"%NODE_EXE%" "%SCRIPT_DIR%qoder_checkin.js" %*
exit /b %ERRORLEVEL%

:qoder
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%QODER_EXE%" "%SCRIPT_DIR%qoder_checkin.js" %*
exit /b %ERRORLEVEL%
