<#
.SYNOPSIS
新闻联播每日总结 - 定时任务主执行脚本

.DESCRIPTION
根据配置文件自动执行新闻联播总结报告生成任务
支持三种模式：auto_v2（全自动正则）、semi_auto（半自动分阶段）、ai_api（AI API全自动）

.NOTES
版本: v1.0.0
日期: 2026-09-13
#>

$ErrorActionPreference = "Continue"

# ============================================================
# 路径配置
# ============================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ConfigPath = Join-Path $ProjectRoot "config\config.json"
$LogDir = Join-Path $ProjectRoot "logs"

# 确保日志目录存在
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

# ============================================================
# 日志函数
# ============================================================
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    
    # 输出到控制台
    Write-Host $logLine
    
    # 写入日志文件（按天）
    $logFile = Join-Path $LogDir "task_$(Get-Date -Format 'yyyyMMdd').log"
    Add-Content -Path $logFile -Value $logLine -Encoding UTF8
}

function Write-Success { param([string]$Message) Write-Log $Message "SUCCESS" }
function Write-Warning { param([string]$Message) Write-Log $Message "WARN" }
function Write-Error { param([string]$Message) Write-Log $Message "ERROR" }

# ============================================================
# 读取配置
# ============================================================
function Get-Config {
    if (-not (Test-Path $ConfigPath)) {
        Write-Error "配置文件不存在: $ConfigPath"
        return $null
    }
    try {
        $config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        return $config
    } catch {
        Write-Error "读取配置文件失败: $_"
        return $null
    }
}

# ============================================================
# 获取目标日期（昨天）
# ============================================================
function Get-TargetDate {
    $yesterday = (Get-Date).AddDays(-1)
    return $yesterday.ToString("yyyyMMdd")
}

# ============================================================
# 模式一：全自动 v2（正则提取六要素）
# ============================================================
function Invoke-AutoV2Mode {
    param(
        [string]$DateStr,
        [psobject]$Config
    )
    
    Write-Log "========== 模式: 全自动 v2（正则版） =========="
    
    $scriptPath = Join-Path (Join-Path $ProjectRoot $Config.paths.script_dir) $Config.paths.gen_v2_script
    
    if (-not (Test-Path $scriptPath)) {
        Write-Error "脚本不存在: $scriptPath"
        return $false
    }
    
    Write-Log "执行脚本: $scriptPath"
    Write-Log "目标日期: $DateStr"
    
    $pythonExe = $Config.paths.python_exe
    
    try {
        $output = & $pythonExe $scriptPath $DateStr 2>&1
        $exitCode = $LASTEXITCODE
        
        # 记录输出
        foreach ($line in $output) {
            Write-Log "  [Python] $line"
        }
        
        if ($exitCode -eq 0) {
            Write-Success "v2 报告生成成功"
            return $true
        } else {
            Write-Error "v2 报告生成失败，退出码: $exitCode"
            return $false
        }
    } catch {
        Write-Error "执行脚本异常: $_"
        return $false
    }
}

# ============================================================
# 模式二：半自动分阶段（Phase 1 自动）
# ============================================================
function Invoke-SemiAutoPhase1 {
    param(
        [string]$DateStr,
        [psobject]$Config
    )
    
    Write-Log "========== 模式: 半自动 Phase 1 =========="
    
    $scriptPath = Join-Path (Join-Path $ProjectRoot $Config.paths.script_dir) $Config.paths.gen_final_script
    
    if (-not (Test-Path $scriptPath)) {
        Write-Error "脚本不存在: $scriptPath"
        return $false
    }
    
    Write-Log "执行 Phase 1: 生成1-5部分 + 数据源JSON"
    Write-Log "目标日期: $DateStr"
    
    $pythonExe = $Config.paths.python_exe
    
    try {
        $output = & $pythonExe $scriptPath $DateStr 2>&1
        $exitCode = $LASTEXITCODE
        
        foreach ($line in $output) {
            Write-Log "  [Python] $line"
        }
        
        if ($exitCode -eq 0) {
            Write-Success "Phase 1 完成，等待人工填写六要素JSON"
            Write-Log "提示: 填写完成后运行 --merge 或等待自动检测合并"
            return $true
        } else {
            Write-Error "Phase 1 失败，退出码: $exitCode"
            return $false
        }
    } catch {
        Write-Error "执行脚本异常: $_"
        return $false
    }
}

# ============================================================
# 模式二：半自动分阶段（Phase 3 合并检测）
# ============================================================
function Invoke-SemiAutoPhase3Check {
    param(
        [string]$DateStr,
        [psobject]$Config
    )
    
    Write-Log "检查是否有待合并的六要素结果..."
    
    $targetDate = [datetime]::ParseExact($DateStr, "yyyyMMdd", $null)
    $monthDir = "$($targetDate.Year)年$($targetDate.Month)月"
    $archiveDir = Join-Path (Join-Path $ProjectRoot $Config.paths.output_dir) $monthDir
    $resultJson = Join-Path $archiveDir "六要素结果_$DateStr.json"
    $reportMd = Join-Path $archiveDir "新闻联播总结_$DateStr.md"
    
    # 检查结果JSON是否存在
    if (-not (Test-Path $resultJson)) {
        Write-Log "六要素结果JSON不存在，跳过合并: $resultJson"
        return $false
    }
    
    # 检查报告是否已完整生成（文件大小 > 50KB 通常表示已包含六七部分）
    if (Test-Path $reportMd) {
        $fileSizeKB = (Get-Item $reportMd).Length / 1KB
        if ($fileSizeKB -gt 50) {
            Write-Log "报告已存在且内容完整（$([math]::Round($fileSizeKB, 1)) KB），跳过合并"
            return $false
        }
    }
    
    Write-Log "检测到六要素结果JSON，开始 Phase 3 合并..."
    
    $scriptPath = Join-Path (Join-Path $ProjectRoot $Config.paths.script_dir) $Config.paths.gen_final_script
    $pythonExe = $Config.paths.python_exe
    
    try {
        $output = & $pythonExe $scriptPath $DateStr --merge 2>&1
        $exitCode = $LASTEXITCODE
        
        foreach ($line in $output) {
            Write-Log "  [Python] $line"
        }
        
        if ($exitCode -eq 0) {
            Write-Success "Phase 3 合并完成，完整报告已生成"
            return $true
        } else {
            Write-Error "Phase 3 合并失败，退出码: $exitCode"
            return $false
        }
    } catch {
        Write-Error "执行合并异常: $_"
        return $false
    }
}

# ============================================================
# 质量检查
# ============================================================
function Invoke-QualityCheck {
    param(
        [string]$DateStr,
        [psobject]$Config
    )
    
    if (-not $Config.quality.run_quality_check) {
        Write-Log "质量检查已禁用，跳过"
        return $true
    }
    
    Write-Log "========== 质量检查 =========="
    
    $targetDate = [datetime]::ParseExact($DateStr, "yyyyMMdd", $null)
    $monthDir = "$($targetDate.Year)年$($targetDate.Month)月"
    $archiveDir = Join-Path (Join-Path $ProjectRoot $Config.paths.output_dir) $monthDir
    $reportMd = Join-Path $archiveDir "新闻联播总结_$DateStr.md"
    
    if (-not (Test-Path $reportMd)) {
        Write-Warning "报告文件不存在，跳过质量检查: $reportMd"
        return $false
    }
    
    # 检查文件大小
    $fileSizeKB = (Get-Item $reportMd).Length / 1KB
    Write-Log "文件大小: $([math]::Round($fileSizeKB, 1)) KB"
    
    if ($fileSizeKB -lt $Config.quality.min_file_size_kb) {
        Write-Error "文件大小不足 $($Config.quality.min_file_size_kb) KB，可能生成不完整"
        return $false
    }
    
    # 运行质量检查脚本（如果存在）
    $checkScript = Join-Path (Join-Path $ProjectRoot $Config.paths.script_dir) $Config.quality.quality_check_script
    if (Test-Path $checkScript) {
        Write-Log "运行质量检查脚本..."
        $pythonExe = $Config.paths.python_exe
        try {
            $output = & $pythonExe $checkScript $reportMd 2>&1
            foreach ($line in $output) {
                Write-Log "  [Quality] $line"
            }
        } catch {
            Write-Warning "质量检查脚本执行异常: $_"
        }
    }
    
    Write-Success "质量检查通过"
    return $true
}

# ============================================================
# Git 同步
# ============================================================
function Invoke-GitSync {
    param([psobject]$Config)
    
    if (-not $Config.sync.enabled) {
        Write-Log "Git同步已禁用，跳过"
        return $true
    }
    
    Write-Log "========== Git 同步 =========="
    
    $syncScript = Join-Path $ProjectRoot $Config.sync.sync_script
    
    if (-not (Test-Path $syncScript)) {
        Write-Warning "同步脚本不存在，跳过: $syncScript"
        return $false
    }
    
    try {
        $output = & powershell -ExecutionPolicy Bypass -File $syncScript 2>&1
        foreach ($line in $output) {
            Write-Log "  [GitSync] $line"
        }
        Write-Success "Git同步完成"
        return $true
    } catch {
        Write-Error "Git同步异常: $_"
        return $false
    }
}

# ============================================================
# 重试机制
# ============================================================
function Invoke-WithRetry {
    param(
        [scriptblock]$ScriptBlock,
        [int]$MaxRetries = 3,
        [int]$RetryIntervalSeconds = 300
    )
    
    $attempt = 0
    while ($attempt -lt $MaxRetries) {
        $attempt++
        Write-Log "执行尝试 $attempt / $MaxRetries"
        
        $result = & $ScriptBlock
        
        if ($result) {
            return $true
        }
        
        if ($attempt -lt $MaxRetries) {
            Write-Warning "执行失败，$RetryIntervalSeconds 秒后重试..."
            Start-Sleep -Seconds $RetryIntervalSeconds
        }
    }
    
    Write-Error "已达到最大重试次数 $MaxRetries，任务失败"
    return $false
}

# ============================================================
# 主函数
# ============================================================
function Main {
    Write-Log "============================================================"
    Write-Log "  新闻联播每日总结 - 定时任务开始执行"
    Write-Log "============================================================"
    
    # 读取配置
    $config = Get-Config
    if (-not $config) {
        Write-Error "无法读取配置，任务终止"
        exit 1
    }
    
    # 获取目标日期
    $dateStr = Get-TargetDate
    Write-Log "目标日期: $dateStr"
    Write-Log "执行模式: $($config.mode)"
    Write-Log ""
    
    $success = $false
    
    # 根据模式执行
    switch ($config.mode) {
        "auto_v2" {
            $success = Invoke-WithRetry -ScriptBlock {
                param($d, $c) Invoke-AutoV2Mode -DateStr $d -Config $c
            } -MaxRetries $config.retry.max_retries -RetryIntervalSeconds $config.retry.retry_interval_seconds -ArgumentList $dateStr, $config
        }
        
        "semi_auto" {
            # Phase 1: 生成1-5部分 + 数据源JSON
            $phase1Success = Invoke-WithRetry -ScriptBlock {
                param($d, $c) Invoke-SemiAutoPhase1 -DateStr $d -Config $c
            } -MaxRetries $config.retry.max_retries -RetryIntervalSeconds $config.retry.retry_interval_seconds -ArgumentList $dateStr, $config
            
            # 尝试 Phase 3 合并（如果结果JSON已存在）
            $phase3Success = Invoke-SemiAutoPhase3Check -DateStr $dateStr -Config $config
            
            $success = $phase1Success
        }
        
        "ai_api" {
            Write-Warning "AI API 模式暂未实现，请使用 auto_v2 或 semi_auto 模式"
            $success = $false
        }
        
        default {
            Write-Error "未知模式: $_"
            $success = $false
        }
    }
    
    # 质量检查
    if ($success) {
        Invoke-QualityCheck -DateStr $dateStr -Config $config | Out-Null
    }
    
    # Git同步
    Invoke-GitSync -Config $config | Out-Null
    
    # 总结
    Write-Log ""
    if ($success) {
        Write-Success "任务执行成功！"
    } else {
        Write-Error "任务执行失败！"
    }
    Write-Log "============================================================"
    Write-Log ""
    
    exit [int](-not $success)
}

# 执行主函数
Main
