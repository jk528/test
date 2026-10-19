# unregister_task.ps1 - 卸载新闻联播定时任务
$ErrorActionPreference = "Stop"

$configPath = Join-Path $PSScriptRoot "..\config\config.json"
if (-not (Test-Path $configPath)) { Write-Error "配置文件不存在: $configPath"; exit 1 }
$config = Get-Content $configPath -Encoding utf8 | ConvertFrom-Json
$taskName = $config.schedule.task_name

$existing = schtasks /Query /TN $taskName 2>$null
if (-not $existing) { Write-Host "任务不存在: $taskName"; exit 0 }

schtasks /Delete /TN $taskName /F | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "任务卸载失败"; exit 1 }
Write-Host "已卸载定时任务: $taskName"