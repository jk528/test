@echo off
setlocal
rem ============================================================
rem  红楼梦阅读分析一体化 — 启动器
rem  功能：
rem    1. 复用已运行的 vite dev server（端口 1420）
rem    2. 否则在最小化窗口中启动 vite
rem    3. 等待端口就绪（最多 30 秒）
rem    4. 启动 Tauri 调试窗口，阻塞直到退出
rem    5. 清理 vite（仅当本脚本启动了它）
rem  增强：
rem    - 前置检查：node.exe / app.exe 是否存在
rem    - 错误时暂停，方便查看报错
rem    - 启动日志写入 .temp/launcher.log
rem ============================================================

set "APP_DIR=%~dp0app"
set "TEMP_DIR=%~dp0app\.temp"
set "LOG_FILE=%TEMP_DIR%\launcher.log"
set "VITE_PORT=1420"
set "STARTED_VITE="

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo [%date% %time%] ================================================== >> "%LOG_FILE%"
echo [%date% %time%] 启动红楼梦阅读分析一体化 >> "%LOG_FILE%"
echo [%date% %time%] APP_DIR=%APP_DIR% >> "%LOG_FILE%"
echo [%date% %time%] CWD=%cd% >> "%LOG_FILE%"

rem ---- 前置检查 1: node.exe ----
where node >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 node.exe，请先安装 Node.js 并加入 PATH。
    echo [错误] 找不到 node.exe，请先安装 Node.js 并加入 PATH。 >> "%LOG_FILE%"
    pause
    goto done
)

rem ---- 前置检查 2: app.exe 是否已编译 ----
if not exist "%APP_DIR%\src-tauri\target\debug\app.exe" (
    echo [错误] app.exe 不存在，请先构建一次：
    echo        cd /d "%APP_DIR%"
    echo        pnpm tauri dev
    echo [错误] app.exe 不存在 >> "%LOG_FILE%"
    pause
    goto done
)

rem ---- 1) 复用已运行的 dev server ----
netstat -ano | findstr ":1420" >nul 2>&1
if not errorlevel 1 (
    echo [信息] 检测到 vite 已在端口 1420 运行，直接启动应用...
    echo [%date% %time%] 复用已有 vite server >> "%LOG_FILE%"
    goto vite_up
)

rem ---- 2) 启动 vite dev server（最小化窗口） ----
echo [信息] 启动 vite dev server...
echo [%date% %time%] 启动 vite >> "%LOG_FILE%"
start "honglou-vite" /min "%APP_DIR%\start_vite.bat"
set "STARTED_VITE=1"

rem ---- 3) 等待端口就绪（最多 30 秒） ----
set /a tries=0
:waitloop
set /a tries+=1
if %tries% gtr 30 (
    echo [警告] vite 尚未就绪（30秒超时），继续尝试启动应用...
    echo [%date% %time%] vite 超时 >> "%LOG_FILE%"
    goto vite_up
)
netstat -ano | findstr ":1420" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)
echo [信息] vite 已就绪（端口 1420），耗时 %tries% 秒
echo [%date% %time%] vite 就绪，耗时 %tries% 秒 >> "%LOG_FILE%"

:vite_up
rem ---- 4) 启动应用（阻塞直到退出） ----
echo [信息] 启动红楼梦阅读分析...
echo [%date% %time%] 启动 app.exe >> "%LOG_FILE%"
start "" /wait "%APP_DIR%\src-tauri\target\debug\app.exe"
set "EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] 应用退出，退出码=%EXIT_CODE% >> "%LOG_FILE%"

rem ---- 5) 清理 vite（仅当本脚本启动了它） ----
if defined STARTED_VITE (
    echo [信息] 清理 vite 进程...
    taskkill /FI "WINDOWTITLE eq honglou-vite*" /T /F >nul 2>&1
    echo [%date% %time%] 已清理 vite >> "%LOG_FILE%"
)

:done
echo [%date% %time%] 启动器退出 >> "%LOG_FILE%"
endlocal
