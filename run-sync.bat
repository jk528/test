@echo off
chcp 65001 >nul
echo [INFO] 启动PC端同步任务...
echo [INFO] 时间: %date% %time%

powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\这是什么\JK-temp\auto-sync-pc.ps1"

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] 同步任务执行完成
) else (
    echo [ERROR] 同步任务执行失败，错误码: %ERRORLEVEL%
)

pause
