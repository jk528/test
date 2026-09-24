@echo off
rem ============================================================
rem  Start the vite dev server for the Honglou Reader app.
rem  Working directory is fixed to this script's folder (app/),
rem  so node resolves node_modules/vite correctly.
rem  Run by 启动红楼梦阅读分析.bat  or manually from app/.
rem ============================================================
cd /d "%~dp0"
node node_modules\vite\bin\vite.js
