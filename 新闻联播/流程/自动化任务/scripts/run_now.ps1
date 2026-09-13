<#
.SYNOPSIS
手动运行一次新闻联播总结任务

.DESCRIPTION
立即执行一次新闻联播总结生成任务，用于测试或手动触发

.NOTES
版本: v1.0.0
日期: 2026-09-13
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskScript = Join-Path $ScriptDir "run_daily_task.ps1"

Write-Host "正在手动执行新闻联播每日总结任务..." -ForegroundColor Cyan
Write-Host ""

& powershell -ExecutionPolicy Bypass -NoProfile -File $TaskScript

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "任务执行完成！" -ForegroundColor Green
} else {
    Write-Host "任务执行失败，退出码: $LASTEXITCODE" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
