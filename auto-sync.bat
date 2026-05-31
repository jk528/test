@echo off
chcp 65001 >nul
echo ========== Git Sync Task ==========
echo [%date% %time%] Entering working directory...
cd /d "c:\Users\Administrator\Documents\JK-temp"
if errorlevel 1 (
    echo [%date% %time%] [ERROR] Cannot enter working directory
    exit /b 1
)

if not exist ".git" (
    echo [%date% %time%] [ERROR] Current directory is not a git repository
    exit /b 1
)

echo [%date% %time%] Checking local changes...
git status --porcelain > temp_status.txt
set /p STATUS=<temp_status.txt
del temp_status.txt

if "%STATUS%"=="" (
    echo [%date% %time%] [INFO] No changes, skip sync
    echo [%date% %time%] ========== Sync Task End ==========
    exit /b 0
)

echo [%date% %time%] Changes detected, start syncing...

echo [%date% %time%] Executing git add .
git add .
if errorlevel 1 (
    echo [%date% %time%] [ERROR] git add failed
    exit /b 1
)
echo [%date% %time%] git add success

set COMMIT_MSG=Auto sync: %date% %time%
echo [%date% %time%] Executing git commit -m "%COMMIT_MSG%"
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo [%date% %time%] [INFO] No changes to commit, skip sync
    exit /b 0
)
echo [%date% %time%] git commit success

echo [%date% %time%] Pushing to Gitee...
git push gitee-test main:main
if errorlevel 1 (
    echo [%date% %time%] [WARN] Gitee push failed, retry in 5 seconds...
    timeout /t 5 /nobreak >nul
    git push gitee-test main:main
    if errorlevel 1 (
        echo [%date% %time%] [WARN] Gitee push failed again, retry in 5 seconds...
        timeout /t 5 /nobreak >nul
        git push gitee-test main:main
        if errorlevel 1 (
            echo [%date% %time%] [ERROR] Gitee push finally failed
        ) else (
            echo [%date% %time%] Gitee push success
        )
    ) else (
        echo [%date% %time%] Gitee push success
    )
) else (
    echo [%date% %time%] Gitee push success
)

echo [%date% %time%] Pushing to GitHub...
git push github main:main
if errorlevel 1 (
    echo [%date% %time%] [WARN] GitHub push failed, retry in 5 seconds...
    timeout /t 5 /nobreak >nul
    git push github main:main
    if errorlevel 1 (
        echo [%date% %time%] [WARN] GitHub push failed again, retry in 5 seconds...
        timeout /t 5 /nobreak >nul
        git push github main:main
        if errorlevel 1 (
            echo [%date% %time%] [ERROR] GitHub push finally failed
        ) else (
            echo [%date% %time%] GitHub push success
        )
    ) else (
        echo [%date% %time%] GitHub push success
    )
) else (
    echo [%date% %time%] GitHub push success
)

echo [%date% %time%] ========== Sync Task End ==========
