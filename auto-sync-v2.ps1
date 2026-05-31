# PC端Git同步脚本
param([string]$RepoPath = "c:\Users\Administrator\Documents\这是什么\JK-temp", [string]$LogFile = "c:\Users\Administrator\Documents\这是什么\JK-temp\sync.log")

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Log($Message, $Level) {
    if (-not $Level) { $Level = "INFO" }
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8
}

Set-Location -Path $RepoPath
Write-Log "进入工作目录: $RepoPath"

if (-not (Test-Path -Path ".git")) {
    Write-Log "错误: 当前目录不是git仓库" "ERROR"
    exit 1
}

$remotes = git remote
$hasGitee = $false
$hasGithub = $false
foreach ($r in $remotes) {
    if ($r -eq "gitee-test") { $hasGitee = $true }
    if ($r -eq "github") { $hasGithub = $true }
}
if (-not $hasGitee -or -not $hasGithub) {
    Write-Log "错误: 远程仓库配置不完整" "ERROR"
    exit 1
}

$dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMessage = "定时同步: $dateStr"

Write-Log "========== 开始同步任务 =========="

$statusOutput = git status --porcelain 2>&1
$hasChanges = $false
if ($statusOutput) {
    if ($statusOutput.GetType().IsArray) {
        if ($statusOutput.Length -gt 0) { $hasChanges = $true }
    } else {
        if ($statusOutput -ne "") { $hasChanges = $true }
    }
}

if (-not $hasChanges) {
    Write-Log "无变更，跳过同步" "INFO"
    Write-Log "========== 同步任务结束 =========="
    exit 0
}

Write-Log "检测到变更"
$statusOutput | ForEach-Object { Write-Log "  $_" }

Write-Log "执行 git add ."
$addOutput = git add . 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "错误: git add 失败" "ERROR"
    exit 1
}
Write-Log "git add 成功"

Write-Log "执行 git commit"
$commitOutput = git commit -m "$commitMessage" 2>&1
if ($LASTEXITCODE -ne 0) {
    $outputStr = $commitOutput -join " "
    if ($outputStr -match "nothing" -or $outputStr -match "没有") {
        Write-Log "没有需要提交的变更，跳过同步" "INFO"
        exit 0
    }
    Write-Log "错误: git commit 失败" "ERROR"
    exit 1
}
Write-Log "git commit 成功"

# 推送到远程
$giteeSuccess = $false
$githubSuccess = $false

# Gitee
Write-Log "推送到 Gitee..."
for ($i = 1; $i -le 3; $i++) {
    Write-Log "  尝试 $i/3..."
    $pushOutput = git push gitee-test main:main 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  Gitee 推送成功"
        $giteeSuccess = $true
        break
    } else {
        Write-Log "  Gitee 推送失败" "WARN"
        if ($i -lt 3) { Start-Sleep -Seconds 5 }
    }
}
if (-not $giteeSuccess) { Write-Log "Gitee推送最终失败" "ERROR" }

# GitHub
Write-Log "推送到 GitHub..."
for ($i = 1; $i -le 3; $i++) {
    Write-Log "  尝试 $i/3..."
    $pushOutput = git push github main:main 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  GitHub 推送成功"
        $githubSuccess = $true
        break
    } else {
        Write-Log "  GitHub 推送失败" "WARN"
        if ($i -lt 3) { Start-Sleep -Seconds 5 }
    }
}
if (-not $githubSuccess) { Write-Log "GitHub推送最终失败" "ERROR" }

Write-Log "========== 同步任务结束 =========="
if ($giteeSuccess -and $githubSuccess) {
    Write-Log "同步成功完成"
    exit 0
} elseif ($giteeSuccess -or $githubSuccess) {
    Write-Log "部分同步成功" "WARN"
    exit 1
} else {
    Write-Log "同步失败" "ERROR"
    exit 1
}
