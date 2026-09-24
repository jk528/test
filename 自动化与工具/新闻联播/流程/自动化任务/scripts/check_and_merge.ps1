<#
.SYNOPSIS
半自动模式 - 检测并合并六要素结果

.DESCRIPTION
用于半自动模式：检测六要素结果JSON是否已填写完成，
如果已填写则自动执行 Phase 3 合并生成完整报告。

可手动运行，也可以配置为定时任务轮询。

.NOTES
版本: v1.0.0
日期: 2026-09-13
#>

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ConfigPath = Join-Path $ProjectRoot "config\config.json"
$LogDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    Write-Host $logLine
    $logFile = Join-Path $LogDir "merge_check_$(Get-Date -Format 'yyyyMMdd').log"
    Add-Content -Path $logFile -Value $logLine -Encoding UTF8
}

# 读取配置
if (-not (Test-Path $ConfigPath)) {
    Write-Log "配置文件不存在: $ConfigPath" "ERROR"
    exit 1
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Log "========== 六要素合并检测 =========="

# 检查最近N天的日期
$checkDays = 7
$foundAny = $false

for ($i = 0; $i -lt $checkDays; $i++) {
    $date = (Get-Date).AddDays(-$i)
    $dateStr = $date.ToString("yyyyMMdd")
    $monthDir = "$($date.Year)年$($date.Month)月"
    $archiveDir = Join-Path (Join-Path $ProjectRoot $config.paths.output_dir) $monthDir
    $resultJson = Join-Path $archiveDir "六要素结果_$dateStr.json"
    $reportMd = Join-Path $archiveDir "新闻联播总结_$dateStr.md"
    
    # 检查结果JSON是否存在
    if (-not (Test-Path $resultJson)) {
        continue
    }
    
    # 检查报告是否已完整
    if (Test-Path $reportMd) {
        $fileSizeKB = (Get-Item $reportMd).Length / 1KB
        if ($fileSizeKB -gt 50) {
            Write-Log "$dateStr 报告已完整，跳过"
            continue
        }
    }
    
    $foundAny = $true
    Write-Log "检测到待合并: $dateStr"
    
    # 执行合并
    $scriptPath = Join-Path (Join-Path $ProjectRoot $config.paths.script_dir) $config.paths.gen_final_script
    $pythonExe = $config.paths.python_exe
    
    $output = & $pythonExe $scriptPath $dateStr --merge 2>&1
    $exitCode = $LASTEXITCODE
    
    foreach ($line in $output) {
        Write-Log "  [Python] $line"
    }
    
    if ($exitCode -eq 0) {
        Write-Log "$dateStr 合并成功！" "SUCCESS"
    } else {
        Write-Log "$dateStr 合并失败，退出码: $exitCode" "ERROR"
    }
}

if (-not $foundAny) {
    Write-Log "最近 $checkDays 天没有待合并的任务"
}

Write-Log "========== 检测完成 =========="
