@echo off & chcp 65001 >nul
setlocal

:: ============================================
:: KukuAI daily check-in entry (shareable template).
::
:: Auto-detects the Node.js runtime; no hardcoded paths.
:: Log redirection is done by the scheduled task (logs\checkin.log),
:: so a manual run prints to console.
::
:: IMPORTANT: keep this file pure ASCII, and keep "chcp 65001" on
::   line 1 - switching the codepage mid-file risks cmd re-reading
::   the batch from a shifted offset (ghost parse errors).
::
:: NOTE: credentials come from config\kuku_config.json (BDUSS etc.),
::   NOT from the local KukuAI client - see README for how to fill it.
:: ============================================

set "SCRIPT_DIR=%~dp0"
set "NODE_EXE="

:: 1) Node from PATH.
where node >nul 2>nul
if %ERRORLEVEL%==0 set "NODE_EXE=node"

:: 2) Common Node.js install location.
if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"

if defined NODE_EXE goto :run

:: 3) Fall back to the KukuAI client EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    The client is an Electron app (GenFlowPro); install+data dir is unified.
set "KUKU_EXE="
if exist "%APPDATA%\baidu\KukuAI\GenFlowPro.exe" set "KUKU_EXE=%APPDATA%\baidu\KukuAI\GenFlowPro.exe"

if defined KUKU_EXE goto :kuku

echo ERROR: No Node.js runtime found. Install Node.js 18+ (or the KukuAI client).
exit /b 1

:run
"%NODE_EXE%" "%SCRIPT_DIR%kuku_checkin.js" %*
exit /b %ERRORLEVEL%

:kuku
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%KUKU_EXE%" "%SCRIPT_DIR%kuku_checkin.js" %*
exit /b %ERRORLEVEL%
