@echo off
setlocal
rem ============================================================
rem  Honglou Reader launcher - 红楼梦阅读分析一体化
rem  Keeps a single source of truth for launching the app:
rem    1. reuses a running vite dev server on port 1420 if present
rem    2. otherwise starts one in a minimized window
rem    3. waits until port 1420 is listening (up to ~30s)
rem    4. launches the Tauri debug window and blocks until it exits
rem    5. kills the dev server only if this script started it
rem  Requires: node on PATH, app built once via "pnpm tauri dev".
rem ============================================================

set "APP_DIR=%~dp0app"
set "VITE_PORT=1420"
set "STARTED_VITE="

rem ---- 1) reuse existing dev server if already listening ----
netstat -ano | findstr ":1420" >nul 2>&1
if not errorlevel 1 goto vite_up

rem ---- 2) start vite dev server in a minimized window ----
echo [honglou] starting vite dev server...
start "honglou-vite" /min "%APP_DIR%\start_vite.bat"
set "STARTED_VITE=1"

rem ---- 3) wait until port 1420 is listening (max ~30s) ----
set /a tries=0
:waitloop
set /a tries+=1
if %tries% gtr 30 (
  echo [honglou] WARN: vite not listening yet, continuing anyway...
  goto vite_up
)
netstat -ano | findstr ":1420" >nul 2>&1
if errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto waitloop
)
:vite_up
echo [honglou] vite is ready on port 1420

rem ---- 4) launch the app window (block until the app exits) ----
if not exist "%APP_DIR%\src-tauri\target\debug\app.exe" (
  echo [honglou] ERROR: app.exe not found.
  echo [honglou] Build once with: cd app ^&^& pnpm tauri dev
  goto done
)
echo [honglou] launching app...
start "" /wait "%APP_DIR%\src-tauri\target\debug\app.exe"

rem ---- 5) cleanup the dev server only if we started it ----
if defined STARTED_VITE taskkill /FI "WINDOWTITLE eq honglou-vite*" /T /F >nul 2>&1

:done
endlocal
