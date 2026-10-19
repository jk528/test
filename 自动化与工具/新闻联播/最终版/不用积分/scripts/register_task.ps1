# register_task.ps1 - 注册每日定时新闻联播日报生成任务（含补全）
# 用法: powershell -ExecutionPolicy Bypass -File register_task.ps1
$ErrorActionPreference = "Stop"

$configPath = Join-Path $PSScriptRoot "..\config\config.json"
if (-not (Test-Path $configPath)) { Write-Error "配置文件不存在: $configPath"; exit 1 }
$config = Get-Content $configPath -Encoding utf8 | ConvertFrom-Json

$taskName = $config.schedule.task_name
$triggerTime = $config.schedule.trigger_time
$pythonExe = $config.python_exe
$scriptDir = $config.script_dir
$completeScript = Join-Path $scriptDir $config.auto_complete_script
$waitSec = $config.schedule.complete_wait_seconds
$maxRetry = $config.schedule.complete_max_retry

if (-not (Test-Path $pythonExe)) { Write-Error "Python解释器不存在: $pythonExe"; exit 1 }
if (-not (Test-Path $completeScript)) { Write-Error "补全脚本不存在: $completeScript"; exit 1 }

$cmdAction = "$pythonExe `"$completeScript`" --wait $waitSec --max-retry $maxRetry"
$workDir = $scriptDir

$existing = schtasks /Query /TN $taskName 2>$null
if ($existing) {
    Write-Host "任务已存在，先卸载旧任务..."
    schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /TR $cmdAction /SC DAILY /ST $triggerTime /F | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "任务注册失败"; exit 1 }

Write-Host "已注册定时任务: $taskName"
Write-Host "  触发时间: 每日 $triggerTime"
Write-Host "  执行命令: $cmdAction"
Write-Host "  工作目录: $workDir"
Write-Host "  补全策略: 首次不全则等待${waitSec}秒后重跑，最多${maxRetry}次"
Write-Host ""
Write-Host "提示: 修改执行时间后需重新运行本脚本注册任务。"