@echo off
setlocal

:: ============================================
:: Smoke test for batch re-read behavior (pure ASCII + chcp 65001)
:: Long comment line to test offset stability: this line contains enough text to
:: make byte offsets meaningful, including symbols like (parentheses) and / slashes,
:: plus the word TraeWork and TeleAgent and WorkBuddy just like the real script
:: ============================================

chcp 65001 >nul

set "NODE_EXE=%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe"

"%NODE_EXE%" -e "console.log(new Date().toLocaleString('zh-CN',{hour12:false})+' [SMOKE] UTF-8 Chinese: Unified check-in smoke test, punctuation 200 points')"

endlocal
