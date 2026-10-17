# ============================================================
#  创建桌面快捷方式 — 红楼梦阅读分析一体化
#  用法：右键 → 使用 PowerShell 运行，或在 PowerShell 中执行：
#        .\创建桌面快捷方式.ps1
#  效果：在桌面生成 "红楼梦阅读分析.lnk"
#        指向 VBS 启动器（无黑色命令行窗口），
#        起始位置设为项目根目录，确保 sidecar/资源路径正确解析。
# ============================================================

$ErrorActionPreference = "Stop"

# 项目根目录 = 脚本所在目录
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LauncherPath = Join-Path $ProjectRoot "启动红楼梦阅读分析.vbs"
$IconPath = Join-Path $ProjectRoot "app\src-tauri\icons\icon.ico"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "红楼梦阅读分析.lnk"

# 检查启动器是否存在
if (-not (Test-Path $LauncherPath)) {
    Write-Host "[错误] 找不到启动器: $LauncherPath" -ForegroundColor Red
    Write-Host "请确保脚本放在项目根目录下。" -ForegroundColor Yellow
    pause
    exit 1
}

# 创建快捷方式
Write-Host "[创建] 桌面快捷方式: $ShortcutPath" -ForegroundColor Cyan
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LauncherPath
$Shortcut.WorkingDirectory = $ProjectRoot   # 关键：设置起始位置为项目根
$Shortcut.Description = "红楼梦阅读分析一体化 — Tauri 桌面应用"

# 设置图标（如果存在）
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}

$Shortcut.Save()

Write-Host ""
Write-Host "[完成] 桌面快捷方式已创建 ✅" -ForegroundColor Green
Write-Host "  目标: $LauncherPath"
Write-Host "  起始位置: $ProjectRoot"
Write-Host ""
Write-Host "双击桌面上的 ""红楼梦阅读分析"" 即可启动。" -ForegroundColor Yellow
Write-Host "（首次启动需要几秒启动 vite dev server，请稍候）" -ForegroundColor Gray
Write-Host ""
pause
