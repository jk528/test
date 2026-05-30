# JK-temp Auto Sync Script
# Supports Chinese filenames, with network timeout retry mechanism

# Get script directory (handles Chinese paths correctly)
$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    $scriptPath = $PSScriptRoot
}
$workspace = Split-Path -Parent $scriptPath
$logFile = Join-Path $workspace "sync.log"

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Write log function
function Write-Log {
    param([string]$message, [string]$level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$level] $message"
    try {
        Add-Content -Path $logFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
    Write-Host $logEntry
}

# Enter workspace
Set-Location -LiteralPath $workspace

# Configure git for Chinese support
& git config core.quotepath false
& git config http.lowSpeedLimit 1000
& git config http.lowSpeedTime 60

Write-Log "Start checking sync status..."

# Check for changes
$status = & git status --porcelain 2>$null

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Log "No changes, skip sync" "SKIP"
    exit 0
}

Write-Log "Changes detected, preparing sync..." "INFO"
Write-Log "Changes: $($status -join '; ')" "DETAIL"

# Add all changes
& git add .
if ($LASTEXITCODE -ne 0) {
    Write-Log "git add failed" "ERROR"
    exit 1
}

# Commit changes
$commitMsg = "Sync: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
& git commit -m "$commitMsg"
if ($LASTEXITCODE -ne 0) {
    Write-Log "git commit failed" "ERROR"
    exit 1
}
Write-Log "Local commit success: $commitMsg" "SUCCESS"

# Push function with retry
function Push-WithRetry {
    param([string]$remote, [string]$branch = "main:main", [int]$maxRetries = 2)
    
    $success = $false
    for ($i = 0; $i -le $maxRetries; $i++) {
        Write-Log "Pushing to $remote (attempt $($i+1)/$($maxRetries+1))..." "INFO"
        
        & git push $remote $branch 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Push to $remote success" "SUCCESS"
            $success = $true
            break
        }
        
        if ($i -lt $maxRetries) {
            Write-Log "Push to $remote failed, retry in 30s..." "WARN"
            Start-Sleep -Seconds 30
        }
    }
    
    if (-not $success) {
        Write-Log "Push to $remote finally failed" "ERROR"
    }
    return $success
}

# Push to Gitee
$giteeResult = Push-WithRetry -remote "gitee-test" -branch "main:main"

# Push to GitHub
$githubResult = Push-WithRetry -remote "github" -branch "main:main"

# Summary
if ($giteeResult -and $githubResult) {
    Write-Log "Sync complete: Gitee and GitHub both success" "SUCCESS"
} elseif ($giteeResult) {
    Write-Log "Sync partial: Gitee success, GitHub failed" "WARN"
} elseif ($githubResult) {
    Write-Log "Sync partial: GitHub success, Gitee failed" "WARN"
} else {
    Write-Log "Sync failed: Both Gitee and GitHub failed" "ERROR"
}

Write-Log "Sync task finished" "INFO"
