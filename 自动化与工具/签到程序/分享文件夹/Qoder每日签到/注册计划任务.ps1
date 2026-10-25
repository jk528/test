# ============================================================
# Qoder 每日签到 - 计划任务一键注册 / 卸载
#
# 用法（在本文件所在目录打开 PowerShell）:
#   .\注册计划任务.ps1                    注册，默认每天 10:40 触发
#   .\注册计划任务.ps1 -Time "11:30"      自定义触发时间
#   .\注册计划任务.ps1 -TaskName "我的签到" 自定义任务名
#   .\注册计划任务.ps1 -Remove            卸载任务
#
# 重要：Qoder 签到活动每日 10:00（UTC+8）才刷新！
#   触发时间绝不能早于 10:30，否则当天活动还没生成，必然扑空。
#   本脚本默认 10:40，自定义 -Time 时脚本会对早于 10:30 的值发出警告。
#
# 注意事项（均为实测结论）:
#   - 本文件夹路径不要含空格；cmd 对「引号包裹路径 + >> 重定向」
#     的组合存在解析 bug，会导致任务秒退码 1 且无日志
#   - 使用 Register-ScheduledTask 而非 schtasks（中文任务名无乱码）
#   - -StartWhenAvailable: 关机错过触发时间后，开机自动补跑
# ============================================================
param(
  [string]$Time = "10:40",
  [string]$TaskName = "Qoder每日签到",
  [switch]$Remove
)

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "已删除计划任务: $TaskName"
  exit 0
}

if ($Time -lt "10:30") {
  Write-Host "警告: 触发时间 $Time 早于 10:30！" -ForegroundColor Yellow
  Write-Host "Qoder 签到活动每日 10:00 才刷新，早于 10:30 触发当天必然领不到。" -ForegroundColor Yellow
  Write-Host "继续注册，但强烈建议改用 10:30 之后的时间（如 -Time ""10:40""）。" -ForegroundColor Yellow
  Write-Host ""
}

$dir = $PSScriptRoot
if (-not $dir) { $dir = (Get-Location).Path }
if ($dir -match '\s') {
  Write-Host "错误: 当前路径包含空格 ($dir)" -ForegroundColor Red
  Write-Host "请将整个文件夹移动到无空格的路径后重试（中文路径没问题）" -ForegroundColor Red
  exit 1
}

$logDir = Join-Path $dir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# cmd 路径与 >> 重定向目标均不加引号（路径无空格前提下最稳）
$arg      = "/s /c $dir\scripts\run_checkin.cmd >> $logDir\checkin.log 2>&1"
$action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arg
$trigger  = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "已注册计划任务: $TaskName（每天 $Time 触发）"
Write-Host ""
Write-Host "验证命令:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'        # 立即手动触发一次"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'      # 查看上次结果/下次运行时间"
Write-Host "  Get-Content '$logDir\checkin.log' -Tail 20       # 查看日志"
