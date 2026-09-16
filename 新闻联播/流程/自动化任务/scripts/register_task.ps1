<#
.SYNOPSIS
注册 Windows 任务计划程序 - 新闻联播每日总结

.DESCRIPTION
读取 config.json，创建计划任务：每天在 config.schedule.time 指定的时刻
直接调用「一键生成/xwlb_report.py」生成前一天的报告。

任务动作（主）：
    <python.exe> "流程\一键生成\xwlb_report.py"      # 不带日期参数 = 昨天
任务动作（可选，config.sync.enabled 为 true 时追加）：
    powershell -File 流程\旧版本\sync_gitee.ps1      # 生成后同步归档到 Gitee

.PARAMETER Force
    已存在同名任务时直接覆盖，不弹询问。
.PARAMETER NoPause
    结束时不停留等待按键。
.PARAMETER NonInteractive
    无人值守模式（等价于 -Force -NoPause），且不尝试 UAC 提权；
    权限不足时以非 0 退出码结束，便于自动化链路判断。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\register_task.ps1 -NonInteractive

.NOTES
版本: v2.0.0
日期: 2026-09-16
变更: 任务动作改为直接调用 xwlb_report.py（不再经过 run_daily_task.ps1 外壳）；
      Python 解释器改为自动探测（要求 requests 可导入）；
      新增 -Force / -NoPause / -NonInteractive；文件以 UTF-8 BOM 保存
#>

param(
    [switch]$Force,
    [switch]$NoPause,
    [switch]$NonInteractive
)

if ($NonInteractive) {
    $Force = $true
    $NoPause = $true
}

$ErrorActionPreference = "Stop"

# ============================================================
# 辅助函数
# ============================================================
function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "  [OK] $Msg"   -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Err  { param([string]$Msg) Write-Host "  [ERR] $Msg"  -ForegroundColor Red }

# ============================================================
# 权限检查（仅在需要时提权；无人值守模式绝不提权）
# ============================================================
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$winPrincipal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $winPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    if ($NonInteractive) {
        Write-Err "需要管理员权限注册计划任务，当前为无人值守模式，不做提权。请以管理员身份重跑。"
        exit 1
    }
    Write-Warn "需要管理员权限来注册任务计划程序，正在请求提升..."
    Start-Process powershell -Verb runAs `
        -ArgumentList "-ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    exit
}

# ============================================================
# 路径配置
# ============================================================
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir          # ...\流程\自动化任务
$FlowRoot    = Split-Path -Parent $ProjectRoot        # ...\流程
$ConfigPath  = Join-Path $ProjectRoot "config\config.json"

# ============================================================
# 读取配置
# ============================================================
Write-Step "读取配置文件"

if (-not (Test-Path $ConfigPath)) {
    Write-Err "配置文件不存在: $ConfigPath"
    if (-not $NoPause) { pause }
    exit 1
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Ok "配置文件加载成功"
Write-Host "    任务名称: $($config.task_name)"
Write-Host "    执行时间: 每天 $($config.schedule.time)"
Write-Host "    执行模式: $($config.mode)"

# ============================================================
# 定位报告脚本
# ============================================================
Write-Step "检查报告脚本"

# 注意：config.paths 下的相对路径均以「自动化任务」目录为基准
$OneShotDir  = Join-Path $ProjectRoot $config.paths.oneshot_dir
$OneShotDir  = [System.IO.Path]::GetFullPath($OneShotDir)
$ReportScript = Join-Path $OneShotDir $config.paths.oneshot_script

if (-not (Test-Path $ReportScript)) {
    Write-Err "报告脚本不存在: $ReportScript"
    if (-not $NoPause) { pause }
    exit 1
}
Write-Ok "报告脚本: $ReportScript"

# ============================================================
# 探测 Python 解释器（必须能 import requests）
# ============================================================
Write-Step "探测 Python 解释器"

$candidates = @()
if ($config.paths.python_exe)       { $candidates += $config.paths.python_exe }
if ($config.paths.python_fallbacks) { $candidates += $config.paths.python_fallbacks }
$candidates += "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"

$PythonExe  = $null
$PythonInfo = $null
foreach ($c in $candidates) {
    if ([string]::IsNullOrWhiteSpace($c)) { continue }
    $exe = $c
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $exe = $cmd.Source }
    if (-not (Test-Path $exe)) { continue }
    try {
        $probe = & $exe -c "import sys,requests;print(sys.version.split()[0]+' | requests '+requests.__version__)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe) {
            $PythonExe  = $exe
            $PythonInfo = $probe
            break
        }
    } catch { }
}

if (-not $PythonExe) {
    Write-Err "未找到可用的 Python 解释器（需可导入 requests）。候选：$($candidates -join ' ; ')"
    if (-not $NoPause) { pause }
    exit 1
}
Write-Ok "使用解释器: $PythonExe"
Write-Host "    版本信息: $PythonInfo"

# ============================================================
# 组装任务动作
# ============================================================
Write-Step "组装任务动作"

$actions = @()

# 动作 1：直接运行一键生成脚本（不带日期 = 生成昨天的报告）
$actions += New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ReportScript`"" `
    -WorkingDirectory $OneShotDir
Write-Ok "动作1: `"$PythonExe`" `"$ReportScript`"  (WD=$OneShotDir)"

# 动作 2：可选，生成后同步归档
if ($config.sync -and $config.sync.enabled) {
    $syncScript = Join-Path $ProjectRoot $config.sync.sync_script
    $syncScript = [System.IO.Path]::GetFullPath($syncScript)
    if (Test-Path $syncScript) {
        $actions += New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$syncScript`"" `
            -WorkingDirectory (Split-Path -Parent $syncScript)
        Write-Ok "动作2: 同步归档 -> $syncScript"
    } else {
        Write-Warn "配置启用了同步但脚本不存在，已跳过: $syncScript"
    }
} else {
    Write-Host "    （同步未启用，跳过动作2）"
}

# ============================================================
# 检查任务是否已存在
# ============================================================
Write-Step "检查现有任务"

$taskName = $config.task_name
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    if ($Force) {
        Write-Warn "检测到同名任务，-Force 指定为直接覆盖"
    } else {
        Write-Warn "检测到同名任务已存在: $taskName"
        $choice = Read-Host "是否覆盖？(y/n)"
        if ($choice -ne 'y' -and $choice -ne 'Y') {
            Write-Host "用户取消，退出"
            if (-not $NoPause) { pause }
            exit 0
        }
    }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Ok "已删除旧任务"
} else {
    Write-Ok "无同名任务"
}

# ============================================================
# 创建任务计划
# ============================================================
Write-Step "创建任务计划程序"

$runTime = $config.schedule.time
Write-Ok "触发时间: 每天 $runTime（时区 $($config.schedule.timezone)）"

$trigger = New-ScheduledTaskTrigger -Daily -At $runTime

# StartWhenAvailable：错过计划时间（关机/休眠）后，恢复时补跑
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$settings.MultipleInstances = "IgnoreNew"

$currentUserName = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $currentUserName `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Description $config.task_description `
    -Trigger $trigger `
    -Action $actions `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Force | Out-Null

Write-Ok "任务计划创建成功！"

# ============================================================
# 显示任务信息
# ============================================================
Write-Step "任务详情"

$task     = Get-ScheduledTask -TaskName $taskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName

Write-Host "    任务名称: $($task.TaskName)"
Write-Host "    任务描述: $($task.Description)"
Write-Host "    执行状态: $($task.State)"
Write-Host "    运行账户: $($task.Principal.UserId)（$($task.Principal.LogonType)）"
Write-Host "    触发时间: $(($task.Triggers | ForEach-Object { $_.StartBoundary }) -join ', ')"
Write-Host "    动作数量: $($task.Actions.Count)"
Write-Host "    下次运行: $($taskInfo.NextRunTime)"
Write-Host "    上次运行: $($taskInfo.LastRunTime)"
Write-Host "    上次结果: $($taskInfo.LastTaskResult)"

# ============================================================
# 提示
# ============================================================
Write-Step "提示"

Write-Host "  任务已注册到 Windows 任务计划程序。"
Write-Host "  每天 $runTime 将直接运行 xwlb_report.py，生成前一天（昨天）的报告。"
Write-Host ""
Write-Host "  常用操作："
Write-Host "    立即验证: powershell -ExecutionPolicy Bypass -File .\run_now.ps1"
Write-Host "    查看状态: powershell -ExecutionPolicy Bypass -File .\check_status.ps1"
Write-Host "    查看任务: 开始菜单 -> 任务计划程序 -> 任务计划程序库"
Write-Host "    手工执行: schtasks /run /tn `"$taskName`""
Write-Host "    修改时间: 编辑 config\config.json 的 schedule.time 后重跑本脚本"
Write-Host "    卸载任务: powershell -ExecutionPolicy Bypass -File .\unregister_task.ps1"
Write-Host ""

if (-not $NoPause) { pause }
exit 0
