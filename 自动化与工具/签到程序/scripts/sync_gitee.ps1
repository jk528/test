$ErrorActionPreference = "Continue"

# ============================================================
#  归档 Git 同步（单实例）
#  调用方：XinWenLianBo_Sync_0600（每天 06:15）
#          XinWenLianBo_Sync_30min（每 30 分钟，相位 :27/:57）
#  两个计划任务跑的是同一份脚本，靠文件锁保证不会并发执行，
#  避免 git 的 index.lock 撞车。
# ============================================================

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$LogFile  = Join-Path $ScriptDir "..\logs\sync_gitee.log"
$LockFile = Join-Path $ScriptDir ".sync_gitee.lock"

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Write-Log {
    param([string]$msg)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Host $line
    try { Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue } catch {}
}

# 计划任务环境的 PATH 可能不含 Git，这里自动探测 Git 安装路径
$gitCmd = $null
if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitCmd = "git"
} elseif (Test-Path "C:\Program Files\Git\cmd\git.exe") {
    $env:Path = "C:\Program Files\Git\cmd;" + $env:Path
    $gitCmd = "git"
} elseif (Test-Path "C:\Program Files (x86)\Git\cmd\git.exe") {
    $env:Path = "C:\Program Files (x86)\Git\cmd;" + $env:Path
    $gitCmd = "git"
} elseif (Test-Path "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe") {
    $env:Path = "$env:LOCALAPPDATA\Programs\Git\cmd;" + $env:Path
    $gitCmd = "git"
}
if (-not $gitCmd) {
    Write-Log "ERROR: Git not found. Please install Git or add it to PATH."
    exit 1
}

# --- 日志轮转：超过 256KB 就把旧日志滚成 .old（只保留一代） ---
try {
    if ((Test-Path -LiteralPath $LogFile) -and (Get-Item -LiteralPath $LogFile).Length -gt 262144) {
        Move-Item -LiteralPath $LogFile -Destination "$LogFile.old" -Force -ErrorAction SilentlyContinue
    }
} catch {}

# --- 单实例锁：独占打开锁文件；抢不到说明已有实例在跑 ---
#     进程被强制结束时句柄由系统回收，不会留下死锁。
$lockStream = $null
try {
    $lockStream = [System.IO.File]::Open(
        $LockFile,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
    try { (Get-Item -LiteralPath $LockFile -Force).Attributes = 'Hidden' } catch {}
} catch {
    Write-Log "SKIP: another sync instance is running (lock held), exit"
    exit 0
}

try {
    Write-Log "===== sync start (pid $PID) ====="

    $repoRoot = "C:\Users\Administrator\Desktop\JK-temp"
    Set-Location $repoRoot -ErrorAction Stop

    Write-Log "repo root: $repoRoot"

    # --- index.lock 自愈：进程被强杀/断电会留下 stale lock，不清理后续永远失败 ---
    #     规则：有 git 进程在跑 → 跳过本轮；锁很新(<5 分钟) → 下轮再说；
    #           无 git 进程且锁超过 5 分钟 → 判定为残留锁，删除。
    $IndexLock = Join-Path $repoRoot ".git\index.lock"
    if (Test-Path -LiteralPath $IndexLock) {
        $gitProcs = Get-Process -Name git,git-remote-https,git-remote-http,ssh -ErrorAction SilentlyContinue
        $lockAge = (Get-Date) - (Get-Item -LiteralPath $IndexLock).LastWriteTime
        if ($gitProcs) {
            Write-Log "SKIP: .git/index.lock exists and git process is running, wait next round"
            Write-Log "===== sync end (skip, git busy) ====="
            exit 0
        }
        if ($lockAge.TotalMinutes -lt 5) {
            Write-Log ("SKIP: .git/index.lock fresh ({0:N0}s), wait next round" -f $lockAge.TotalSeconds)
            Write-Log "===== sync end (skip, lock fresh) ====="
            exit 0
        }
        Write-Log ("STALE LOCK: no git process, lock age {0:N0} min, removing index.lock" -f $lockAge.TotalMinutes)
        Remove-Item -LiteralPath $IndexLock -Force -ErrorAction Stop
    }

    # --- 防挂起：计划任务无交互环境，凭证失效/传输停滞时快速失败而非永久等待 ---
    $env:GIT_TERMINAL_PROMPT = "0"

    # --- 仓库体积检查：接近 Gitee 配额（819 MB）时告警，平时静默 ---
    try {
        $m = (git count-objects -v 2>$null | Select-String "^size-pack:\s+(\d+)")
        if ($m) {
            $mb = [math]::Round([double]$m.Matches[0].Groups[1].Value / 1024)
            if ($mb -ge 700) {
                Write-Log ("WARN: repo pack size ~{0} MB approaching Gitee quota (819 MB), consider cleaning large files in history" -f $mb)
            }
        }
    } catch {}

    # --- 空闲轮快速退出：树干净时跳过 add/commit/push，只同步远端变更 ---
    $dirty = @(git status --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR: git status failed, abort this round"
        Write-Log "===== sync end (status failed) ====="
        exit 1
    }
    if ($dirty.Count -eq 0) {
        Write-Log "working tree clean, pull-only round"
        git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=60 pull origin main --no-edit --ff-only 2>&1 | ForEach-Object { Write-Log $_ }
        $pullExit = $LASTEXITCODE
        Write-Log "pull exit code: $pullExit"
        if ($pullExit -ne 0) {
            Write-Log "pull failed"
            Write-Log "===== sync end (pull failed) ====="
            exit 1
        }
        Write-Log "===== sync end (clean, nothing to push) ====="
        exit 0
    }

    Write-Log "git add -A"
    git add -A 2>&1 | ForEach-Object { Write-Log $_ }
    $addExit = $LASTEXITCODE
    Write-Log "add exit code: $addExit"
    if ($addExit -ne 0) {
        Write-Log "add failed, abort this round"
        Write-Log "===== sync end (add failed) ====="
        exit 1
    }

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
            Write-Log "commit failed, abort this round"
            Write-Log "===== sync end (commit failed) ====="
            exit 1
        }
    }

    Write-Log "git pull origin main --no-edit --ff-only"
    git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=60 pull origin main --no-edit --ff-only 2>&1 | ForEach-Object { Write-Log $_ }
    $pullExit = $LASTEXITCODE
    Write-Log "pull exit code: $pullExit"

    if ($pullExit -ne 0) {
        Write-Log "pull failed (diverged or network issue), stop push"
        Write-Log "===== sync end (pull failed) ====="
        exit 1
    }

    Write-Log "git push origin main"
    git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=60 push origin main 2>&1 | ForEach-Object { Write-Log $_ }
    $pushExit = $LASTEXITCODE
    Write-Log "push exit code: $pushExit"

    if ($pushExit -ne 0) {
        Write-Log "push failed"
        Write-Log "===== sync end (push failed) ====="
        exit 1
    }

    Write-Log "===== sync success ====="
}
finally {
    if ($lockStream) {
        try { $lockStream.Close() } catch {}
        try { $lockStream.Dispose() } catch {}
    }
}
