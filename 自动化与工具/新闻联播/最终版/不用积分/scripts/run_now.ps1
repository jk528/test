# run_now.ps1 - 手动运行新闻联播日报生成
# 用法: powershell -ExecutionPolicy Bypass -File run_now.ps1 [-TargetDate YYYYMMDD] [-Force]
param(
    [string]$TargetDate = "",
    [switch]$Force,
    [string]$Mode = "oneshot"
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$configPath = Join-Path $PSScriptRoot "..\config\config.json"
if (-not (Test-Path $configPath)) { Write-Error "配置文件不存在: $configPath"; exit 1 }
$config = Get-Content $configPath -Encoding utf8 | ConvertFrom-Json

$pythonExe = $config.python_exe
$entryScript = Join-Path $config.script_dir $config.entry_script

if (-not (Test-Path $pythonExe)) { Write-Error "Python解释器不存在: $pythonExe"; exit 1 }
if (-not (Test-Path $entryScript)) { Write-Error "入口脚本不存在: $entryScript"; exit 1 }

$args = @("--mode", $Mode)
if ($TargetDate) { $args = @($TargetDate) + $args }
if ($Force) { $args += "--force" }

Write-Host "执行: $pythonExe $entryScript $($args -join ' ')"
& $pythonExe $entryScript @args
$exitCode = $LASTEXITCODE
Write-Host ""
Write-Host "退出码: $exitCode (0=成功 1=ERROR 2=CRITICAL)"
exit $exitCode