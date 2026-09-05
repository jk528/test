$ErrorActionPreference = "Continue"
$logDir = "$PSScriptRoot\sync_logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir ("sync_" + (Get-Date -Format "yyyyMMdd") + ".log")

function Write-Log {
    param([string]$msg)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-Log "===== sync start ====="

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

Write-Log "repo root: $repoRoot"
Write-Log "git add -A"
git add -A 2>&1 | ForEach-Object { Write-Log $_ }

$commitMsg = "sync: " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Write-Log "git commit -m `"$commitMsg`""
$commitOutput = git commit -m $commitMsg 2>&1
$commitExit = $LASTEXITCODE
Write-Log "commit exit code: $commitExit"

if ($commitExit -ne 0) {
    $commitLower = ($commitOutput | Out-String).ToLower()
    if ($commitLower -match "nothing to commit" -or $commitLower -match "no changes" -or $commitLower -match "nothing added") {
        Write-Log "no changes, skip commit (normal)"
    } else {
        Write-Log "commit unexpected: $commitOutput"
    }
}

Write-Log "git pull origin main --no-edit"
git pull origin main --no-edit 2>&1 | ForEach-Object { Write-Log $_ }
$pullExit = $LASTEXITCODE
Write-Log "pull exit code: $pullExit"

if ($pullExit -ne 0) {
    Write-Log "pull failed, stop push"
    Write-Log "===== sync end (pull failed) ====="
    exit 1
}

Write-Log "git push origin main"
git push origin main 2>&1 | ForEach-Object { Write-Log $_ }
$pushExit = $LASTEXITCODE
Write-Log "push exit code: $pushExit"

if ($pushExit -ne 0) {
    Write-Log "push failed"
    Write-Log "===== sync end (push failed) ====="
    exit 1
}

Write-Log "===== sync success ====="