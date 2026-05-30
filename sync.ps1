# JK-temp 自动同步脚本
# 工作目录: c:\Users\Administrator\Documents\这是什么\JK-temp
# 功能: 检查变更 -> 提交 -> 推送到 Gitee 和 GitHub

param(
    [string]$WorkDir = "c:\Users\Administrator\Documents\这是什么\JK-temp",
    [string]$LogFile = "c:\Users\Administrator\Documents\这是什么\JK-temp\sync.log"
)

# 设置编码支持中文
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 记录日志函数
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8
}

# 切换到工作目录
Set-Location $WorkDir
if ($LASTEXITCODE -ne 0) {
    Write-Log "无法进入工作目录: $WorkDir" "ERROR"
    exit 1
}
Write-Log "进入工作目录: $WorkDir"

# 检查是否是Git仓库
if (-not (Test-Path ".git")) {
    Write-Log "当前目录不是Git仓库" "ERROR"
    exit 1
}

# 获取当前日期时间用于提交信息
$commitMessage = "定时同步: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# 检查是否有未跟踪的文件或修改
Write-Log "检查文件变更状态..."
$status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($status)) {
    # 没有变更
    Write-Log "无变更，跳过同步" "INFO"
    exit 0
}

# 有变更，显示变更内容
Write-Log "检测到文件变更:"
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
Write-Log "推送到 Gitee..."
git push gitee-test main:main
if ($LASTEXITCODE -ne 0) {
    Write-Log "推送到 Gitee 失败" "ERROR"
} else {
    Write-Log "推送到 Gitee 成功"
}

# 推送到 GitHub
Write-Log "推送到 GitHub..."
git push github main:main
if ($LASTEXITCODE -ne 0) {
    Write-Log "推送到 GitHub 失败" "ERROR"
} else {
    Write-Log "推送到 GitHub 成功"
}

Write-Log "同步任务完成"
