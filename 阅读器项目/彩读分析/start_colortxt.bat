@echo off
rem ============================================================
rem  ColorTxt Analysis launcher helper - start dev server
rem  Called by 启动彩读分析.vbs in a minimized window.
rem ============================================================
setlocal
set "LOG=%~dp0.temp\colortxt_dev.log"
set "APP=%~dp0.temp\ColorTxt"
if not exist "%APP%\node_modules" (
  echo [colortxt] ERROR: node_modules not found. Run `npm install` first. > "%LOG%"
  goto done
)
cd /d "%APP%"
echo [colortxt] === %date% %time% === > "%LOG%" 2>&1
echo [colortxt] node: >> "%LOG%" 2>&1
call node --version >> "%LOG%" 2>&1
echo [colortxt] npm: >> "%LOG%" 2>&1
call npm --version >> "%LOG%" 2>&1
echo [colortxt] starting electron-vite dev... >> "%LOG%" 2>&1
call npm run dev >> "%LOG%" 2>&1
:done
