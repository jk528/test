@echo off
rem ============================================================
rem  ColorTxt Analysis launcher helper - start dev server
rem  Called by 启动彩读分析.vbs in a minimized window.
rem  Runs `npm run dev` in the ColorTxt project so the VBS
rem  can poll the vite port (5173) and the electron process.
rem ============================================================
setlocal
set "LOG=%~dp0.temp\colortxt_dev.log"
set "APP=%~dp0.temp\ColorTxt"
if not exist "%APP%\node_modules" (
  echo [colortxt] ERROR: node_modules not found. Run `npm install` first.
  goto done
)
cd /d "%APP%"
echo [colortxt] starting electron-vite dev... > "%LOG%" 2>&1
npm run dev >> "%LOG%" 2>&1
:done
