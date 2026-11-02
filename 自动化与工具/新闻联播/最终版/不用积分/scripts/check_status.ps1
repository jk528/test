# check_status.ps1 - 查询定时任务状态与目标日期报告是否就位
# 用法: powershell -ExecutionPolicy Bypass -File check_status.ps1 [-TargetDate YYYYMMDD] [-NoPause]
param(
    [string]$TargetDate = "",
    [switch]$NoPause
)

$configPath = Join-Path $PSScriptRoot "..\config\config.json"
if (-not (Test-Path $configPath)) { Write-Error "配置文件不存在: $configPath"; exit 1 }
$config = Get-Content $configPath -Encoding utf8 | ConvertFrom-Json

$taskName = $config.schedule.task_name
$archiveRoot = $config.archive_root

Write-Host "=" * 60
Write-Host "  新闻联播日报 - 状态查询"
Write-Host "=" * 60

# 1. 定时任务状态
Write-Host ""
Write-Host "[1] 定时任务状态"
# schtasks /Query 的输出列名随系统语言变化（英文系统为 TaskName/Status/Next Run Time），
# 旧实现按中文列名过滤，在英文环境会静默输出空行。改用 ScheduledTasks 模块，语言无关
# 且能直接拿到 LastResult（判断任务成败的关键字段）。
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    $action = $task.Actions | Select-Object -First 1
    Write-Host "  任务名: $taskName"
    Write-Host "  状态: $($task.State)"
    Write-Host "  执行: $($action.Execute) $($action.Arguments)"
    Write-Host "  工作目录: $($action.WorkingDirectory)"
    Write-Host "  上次运行: $($info.LastRunTime)"
    Write-Host "  上次结果: $($info.LastTaskResult)"
    Write-Host "  下次运行: $($info.NextRunTime)"
} else {
    Write-Host "  任务未注册: $taskName"
}

# 2. 目标日期报告
Write-Host ""
Write-Host "[2] 报告状态"
if (-not $TargetDate) {
    $TargetDate = (Get-Date).AddDays(-1).ToString("yyyyMMdd")
}
$year = $TargetDate.Substring(0, 4)
$month = $TargetDate.Substring(4, 2)
$monthDir = Join-Path $archiveRoot "${year}年${month}月"
$reportPath = Join-Path $monthDir "新闻联播总结_$TargetDate.md"

if (Test-Path $reportPath) {
    $size = (Get-Item $reportPath).Length / 1KB
    $lines = (Get-Content $reportPath -Encoding utf8 | Measure-Object -Line).Lines
    Write-Host "  日期: $TargetDate"
    Write-Host "  路径: $reportPath"
    Write-Host "  大小: $([math]::Round($size, 1))KB / $lines 行"
    Write-Host "  状态: 已就位"
} else {
    Write-Host "  日期: $TargetDate"
    Write-Host "  状态: 报告未生成"
}

Write-Host ""
Write-Host "=" * 60
if (-not $NoPause) { Read-Host "按回车键退出" }