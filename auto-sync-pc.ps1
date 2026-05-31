# JK-temp PC端自动同步脚本
# 工作目录: c:\Users\Administrator\Documents\这是什么\JK-temp
# 功能: 检查变更 -> 提交 -> 推送到 Gitee 和 GitHub
# 特性: 支持中文文件名、网络超时重试、详细日志

param(
    [string]$WorkDir = "c:\Users\Administrator\Documents\这是什么\JK-temp",
    [string]$LogFile = "c:\Users\Administrator\Documents\这是什么\JK-temp\sync.log",
    [int]$MaxRetries = 3,
    [int]$RetryDelay = 5
)

# 设置编码支持中文
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 记录日志函数
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    try {
        Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        Write-Host "[WARNING] 无法写入日志文件: $_" -ForegroundColor Yellow
    }
}

# 执行Git命令带重试功能
function Invoke-GitCommand {
    param(
        [string]$Command,
        [string]$Description,
        [int]$TimeoutSeconds = 60
    )

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Log "执行: $Description (尝试 $attempt/$MaxRetries)..."

        try {
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = "git"
            $psi.Arguments = $Command
            $psi.WorkingDirectory = $WorkDir
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError = $true
            $psi.UseShellExecute = $false
            $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
            $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

            $process = New-Object System.Diagnostics.Process
            $process.StartInfo = $psi
            $process.Start() | Out-Null

            $completed = $process.WaitForExit($TimeoutSeconds * 1000)

            if (-not $completed) {
                $process.Kill()
                Write-Log "命令超时 (${TimeoutSeconds}秒)" "WARNING"
                if ($attempt -lt $MaxRetries) {
                    Write-Log "等待 ${RetryDelay}秒后重试..." "INFO"
                    Start-Sleep -Seconds $RetryDelay
                    continue
                }
                return $false
            }

            $stdout = $process.StandardOutput.ReadToEnd()
            $stderr = $process.StandardError.ReadToEnd()
            $exitCode = $process.ExitCode

            if ($exitCode -eq 0) {
                if ($stdout) {
                    Write-Log "输出: $stdout" "DEBUG"
                }
                return $true
            } else {
                Write-Log "Git错误: $stderr" "ERROR"
                if ($attempt -lt $MaxRetries) {
                    Write-Log "等待 ${RetryDelay}秒后重试..." "INFO"
                    Start-Sleep -Seconds $RetryDelay
                    continue
                }
                return $false
            }
        }
        catch {
            Write-Log "执行异常: $_" "ERROR"
            if ($attempt -lt $MaxRetries) {
                Write-Log "等待 ${RetryDelay}秒后重试..." "INFO"
                Start-Sleep -Seconds $RetryDelay
                continue
            }
            return $false
        }
    }
    return $false
}

# 主程序
Write-Log "========== PC端同步任务开始 =========="

# 检查工作目录
if (-not (Test-Path $WorkDir)) {
    Write-Log "工作目录不存在: $WorkDir" "ERROR"
    exit 1
}

# 切换到工作目录
try {
    Set-Location $WorkDir -ErrorAction Stop
    Write-Log "进入工作目录: $WorkDir"
} catch {
    Write-Log "无法进入工作目录: $_" "ERROR"
    exit 1
}

# 检查是否是Git仓库
if (-not (Test-Path ".git")) {
    Write-Log "当前目录不是Git仓库" "ERROR"
    exit 1
}

# 检查远程仓库配置
$remotes = git remote
if (-not ($remotes -contains "gitee-test") -or -not ($remotes -contains "github")) {
    Write-Log "远程仓库配置不完整。需要配置 gitee-test 和 github" "ERROR"
    exit 1
}

# 获取当前分支
$currentBranch = git branch --show-current
Write-Log "当前分支: $currentBranch"

# 检查是否有变更（处理中文文件名）
Write-Log "检查文件变更状态..."
$statusOutput = git status --porcelain 2>&1

if ([string]::IsNullOrWhiteSpace($statusOutput)) {
    Write-Log "无变更，跳过同步"
    Write-Log "========== 同步任务结束 =========="
    exit 0
}

# 有变更，显示变更内容
Write-Log "检测到文件变更:" "INFO"
$statusLines = $statusOutput -split "`r?`n"
$changeCount = 0
foreach ($line in $statusLines) {
    if (-not [string]::IsNullOrWhiteSpace($line)) {
        Write-Log "  $line" "DETAIL"
        $changeCount++
    }
}
Write-Log "共检测到 $changeCount 个变更" "INFO"

# 执行 git add
if (-not (Invoke-GitCommand -Command "add ." -Description "git add ." -TimeoutSeconds 30)) {
    Write-Log "git add 失败，终止同步" "ERROR"
    exit 1
}
Write-Log "git add 成功"

# 获取提交信息
$commitMessage = "定时同步: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# 执行 git commit
$commitCmd = "commit -m `"$commitMessage`""
if (-not (Invoke-GitCommand -Command $commitCmd -Description "git commit" -TimeoutSeconds 30)) {
    Write-Log "git commit 失败，终止同步" "ERROR"
    exit 1
}
Write-Log "git commit 成功: $commitMessage"

# 获取提交哈希
$commitHash = git rev-parse --short HEAD
Write-Log "提交哈希: $commitHash"

# 推送到 Gitee
$giteeSuccess = $false
if (Invoke-GitCommand -Command "push gitee-test main:main" -Description "推送到 Gitee" -TimeoutSeconds 120) {
    Write-Log "推送到 Gitee 成功"
    $giteeSuccess = $true
} else {
    Write-Log "推送到 Gitee 失败" "ERROR"
}

# 推送到 GitHub
$githubSuccess = $false
if (Invoke-GitCommand -Command "push github main:main" -Description "推送到 GitHub" -TimeoutSeconds 120) {
    Write-Log "推送到 GitHub 成功"
    $githubSuccess = $true
} else {
    Write-Log "推送到 GitHub 失败" "ERROR"
}

# 汇总结果
if ($giteeSuccess -and $githubSuccess) {
    Write-Log "同步完成 | commit: $commitHash | Gitee: 成功 | GitHub: 成功 | 变更文件数: $changeCount" "SUCCESS"
} elseif ($giteeSuccess) {
    Write-Log "同步部分完成 | commit: $commitHash | Gitee: 成功 | GitHub: 失败 | 变更文件数: $changeCount" "WARNING"
} elseif ($githubSuccess) {
    Write-Log "同步部分完成 | commit: $commitHash | Gitee: 失败 | GitHub: 成功 | 变更文件数: $changeCount" "WARNING"
} else {
    Write-Log "同步失败 | commit: $commitHash | Gitee: 失败 | GitHub: 失败" "ERROR"
}

Write-Log "========== PC端同步任务结束 =========="
