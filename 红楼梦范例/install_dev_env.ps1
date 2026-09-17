# install_dev_env.ps1
# 「红楼读析」开发环境一键安装脚本（Windows / winget）
# 幂等可重跑：每步先探测、已装则跳过；每步安装后必须拿到版本号证据才算成功
# 用法（任一）：
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\install_dev_env.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\install_dev_env.ps1 -SkipBuildTools
param(
  [switch]$SkipBuildTools,   # 跳过 MSVC C++ Build Tools（约 3GB，需 UAC）
  [switch]$SkipVenv,         # 跳过项目 venv 与 pip 依赖
  [switch]$UseOfficialPypi   # pip 用官方源（默认走清华镜像）
)

$ErrorActionPreference = 'Continue'
$ProjectRoot = 'a:\HuaweiMoveData\Users\代\Desktop\gitee\test\红楼梦范例'
$VenvDir     = Join-Path $env:USERPROFILE '.venvs\honglou'   # venv 放在同步文件夹之外
$LogFile     = Join-Path $PSScriptRoot 'install_dev_env.log'
$Winget      = "$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe"
$script:Result = @{}   # 记录每步结果

function Log([string]$msg) {
  $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $msg
  Write-Host $line
  Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Refresh-Path {
  $machine = [Environment]::GetEnvironmentVariable('Path','Machine')
  $user    = [Environment]::GetEnvironmentVariable('Path','User')
  $env:PATH = ($machine.TrimEnd(';') + ';' + $user.TrimEnd(';'))
}

# winget 安装；返回 winget 退出码（0/已装类码视为通过，最终以验证函数为准）
function Install-WingetPkg([string]$Id, [string[]]$Extra = @()) {
  Log "---- winget install $Id ----"
  $a = @('install','--id',$Id,'-e','--source','winget',
         '--accept-source-agreements','--accept-package-agreements',
         '--disable-interactivity')
  if ($Extra.Count -gt 0) { $a += $Extra }
  & $Winget @A
  $code = $LASTEXITCODE
  Log "winget $Id 退出码 = $code"
  Refresh-Path
  return $code
}

# 可执行文件 + 版本输出双证据
function Test-Exe([string]$Exe, [string]$VersionArg = '--version') {
  if (-not (Test-Path $Exe)) { return $null }
  try {
    $v = & $Exe $VersionArg 2>$null | Select-Object -First 1
    if ($v) { return ([string]$v).Trim() }
  } catch {}
  return $null
}

# 用已知路径或 PATH 解析可执行文件
function Resolve-Exe([string]$Name, [string[]]$KnownPaths) {
  foreach ($p in $KnownPaths) {
    if ($p -and (Test-Path $p)) { return $p }
  }
  $c = Get-Command $Name -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  return $null
}

if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Log '========== 红楼读析 开发环境安装开始 =========='
Log ("是否管理员: " + ((New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)))

# 0) 执行策略（CurrentUser，无需管理员）
try {
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  Log '执行策略已设置: CurrentUser = RemoteSigned'
} catch { Log "执行策略设置失败: $($_.Exception.Message)" }

if (-not (Test-Path $Winget)) {
  Log '致命: winget 不存在，请先从 Microsoft Store 安装“应用安装程序 App Installer”'
  exit 2
}
Log "winget: $Winget"

# ---------------------------------------------------------------
# 1) Python 3.12（用户级安装，免 UAC）
# ---------------------------------------------------------------
$pyCandidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
)
$python = Resolve-Exe 'python' $pyCandidates
if ($python) {
  $ver = & $python --version 2>&1
  Log "Python 已存在，跳过安装: $python -> $ver"
} else {
  Install-WingetPkg 'Python.Python.3.12' @('--scope','user','--silent') | Out-Null
  Start-Sleep -Seconds 3
  Refresh-Path
  $python = Resolve-Exe 'python' $pyCandidates
  if (-not $python) {
    # winget 可能装成机器级，补几个常见位置
    $python = Resolve-Exe 'python' @(
      'C:\Program Files\Python312\python.exe',
      'C:\Program Files\Python313\python.exe')
  }
  $ver = if ($python) { & $python --version 2>&1 } else { '未找到' }
  Log "Python 安装后验证: $python -> $ver"
}
$script:Result['Python'] = if ($python) { "$python :: $(& $python --version 2>&1)" } else { 'FAILED' }

# ---------------------------------------------------------------
# 2) Rust rustup（用户级，免 UAC）
# ---------------------------------------------------------------
$cargoHome = "$env:USERPROFILE\.cargo"
$cargoExe  = "$cargoHome\bin\cargo.exe"
if (Test-Path $cargoExe) {
  Log "Rust 已存在，跳过安装: $cargoExe -> $(Test-Exe $cargoExe)"
} else {
  Install-WingetPkg 'Rustlang.Rustup' @('--scope','user') | Out-Null
  Start-Sleep -Seconds 3
  Refresh-Path
  # rustup 的 winget 包有时只放 rustup.exe，需确保 default toolchain
  if (Test-Path "$cargoHome\bin\rustup.exe") {
    Log 'rustup 初始化 default stable (msvc)...'
    & "$cargoHome\bin\rustup.exe" default stable-x86_64-pc-windows-msvc 2>&1 | ForEach-Object { Log "rustup: $_" }
  }
}
$script:Result['Cargo'] = if (Test-Path $cargoExe) { Test-Exe $cargoExe } else { 'FAILED' }
$rustcExe = "$cargoHome\bin\rustc.exe"
$script:Result['Rustc'] = if (Test-Path $rustcExe) { Test-Exe $rustcExe } else { 'FAILED (需 MSVC 链接器后才能编译)' }

# ---------------------------------------------------------------
# 3) Node.js LTS（MSI 机器级，会弹一次 UAC，请点“是”）
# ---------------------------------------------------------------
$nodeCandidates = @('C:\Program Files\nodejs\node.exe', "$env:LOCALAPPDATA\Programs\nodejs\node.exe")
$node = Resolve-Exe 'node' $nodeCandidates
if ($node) {
  Log "Node 已存在，跳过安装: $node -> $(Test-Exe $node)"
} else {
  Log '=== 注意：接下来可能弹出 UAC 用户账户控制，请点“是” ==='
  Install-WingetPkg 'OpenJS.NodeJS.LTS' @('--silent') | Out-Null
  Start-Sleep -Seconds 3
  Refresh-Path
  $node = Resolve-Exe 'node' $nodeCandidates
}
$script:Result['Node'] = if ($node) { "$node :: $(Test-Exe $node)" } else { 'FAILED' }
$npmCandidates = @('C:\Program Files\nodejs\npm.cmd', "$env:LOCALAPPDATA\Programs\nodejs\npm.cmd")
$npm = Resolve-Exe 'npm.cmd' $npmCandidates
$script:Result['npm']  = if ($npm) { Test-Exe $npm } else { 'FAILED' }

# ---------------------------------------------------------------
# 4) MSVC C++ Build Tools + Windows SDK（约 3GB，UAC，最慢）
# ---------------------------------------------------------------
$vsWhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
$msvcOk  = $false
if (Test-Path $vsWhere) {
  $inst = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -latest -property installationPath 2>$null
  if ($inst) { $msvcOk = $true; Log "MSVC C++ Build Tools 已存在: $inst" }
}
if ($SkipBuildTools) {
  Log '已指定 -SkipBuildTools，跳过 MSVC Build Tools'
  $script:Result['MSVC'] = 'SKIPPED'
} elseif ($msvcOk) {
  $script:Result['MSVC'] = $inst
} else {
  Log '=== 安装 MSVC C++ Build Tools（约 3GB，UAC 可能再弹一次，请点“是”）==='
  $override = '--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --includeRecommended'
  Install-WingetPkg 'Microsoft.VisualStudio.2022.BuildTools' @('--override', $override) | Out-Null
  if (Test-Path $vsWhere) {
    $inst = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -latest -property installationPath 2>$null
    $script:Result['MSVC'] = if ($inst) { $inst } else { '安装命令已结束但未检测到 VCTools（建议重启后重跑本脚本）' }
  } else {
    $script:Result['MSVC'] = 'vswhere 仍不存在，安装可能被取消或失败'
  }
}

# ---------------------------------------------------------------
# 5) 项目 venv + 档A/档B 依赖（jieba + LLM；V1.0 改 stdio，不装 FastAPI）
# ---------------------------------------------------------------
if ($SkipVenv) {
  Log '已指定 -SkipVenv，跳过 venv'
} elseif (-not $python) {
  Log 'Python 不可用，跳过 venv'
} else {
  $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
  if (-not (Test-Path $venvPy)) {
    Log "创建 venv 于同步目录外: $VenvDir"
    New-Item -ItemType Directory -Force -Path (Split-Path $VenvDir) | Out-Null
    & $python -m venv $VenvDir 2>&1 | ForEach-Object { Log "venv: $_" }
  } else { Log 'venv 已存在（同步目录外）' }
  if (Test-Path $venvPy) {
    Log '升级 pip 并按 requirements.txt 安装依赖 ...'
    $indexArgs = if ($UseOfficialPypi) { @() } else { @('-i','https://pypi.tuna.tsinghua.edu.cn/simple') }
    & $venvPy -m pip install --upgrade pip @indexArgs 2>&1 | ForEach-Object { Log "pip: $_" }
    $reqFile = Join-Path $ProjectRoot 'requirements.txt'
    if (Test-Path $reqFile) {
      & $venvPy -m pip install -r $reqFile @indexArgs 2>&1 | ForEach-Object { Log "pip: $_" }
    } else {
      & $venvPy -m pip install jieba openai jinja2 pydantic python-dotenv loguru @indexArgs 2>&1 | ForEach-Object { Log "pip: $_" }
    }
    $jb = & $venvPy -c "import jieba, sys; print('jieba', jieba.__version__ if hasattr(jieba,'__version__') else 'ok', '| py', sys.version.split()[0])" 2>&1
    Log "venv 依赖验证: $jb"
    $script:Result['venv+jieba'] = [string]$jb
  }
}

# ---------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------
Log '========== 安装结果汇总 =========='
foreach ($k in $script:Result.Keys) {
  Log ("{0,-12} : {1}" -f $k, $script:Result[$k])
}
Log '========== 结束 =========='
