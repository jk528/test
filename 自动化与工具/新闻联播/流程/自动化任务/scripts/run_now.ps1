<#
.SYNOPSIS
手动运行一次新闻联播总结任务（与计划任务动作完全一致）

.DESCRIPTION
按 config.json 解析出解释器与报告脚本，在前台执行一次；
执行的命令行与「新闻联播每日总结」计划任务的动作 1 完全相同，
因此这里的验证结果即 05:00 自动运行的结果。

.PARAMETER TargetDate
    指定目标日期 YYYYMMDD。缺省不带该参数 = 生成昨天（与计划任务一致）。

.PARAMETER WithSync
    生成后再执行一次归档同步（计划任务默认不含此动作）。

.PARAMETER NoPause
    结束时不停留等待按键（供自动化调用）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\run_now.ps1
    powershell -ExecutionPolicy Bypass -File .\run_now.ps1 -TargetDate 20260915
    powershell -ExecutionPolicy Bypass -File .\run_now.ps1 -NoPause

.NOTES
版本: v2.0.0
日期: 2026-09-16
变更: 改为直接执行 xwlb_report.py（与计划任务动作一致），
      不再经 run_daily_task.ps1 外壳；新增 -TargetDate / -WithSync / -NoPause
#>

param(
    [string]$TargetDate = "",
    [switch]$WithSync,
    [switch]$NoPause
)

$ErrorActionPreference = "Continue"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ConfigPath  = Join-Path $ProjectRoot "config\config.json"

if (-not (Test-Path $ConfigPath)) {
    Write-Host "配置文件不存在: $ConfigPath" -ForegroundColor Red
    if (-not $NoPause) { $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") }
    exit 1
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

$OneShotDir   = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $config.paths.oneshot_dir))
$ReportScript = Join-Path $OneShotDir $config.paths.oneshot_script

if (-not (Test-Path $ReportScript)) {
    Write-Host "报告脚本不存在: $ReportScript" -ForegroundColor Red
    if (-not $NoPause) { $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") }
    exit 1
}

# ---- 解析解释器（必须能 import requests），与 register_task.ps1 同逻辑 ----
$candidates = @()
if ($config.paths.python_exe)       { $candidates += $config.paths.python_exe }
if ($config.paths.python_fallbacks) { $candidates += $config.paths.python_fallbacks }

$PythonExe = $null
foreach ($c in $candidates) {
    if ([string]::IsNullOrWhiteSpace($c)) { continue }
    $exe = $c
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $exe = $cmd.Source }
    if (-not (Test-Path $exe)) { continue }
    $probe = & $exe -c "import sys,requests" 2>$null
    if ($LASTEXITCODE -eq 0) { $PythonExe = $exe; break }
}

if (-not $PythonExe) {
    Write-Host "未找到可用 Python 解释器（需可导入 requests）" -ForegroundColor Red
    if (-not $NoPause) { $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") }
    exit 1
}

# ---- 组装命令行（与计划任务动作 1 相同，区别仅在本脚本可传日期） ----
$argList = @()
if ($TargetDate) { $argList += $TargetDate }
$shown = if ($TargetDate) { $TargetDate } else { "（缺省 = 昨天）" }

Write-Host "正在手动执行新闻联播每日总结任务..." -ForegroundColor Cyan
Write-Host "    解释器 : $PythonExe"
Write-Host "    脚本   : $ReportScript"
Write-Host "    目标日期: $shown"
Write-Host ""

Push-Location $OneShotDir
try {
    & $PythonExe $ReportScript @argList
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

Write-Host ""
switch ($code) {
    0 { Write-Host "任务执行完成（自检全部通过）。" -ForegroundColor Green }
    1 { Write-Host "任务失败：致命错误（日期非法 / 抓取失败）。" -ForegroundColor Red }
    2 { Write-Host "报告已生成，但自检发现 CRITICAL 问题，请查看上方清单。" -ForegroundColor Red }
    default { Write-Host "任务结束，退出码: $code" -ForegroundColor Yellow }
}

# ---- 可选：同步归档 ----
if ($WithSync) {
    $syncScript = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $config.sync.sync_script))
    if (Test-Path $syncScript) {
        Write-Host ""
        Write-Host "正在同步归档..." -ForegroundColor Cyan
        & powershell.exe -ExecutionPolicy Bypass -NoProfile -File $syncScript
    } else {
        Write-Host "同步脚本不存在: $syncScript" -ForegroundColor Yellow
    }
}

Write-Host ""
if (-not $NoPause) {
    Write-Host "按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
exit $code
