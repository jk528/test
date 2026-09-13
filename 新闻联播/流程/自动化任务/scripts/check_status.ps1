<#
.SYNOPSIS
查看任务计划程序状态和最近日志

.DESCRIPTION
显示任务计划程序的运行状态、下次运行时间、最近执行结果
以及查看最近的日志文件

.NOTES
版本: v1.0.0
日期: 2026-09-13
#>

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
# 最近日志
# ============================================================
Write-Step "最近日志"

if (Test-Path $LogDir) {
    $logFiles = Get-ChildItem $LogDir -Filter "task_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
    
    if ($logFiles) {
        Write-Host "  最近的日志文件:"
        foreach ($f in $logFiles) {
            $sizeKB = [math]::Round($f.Length / 1KB, 1)
            Write-Host "    - $($f.Name) ($sizeKB KB, $($f.LastWriteTime))"
        }
        
        # 显示今天的日志最后几行
        $todayLog = Join-Path $LogDir "task_$(Get-Date -Format 'yyyyMMdd').log"
        if (Test-Path $todayLog) {
            Write-Host ""
            Write-Host "  今日日志最后 20 行:"
            Write-Host "  --------------------"
            $lines = Get-Content $todayLog -Tail 20 -Encoding UTF8
            foreach ($line in $lines) {
                Write-Host "  $line"
            }
        }
    } else {
        Write-Warn "暂无日志文件"
    }
} else {
    Write-Warn "日志目录不存在"
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
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
