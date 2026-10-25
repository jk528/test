@echo off
setlocal

:: ============================================
:: Daily check-in entry.
::
:: Runs checkin_all.js with an optional group filter (2026-10-25 refactor):
::   --group=ai     00:05 daily: Trae/TeleAgent/WorkBuddy/CodeArts/OfficeAce/KukuAI
::   --group=daily  10:35 daily: Qoder(resets 10:00)/BaiduPan/TianYi cloud
::   (no group arg runs all 9 platforms; TraeWork/TraeCN merged 2026-10-16)
::
:: Auto-detects the Node.js runtime; no hardcoded paths.
:: Log redirection is done by the scheduled task (checkin_ai.log /
:: checkin_daily.log per group), so a manual run prints to console.
::
:: Qoder's daily campaign resets at 10:00 and cannot be claimed before
:: that, so it stays in the daily group. OfficeAce additionally
:: needs its desktop client running.
::
:: IMPORTANT: keep this file pure ASCII - cmd.exe re-reads the
::   batch file after "chcp 65001", and non-ASCII bytes shift
::   its read offset, making it execute comment fragments.
:: ============================================

:: Force UTF-8 codepage so cmd's own messages and Node output share
:: one encoding - prevents mixed-encoding log files.
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"

:: ---- log rotation ----
:: Scheduled tasks redirect output to a per-group log. Rotate when > 5 MB
:: (keep one .old generation, same strategy as sync_gitee.ps1). Pure ASCII.
set "LOG_FILE=%SCRIPT_DIR%checkin_all.log"
if "%~1"=="--group=ai" set "LOG_FILE=%SCRIPT_DIR%checkin_ai.log"
if "%~1"=="--group=daily" set "LOG_FILE=%SCRIPT_DIR%checkin_daily.log"
:: Read the size OUTSIDE any ( ) block: %LOG_SIZE% is expanded when the
:: block is parsed, which would leave "if GTR 5242880 (" and abort cmd.
set "LOG_SIZE=0"
if exist "%LOG_FILE%" for %%A in ("%LOG_FILE%") do set "LOG_SIZE=%%~zA"
if %LOG_SIZE% GTR 5242880 (
    move /y "%LOG_FILE%" "%LOG_FILE%.old" >nul 2>&1
    if exist "%LOG_FILE%.old.old" del /q "%LOG_FILE%.old.old" >nul 2>&1
)
:: ----------------------

set "SCRIPT=checkin_all.js"
set "NODE_EXE="

:: 1) Node from PATH (most robust for scheduled tasks too).
where node >nul 2>nul
if %ERRORLEVEL%==0 set "NODE_EXE=node"

:: 2) Common Node.js install locations.
if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"

:: 3) TeleAgent bundled Node (some setups rely on it).
if not defined NODE_EXE if exist "%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe" set "NODE_EXE=%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe"

:: "goto :run" instead of an if-block: %ERRORLEVEL% is expanded at parse
:: time inside parentheses, which would return a stale exit code.
if defined NODE_EXE goto :run

:: 4) Fall back to the Trae CN EXE as Node runtime (ELECTRON_RUN_AS_NODE=1).
::    Install location is auto-detected from the registry; never hardcoded.
set "TRAE_INSTALL="
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Trae" /d 2^>nul ^| findstr /i "InstallLocation"') do set "TRAE_INSTALL=%%b"
set "TRAE_EXE="
if defined TRAE_INSTALL if exist "%TRAE_INSTALL%Trae CN.exe" set "TRAE_EXE=%TRAE_INSTALL%Trae CN.exe"
if not defined TRAE_EXE if defined TRAE_INSTALL if exist "%TRAE_INSTALL%TRAE SOLO CN.exe" set "TRAE_EXE=%TRAE_INSTALL%TRAE SOLO CN.exe"
if not defined TRAE_EXE if exist "%LOCALAPPDATA%\Programs\Trae CN\Trae CN.exe" set "TRAE_EXE=%LOCALAPPDATA%\Programs\Trae CN\Trae CN.exe"
if not defined TRAE_EXE if exist "%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe" set "TRAE_EXE=%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe"

if defined TRAE_EXE goto :trae

echo ERROR: No Node.js runtime found. Install Node.js (18+) or the Trae CN client.
exit /b 1

:: Args are passed straight through to the script, so
:: "run_checkin.cmd --no-delay" skips the random delay for testing.
:run
"%NODE_EXE%" "%SCRIPT_DIR%%SCRIPT%" %*
exit /b %ERRORLEVEL%

:trae
set ELECTRON_RUN_AS_NODE=1
set VSCODE_DEV=
"%TRAE_EXE%" "%SCRIPT_DIR%%SCRIPT%" %*
exit /b %ERRORLEVEL%
