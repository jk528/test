<#
.SYNOPSIS
卸载 Windows 任务计划程序 - 新闻联播每日总结

.DESCRIPTION
从Windows任务计划程序中移除新闻联播每日总结任务

.NOTES
版本: v1.0.0
日期: 2026-09-13
使用方法: 右键 -> 使用PowerShell运行
#>

# 提升权限
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "需要管理员权限来卸载任务计划程序，正在请求提升..." -ForegroundColor Yellow
    Start-Process powershell -Verb runAs -ArgumentList "-ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    exit
}

$ErrorActionPreference = "Stop"

# ============================================================
# 路径配置
# ============================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ConfigPath = Join-Path $ProjectRoot "config\config.json"

# ============================================================
# 辅助函数
# ============================================================
function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok { param([string]$Msg) Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Err { param([string]$Msg) Write-Host "  [ERR] $Msg" -ForegroundColor Red }

# ============================================================
# 读取配置
# ============================================================
Write-Step "读取配置文件"

if (-not (Test-Path $ConfigPath)) {
    Write-Err "配置文件不存在: $ConfigPath"
    pause
    exit 1
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskName = $config.task_name
Write-Ok "任务名称: $taskName"

# ============================================================
# 检查任务是否存在
# ============================================================
Write-Step "检查任务状态"

$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if (-not $existingTask) {
    Write-Warn "任务不存在: $taskName"
    Write-Host "  无需卸载。"
    pause
    exit 0
}

Write-Ok "找到任务: $taskName"
Write-Host "    当前状态: $($existingTask.State)"

# ============================================================
# 确认卸载
# ============================================================
Write-Step "确认卸载"

$choice = Read-Host "确定要卸载任务 '$taskName' 吗？(y/n)"
if ($choice -ne 'y' -and $choice -ne 'Y') {
    Write-Host "用户取消，退出"
    pause
    exit 0
}

# ============================================================
# 卸载任务
# ============================================================
Write-Step "卸载任务"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Ok "任务已成功卸载"

# ============================================================
# 验证
# ============================================================
Write-Step "验证结果"

$verifyTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $verifyTask) {
    Write-Ok "确认任务已被移除"
} else {
    Write-Err "任务仍然存在，卸载可能失败"
}

Write-Host ""
Write-Host "  提示: 日志文件和生成的报告不会被删除。"
Write-Host "  如需重新注册，请运行 register_task.ps1"
Write-Host ""

pause
