<#
.SYNOPSIS
查看任务计划程序状态和最近日志

.DESCRIPTION
显示任务计划程序的运行状态、下次运行时间、最近执行结果
以及查看最近的日志文件

.NOTES
版本: v1.1.0
日期: 2026-09-16
变更: 新增「目标报告检查」（以报告文件判定执行结果）；
      任务日志改为历史追溯（新版任务直接运行 xwlb_report.py，不再写 logs\task_*.log）；
      新增 -NoPause，便于无人值守/管道调用
#>

param(
    [switch]$NoPause
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ConfigPath = Join-Path $ProjectRoot "config\config.json"
$LogDir = Join-Path $ProjectRoot "logs"

function Write-Step { param([string]$Msg) Write-Host "`n== $Msg ==" -ForegroundColor Cyan }
function Write-Ok { param([string]$Msg) Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Err { param([string]$Msg) Write-Host "  [ERR] $Msg" -ForegroundColor Red }

# ============================================================
# 读取配置
# ============================================================
if (Test-Path $ConfigPath) {
    $config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskName = $config.task_name
} else {
    $taskName = "新闻联播每日总结"
}

# ============================================================
# 任务计划状态
# ============================================================
Write-Step "任务计划状态"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
    
    Write-Host "    任务名称: $($task.TaskName)"
    Write-Host "    任务状态: $($task.State)"
    
    $stateColor = if ($task.State -eq "Ready") { "Green" } else { "Yellow" }
    Write-Host "    启用状态: " -NoNewline
    Write-Host $task.Settings.Enabled -ForegroundColor $stateColor
    
    Write-Host "    下次运行: $($taskInfo.NextRunTime)"
    Write-Host "    上次运行: $($taskInfo.LastRunTime)"
    
    $resultColor = if ($taskInfo.LastTaskResult -eq 0) { "Green" } else { "Red" }
    Write-Host "    上次结果: " -NoNewline
    Write-Host "0x$($taskInfo.LastTaskResult.ToString('X8'))" -ForegroundColor $resultColor
    
    # 显示触发器
    Write-Host "    触发器:"
    foreach ($trigger in $task.Triggers) {
        Write-Host "      - 每日 $($trigger.StartBoundary.Substring(11, 5))"
    }
} else {
    Write-Warn "任务未注册（请运行 register_task.ps1 注册）"
}

# ============================================================
# 本次应生成的报告是否已就位
# 说明：计划任务现在直接运行 xwlb_report.py，不再写 logs\task_*.log，
#       因此以「目标日期的报告文件是否存在」作为执行结果的第一判据。
# ============================================================
Write-Step "目标报告检查"

$archiveRoot = Join-Path $ProjectRoot "..\..\归档"
$archiveRoot = [System.IO.Path]::GetFullPath($archiveRoot)

$yesterday = (Get-Date).AddDays(-1)
$expectName = "新闻联播总结_" + $yesterday.ToString("yyyyMMdd") + ".md"

if (Test-Path $archiveRoot) {
    $hit = Get-ChildItem $archiveRoot -Recurse -Filter $expectName -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) {
        $kb = [math]::Round($hit.Length / 1KB, 1)
        Write-Ok "已就位: $expectName（${kb}KB，$($hit.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))）"
    } else {
        Write-Warn "未找到 $expectName（对应 $($yesterday.ToString('yyyy-MM-dd')) 的报告尚未生成）"
    }
} else {
    Write-Warn "归档目录不存在: $archiveRoot"
}

# ============================================================
# 历史任务日志（旧版 run_daily_task.ps1 留下的记录，仅供追溯）
# ============================================================
$LogDir = Join-Path $ProjectRoot "logs"
if (Test-Path $LogDir) {
    $logFiles = Get-ChildItem $LogDir -Filter "task_*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 3
    if ($logFiles) {
        Write-Step "历史任务日志"
        foreach ($f in $logFiles) {
            $sizeKB = [math]::Round($f.Length / 1KB, 1)
            Write-Host "    - $($f.Name) ($sizeKB KB, $($f.LastWriteTime))"
        }
    }
}

# ============================================================
# 最近生成的报告
# ============================================================
Write-Step "最近生成的报告"

$archiveDir = Join-Path $ProjectRoot "..\..\归档"

if (Test-Path $archiveDir) {
    $recentFiles = Get-ChildItem $archiveDir -Recurse -Filter "新闻联播总结_*.md" | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -First 5
    
    if ($recentFiles) {
        foreach ($f in $recentFiles) {
            $sizeKB = [math]::Round($f.Length / 1KB, 1)
            Write-Host "    - $($f.Name) ($sizeKB KB, $($f.LastWriteTime.ToString('yyyy-MM-dd HH:mm')))"
        }
    } else {
        Write-Warn "暂无报告文件"
    }
} else {
    Write-Warn "归档目录不存在: $archiveDir"
}

Write-Host ""
if (-not $NoPause) {
    Write-Host "按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
