@echo off & chcp 65001 >nul
setlocal

:: ============================================
:: CodeArts daily check-in entry (shareable template).
::
:: Auto-detects the Node.js runtime; no hardcoded paths.
:: Log redirection is done by the scheduled task (logs\checkin.log),
:: so a manual run prints to console.
::
:: Requires Node.js 22.13+ (built-in node:sqlite is used to decrypt
:: the local credential store).
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

:: 3) Fall back to the CodeArts Agent EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    Install location is auto-detected from the registry.
set "CA_INSTALL="
for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "CodeArts" /d 2^>nul ^| findstr /i "InstallLocation"') do set "CA_INSTALL=%%b"
if not defined CA_INSTALL for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "CodeArts" /d 2^>nul ^| findstr /i "InstallLocation"') do set "CA_INSTALL=%%b"
set "CA_EXE="
if defined CA_INSTALL if exist "%CA_INSTALL%codearts-agent.exe" set "CA_EXE=%CA_INSTALL%codearts-agent.exe"
if not defined CA_EXE if exist "C:\Program Files\CodeArts Agent\codearts-agent.exe" set "CA_EXE=C:\Program Files\CodeArts Agent\codearts-agent.exe"

if defined CA_EXE goto :cae

echo ERROR: No Node.js runtime found. Install Node.js 22.13+ (24+ recommended) or the CodeArts Agent client.
exit /b 1

:run
"%NODE_EXE%" "%SCRIPT_DIR%codearts_checkin.js" %*
exit /b %ERRORLEVEL%

:cae
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%CA_EXE%" "%SCRIPT_DIR%codearts_checkin.js" %*
exit /b %ERRORLEVEL%
