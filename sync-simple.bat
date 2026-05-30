@echo off
chcp 65001 >nul
cd /d "c:\Users\Administrator\Documents\这是什么\JK-temp"

echo [%date% %time%] 开始同步检查...

REM 检查是否有变更
git status --porcelain > temp_status.txt
set /p STATUS=<temp_status.txt
del temp_status.txt

if "%STATUS%"=="" (
    echo [%date% %time%] 无变更，跳过同步
    goto :end
)

echo [%date% %time%] 检测到文件变更，开始同步...

REM 添加所有变更
git add .
if errorlevel 1 (
    echo [%date% %time%] git add 失败
    goto :error
)

REM 提交变更
git commit -m "定时同步: %date% %time%"
if errorlevel 1 (
    echo [%date% %time%] git commit 失败
    goto :error
)

REM 推送到 Gitee
echo [%date% %time%] 推送到 Gitee...
git push gitee-test main:main
if errorlevel 1 (
    echo [%date% %time%] 推送到 Gitee 失败
) else (
    echo [%date% %time%] 推送到 Gitee 成功
)

REM 推送到 GitHub
echo [%date% %time%] 推送到 GitHub...
git push github main:main
if errorlevel 1 (
    echo [%date% %time%] 推送到 GitHub 失败
) else (
    echo [%date% %time%] 推送到 GitHub 成功
)

echo [%date% %time%] 同步任务完成
goto :end

:error
echo [%date% %time%] 同步过程中发生错误

:end
