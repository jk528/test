# JK-temp 自动同步脚本（增强版）
# 工作目录: c:\Users\Administrator\Documents\这是什么\JK-temp
# 功能: 检查变更 -> 提交 -> 推送到 Gitee 和 GitHub（支持中文文件名、网络超时重试）

param(
    [string]$WorkDir = "c:\Users\Administrator\Documents\这是什么\JK-temp",
    [string]$LogFile = "c:\Users\Administrator\Documents\这是什么\JK-temp\sync.log",
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 5
)

# 设置编码支持中文
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:LC_ALL = "C.UTF-8"

# 记录日志函数
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    try {
        Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        Write-Host "[警告] 无法写入日志文件: $_"
    }
}

# 带重试的Git推送函数
function Push-WithRetry {
    param(
        [string]$Remote,
        [string]$RefSpec,
        [int]$MaxAttempts = 3
    )
    
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-Log "推送到 $Remote... (尝试 $attempt/$MaxAttempts)"
        
        # 使用 --timeout 和设置低速度限制来避免长时间挂起
        $output = git push $Remote $RefSpec 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-Log "推送到 $Remote 成功"
            return $true
        } else {
            $errorMsg = $output -join "; "
            Write-Log "推送到 $Remote 失败: $errorMsg" "WARN"
            
            if ($attempt -lt $MaxAttempts) {
                Write-Log "等待 ${RetryDelaySeconds}秒后重试..." "INFO"
                Start-Sleep -Seconds $RetryDelaySeconds
            }
        }
    }
    
    Write-Log "推送到 $Remote 最终失败，已尝试 $MaxAttempts 次" "ERROR"
    return $false
}

# 主程序
try {
    # 切换到工作目录
    if (-not (Test-Path $WorkDir)) {
        Write-Log "工作目录不存在: $WorkDir" "ERROR"
        exit 1
    }
    
    Set-Location $WorkDir
    Write-Log "=========================================="
    Write-Log "进入工作目录: $WorkDir"
    
    # 检查是否是Git仓库
    if (-not (Test-Path ".git")) {
        Write-Log "当前目录不是Git仓库" "ERROR"
        exit 1
    }
    
    # 配置git支持中文文件名
    git config core.quotepath false | Out-Null
    git config core.precomposeunicode true | Out-Null
    
    # 获取当前分支
    $currentBranch = git branch --show-current 2>$null
    if ([string]::IsNullOrWhiteSpace($currentBranch)) {
        $currentBranch = "main"
    }
    Write-Log "当前分支: $currentBranch"
    
    # 获取当前日期时间用于提交信息
    $commitMessage = "定时同步: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    # 检查是否有未跟踪的文件或修改
    Write-Log "检查文件变更状态..."
    $status = git status --porcelain 2>$null
    
    if ([string]::IsNullOrWhiteSpace($status)) {
        # 没有变更
        Write-Log "无变更，跳过同步" "INFO"
        exit 0
    }
    
    # 有变更，显示变更内容
    $changeCount = ($status | Measure-Object).Count
    Write-Log "检测到 $changeCount 个文件变更:"
    $status | ForEach-Object { Write-Log "  $_" }
    
    # 执行 git add
    Write-Log "执行 git add ."
    git add .
    if ($LASTEXITCODE -ne 0) {
        Write-Log "git add 失败" "ERROR"
        exit 1
    }
    Write-Log "git add 成功"
    
    # 执行 git commit
    Write-Log "执行 git commit -m `"$commitMessage`""
    git commit -m "$commitMessage"
    if ($LASTEXITCODE -ne 0) {
        Write-Log "git commit 失败" "ERROR"
        exit 1
    }
    Write-Log "git commit 成功: $commitMessage"
    
    # 推送到 Gitee
    $giteeResult = Push-WithRetry -Remote "gitee-test" -RefSpec "main:main" -MaxAttempts $MaxRetries
    
    # 推送到 GitHub
    $githubResult = Push-WithRetry -Remote "github" -RefSpec "main:main" -MaxAttempts $MaxRetries
    
    # 总结
    if ($giteeResult -and $githubResult) {
        Write-Log "同步任务完成 - 全部成功"
    } elseif ($giteeResult -or $githubResult) {
        Write-Log "同步任务完成 - 部分成功" "WARN"
    } else {
        Write-Log "同步任务完成 - 全部失败" "ERROR"
    }
    Write-Log "=========================================="
    
} catch {
    Write-Log "发生异常: $_" "ERROR"
    exit 1
}
