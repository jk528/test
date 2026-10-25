@echo off & chcp 65001 >nul
setlocal

:: ============================================
:: OfficeAce (GuoBan) daily check-in entry (shareable template).
::
:: Auto-detects the Node.js runtime; no hardcoded paths.
:: Log redirection is done by the scheduled task (logs\checkin.log),
:: so a manual run prints to console.
::
:: NOTE: the OfficeAce client must be RUNNING at check-in time
::   (the check-in goes through its local API on 127.0.0.1).
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

:: 3) Fall back to the OfficeAce EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    Install location is auto-detected from the registry.
set "OA_INSTALL="
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "OfficeAce" /d 2^>nul ^| findstr /i "InstallLocation"') do set "OA_INSTALL=%%b"
set "OA_EXE="
if defined OA_INSTALL if exist "%OA_INSTALL%OfficeAce.exe" set "OA_EXE=%OA_INSTALL%OfficeAce.exe"
if not defined OA_EXE if exist "%USERPROFILE%\OfficeAce\OfficeAce.exe" set "OA_EXE=%USERPROFILE%\OfficeAce\OfficeAce.exe"
if not defined OA_EXE if exist "%LOCALAPPDATA%\Programs\OfficeAce\OfficeAce.exe" set "OA_EXE=%LOCALAPPDATA%\Programs\OfficeAce\OfficeAce.exe"

if defined OA_EXE goto :oae

echo ERROR: No Node.js runtime found. Install Node.js 18+ or the OfficeAce client.
exit /b 1

:run
"%NODE_EXE%" "%SCRIPT_DIR%officeace_checkin.js" %*
exit /b %ERRORLEVEL%

:oae
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%OA_EXE%" "%SCRIPT_DIR%officeace_checkin.js" %*
exit /b %ERRORLEVEL%
