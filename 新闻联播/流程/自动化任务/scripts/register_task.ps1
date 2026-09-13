<#
.SYNOPSIS
注册 Windows 任务计划程序 - 新闻联播每日总结

.DESCRIPTION
读取配置文件，自动创建Windows任务计划程序定时任务
每天在指定时间自动执行新闻联播总结生成任务

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
    Write-Host "需要管理员权限来注册任务计划程序，正在请求提升..." -ForegroundColor Yellow
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
$TaskScript = Join-Path $ScriptDir "run_daily_task.ps1"

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
Write-Ok "配置文件加载成功"
Write-Host "    任务名称: $($config.task_name)"
Write-Host "    执行时间: $($config.schedule.time)"
Write-Host "    执行模式: $($config.mode)"

# ============================================================
# 检查脚本是否存在
# ============================================================
Write-Step "检查执行脚本"

if (-not (Test-Path $TaskScript)) {
    Write-Err "执行脚本不存在: $TaskScript"
    pause
    exit 1
}
Write-Ok "执行脚本存在: $TaskScript"

# ============================================================
# 检查任务是否已存在
# ============================================================
Write-Step "检查现有任务"

$taskName = $config.task_name
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Warn "检测到同名任务已存在: $taskName"
    $choice = Read-Host "是否覆盖？(y/n)"
    if ($choice -ne 'y' -and $choice -ne 'Y') {
        Write-Host "用户取消，退出"
        pause
        exit 0
    }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Ok "已删除旧任务"
} else {
    Write-Ok "无同名任务"
}

# ============================================================
# 创建任务计划
# ============================================================
Write-Step "创建任务计划程序"

# 解析时间
$runTime = $config.schedule.time
$timeParts = $runTime -split ':'
$hour = [int]$timeParts[0]
$minute = [int]$timeParts[1]

# 创建触发器
$trigger = New-ScheduledTaskTrigger -Daily -At $runTime

# 创建操作
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$TaskScript`"" `
    -WorkingDirectory $ScriptDir

# 创建设置
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount $config.retry.max_retries `
    -RestartInterval (New-TimeSpan -Minutes 5)

# 创建主体（使用当前用户）
$currentUserName = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUserName `
    -LogonType Interactive `
    -RunLevel Limited

# 注册任务
Register-ScheduledTask `
    -TaskName $taskName `
    -Description $config.task_description `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Ok "任务计划创建成功！"

# ============================================================
# 显示任务信息
# ============================================================
Write-Step "任务详情"

$task = Get-ScheduledTask -TaskName $taskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName

Write-Host "    任务名称: $($task.TaskName)"
Write-Host "    任务描述: $($task.Description)"
Write-Host "    执行状态: $($task.State)"
Write-Host "    下次运行: $($taskInfo.NextRunTime)"
Write-Host "    上次运行: $($taskInfo.LastRunTime)"
Write-Host "    上次结果: $($taskInfo.LastTaskResult)"

# ============================================================
# 提示
# ============================================================
Write-Step "提示"

Write-Host "  任务已注册到 Windows 任务计划程序。"
Write-Host "  每天 $runTime 将自动执行新闻联播总结生成任务。"
Write-Host ""
Write-Host "  常用操作："
Write-Host "    查看任务: 开始菜单 -> 任务计划程序 -> 任务计划程序库"
Write-Host "    手动运行: 右键任务 -> 运行"
Write-Host "    查看日志: logs\ 文件夹"
Write-Host "    修改配置: config\config.json"
Write-Host "    卸载任务: 运行 unregister_task.ps1"
Write-Host ""

pause
