# install_fix_python_rust.ps1
# ASCII-only to avoid PS5.1 encoding issues.
# Fixes Python (ghost ARP -> --force) and Rustup (drop --scope user), then venv+pip.
$ErrorActionPreference = 'Continue'
$ProjectRoot = 'a:\HuaweiMoveData\Users\代\Desktop\gitee\test\红楼梦范例'
$VenvDir = Join-Path $env:USERPROFILE '.venvs\honglou'   # OUTSIDE the synced folder
$LogFile = Join-Path $PSScriptRoot 'install_fix.log'
$Winget = "$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe"
$cargoHome = "$env:USERPROFILE\.cargo"

function Log([string]$m) { $l='[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'),$m; Write-Host $l; Add-Content $LogFile $l -Encoding UTF8 }
function Refresh-Path {
  $m=[Environment]::GetEnvironmentVariable('Path','Machine'); $u=[Environment]::GetEnvironmentVariable('Path','User')
  $env:PATH=($m.TrimEnd(';')+';'+$u.TrimEnd(';'))
}
if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Log '==== fix python + rust start ===='

# ---------- 1) Python 3.12 : force reinstall (ghost ARP points to missing B:\pytest) ----------
$pyCand = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
            'C:\Program Files\Python312\python.exe',
            "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
            'C:\Program Files\Python313\python.exe')
$python = ($pyCand | Where-Object { Test-Path $_ } | Select-Object -First 1)
if ($python) { Log "python already real: $python" }
else {
  Log 'winget --force Python.Python.3.12 ...'
  & $Winget install --id Python.Python.3.12 -e --source winget --force `
     --accept-source-agreements --accept-package-agreements --silent 2>&1 | ForEach-Object { Log "py: $_" }
  Log ("python winget exit=" + $LASTEXITCODE)
  Start-Sleep 3; Refresh-Path
  $python = ($pyCand | Where-Object { Test-Path $_ } | Select-Object -First 1)
  if (-not $python) {
    $c = Get-Command python -ErrorAction SilentlyContinue
    if ($c) { $python = $c.Source }
  }
}
if ($python) { Log ("PYTHON OK: " + (& $python --version 2>&1)) } else { Log 'PYTHON FAILED' }

# ---------- 2) Rustup : no --scope (manifest scope=Unknown) ----------
if (Test-Path "$cargoHome\bin\cargo.exe") { Log 'cargo already present' }
else {
  Log 'winget Rustlang.Rustup (no scope) ...'
  & $Winget install --id Rustlang.Rustup -e --source winget `
     --accept-source-agreements --accept-package-agreements --silent 2>&1 | ForEach-Object { Log "rustup: $_" }
  Log ("rustup winget exit=" + $LASTEXITCODE)
  Start-Sleep 3; Refresh-Path
  $ru = "$cargoHome\bin\rustup.exe"
  if (Test-Path $ru) {
    Log 'install stable-x86_64-pc-windows-msvc toolchain ...'
    & $ru default stable-x86_64-pc-windows-msvc 2>&1 | ForEach-Object { Log "tc: $_" }
  } else {
    $c = Get-Command rustup -ErrorAction SilentlyContinue
    if ($c) { Log ("rustup on PATH: " + $c.Source); & $c.Source default stable-x86_64-pc-windows-msvc 2>&1 | ForEach-Object { Log "tc: $_" } }
    else { Log 'RUSTUP NOT FOUND' }
  }
}
if (Test-Path "$cargoHome\bin\cargo.exe") { Log ("CARGO OK: " + (& "$cargoHome\bin\cargo.exe" --version 2>&1)) } else { Log 'CARGO MISSING' }

# ---------- 3) venv + pip deps ----------
if ($python) {
  $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
  if (-not (Test-Path $venvPy)) {
    Log ("creating venv at " + $VenvDir)
    New-Item -ItemType Directory -Force -Path (Split-Path $VenvDir) | Out-Null
    & $python -m venv $VenvDir 2>&1 | ForEach-Object { Log "venv: $_" }
  } else { Log 'venv exists (outside sync folder)' }
  if (Test-Path $venvPy) {
    Log 'pip install (tsinghua mirror) ...'
    & $venvPy -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | ForEach-Object { Log "pip: $_" }
    & $venvPy -m pip install -r (Join-Path $ProjectRoot 'requirements.txt') -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | ForEach-Object { Log "pip: $_" }
    $chk = & $venvPy -c "import jieba,sys;print('jieba ok | py',sys.version.split()[0])" 2>&1
    Log ("VENV CHECK: " + $chk)
  }
}
Log '==== fix python + rust done ===='
