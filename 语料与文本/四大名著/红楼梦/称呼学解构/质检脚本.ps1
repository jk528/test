# ============================================================
# 《红楼梦》称呼学解构工程 · 生成前验证脚本 v2
# 固化：2026-11-25（001–024 全量审订后）；已接入 .githooks/pre-commit
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File "语料与文本\四大名著\红楼梦\称呼学解构\质检脚本.ps1"
# 退出码：0＝通过；1＝未通过（须修复后再提交）
# 检查：①结构六节 ②计数守恒（含 4b 行）③零宽/错字 ④引文底本锚定（码点归一化，
#       剥离标点/空白/不可见字符/私用区字符——底本 019 含隐形 U+E02D）⑤尾注与引用
# ============================================================
$ErrorActionPreference='Stop'
$proj = Split-Path -Parent $MyInvocation.MyCommand.Path
$hlm  = Split-Path -Parent $proj
$splitDir = Join-Path $hlm '红楼梦_拆分'
$nieqDir  = Join-Path $hlm '名词列锦章节'
$enc = [System.Text.Encoding]::UTF8

function Norm([string]$s){
  $sb = New-Object System.Text.StringBuilder
  foreach($ch in $s.ToCharArray()){
    $c = [int]$ch
    if($c -lt 0x20){ continue }
    if($c -eq 0x20 -or $c -eq 0x3000 -or $c -eq 0xA0){ continue }
    if($c -eq 0xAD -or $c -eq 0x180E -or $c -eq 0xFEFF){ continue }
    if(($c -ge 0x200B -and $c -le 0x200F) -or ($c -ge 0x202A -and $c -le 0x202E) -or ($c -ge 0x2060 -and $c -le 0x2064)){ continue }
    if(($c -ge 0xE000 -and $c -le 0xF8FF) -or ($c -ge 0xFE00 -and $c -le 0xFE0F)){ continue }
    if(($c -ge 0x21 -and $c -le 0x2F) -or ($c -ge 0x3A -and $c -le 0x40) -or ($c -ge 0x5B -and $c -le 0x60) -or ($c -ge 0x7B -and $c -le 0x7E)){ continue }
    if(($c -ge 0x2010 -and $c -le 0x2027) -or $c -eq 0xB7){ continue }
    if($c -ge 0x3001 -and $c -le 0x303F){ continue }
    if($c -ge 0xFF01 -and $c -le 0xFF0F){ continue }
    if($c -ge 0xFF1A -and $c -le 0xFF20){ continue }
    if($c -ge 0xFF3B -and $c -le 0xFF40){ continue }
    if($c -ge 0xFF5B -and $c -le 0xFF65){ continue }
    [void]$sb.Append($ch)
  }
  $sb.ToString()
}

$src=@{}
Get-ChildItem -LiteralPath $splitDir -Filter '*.txt' | ForEach-Object {
  $src[$_.Name.Substring(0,3)] = Norm ([System.IO.File]::ReadAllText($_.FullName,$enc))
}
$nq=@{}
Get-ChildItem -LiteralPath $nieqDir -Filter '*.md' | ForEach-Object {
  $nq[$_.Name.Substring(0,3)] = Norm ([System.IO.File]::ReadAllText($_.FullName,$enc))
}

$fail=0; $sumDecl=0; $totalQ=0; $totalMiss=0
foreach($f in (Get-ChildItem -LiteralPath $proj -Filter '*.md' | Sort-Object Name)){
  if($f.Name -match '^(\d{3})_'){ $num=$Matches[1] } else { continue }
  $c = [System.IO.File]::ReadAllText($f.FullName,$enc)
  $iss=@()
  foreach($sec in 0..5){ if($c -notmatch ("(?m)^##\s*"+$sec+"\s*\.")){ $iss+=("缺§"+$sec) } }
  $rows=[regex]::Matches($c,'(?m)^\|\s*\*{0,2}(\d+b?)\*{0,2}\s*\|').Count
  $decl=0; if($c -match '本回解构\s*(\d+)\s*件'){ $decl=[int]$Matches[1] }
  $sumDecl+=$decl
  if($decl -lt 1 -or $decl -ne $rows){ $iss+=("计数不符(声明$decl/表行$rows)") }
  $d2=0; if($c -match '重点解构\s*(\d+)\s*段'){ $d2=[int]$Matches[1] }
  $h3=[regex]::Matches($c,'(?m)^###\s').Count
  if($d2 -and $d2 -ne $h3){ $iss+=("解构段不符(声明$d2/实际$h3)") }
  if($c -notmatch '(?m)^>\s*AI生成\s*$'){ $iss+='缺AI尾标' }
  if($c -notmatch '（注：'){ $iss+='缺注块' }
  if($c -match '（(\d+)/120）'){
    if([int]$Matches[1] -ne [int]$num){ $iss+=("头标回号错("+$Matches[1]+")") }
  } else { $iss+='头标120缺' }
  if($c -notmatch '【A】'){ $iss+='缺【A】锚' }
  $zw=[regex]::Matches($c,'[\u200B-\u200F\u202A-\u202E\uFEFF]').Count
  if($zw -gt 0){ $iss+=("零宽×"+$zw) }
  $yc=[regex]::Matches($c,'诒').Count
  if($yc -gt 0){ $iss+=("错字诒×"+$yc) }
  if(($c -notmatch ("红楼梦_拆分/"+$num+"_")) -and ($c -notmatch '全文精读复核待作')){ $iss+='底本引用缺' }
  $qm=@(); $s0=$src[$num]; $n0=$nq[$num]; $qi=0
  foreach($q in [regex]::Matches($c,'「([^「」]+)」')){
    $qi++
    foreach($seg in ($q.Groups[1].Value -split '……|＋|——|—')){
      $nf = Norm $seg
      if($nf.Length -lt 12){ continue }
      $totalQ++
      if($s0 -and $s0.Contains($nf)){ continue }
      if($n0 -and $n0.Contains($nf)){ continue }
      $fnd=@()
      foreach($k in $src.Keys){ if($k -ne $num -and $src[$k].Contains($nf)){ $fnd+=$k } }
      $totalMiss++
      if($fnd.Count -gt 0){ $qm+=("["+$qi+"→"+($fnd -join ',')+"]"+$nf.Substring(0,[Math]::Min(20,$nf.Length))) }
      else{ $qm+=("["+$qi+"×]"+$nf.Substring(0,[Math]::Min(20,$nf.Length))) }
    }
  }
  if($iss.Count -gt 0 -or $qm.Count -gt 0){
    $fail++
    Write-Output ("[FAIL] {0} ▶ {1}" -f $f.Name, ($iss -join '；'))
    if($qm.Count -gt 0){ Write-Output ("       QMISS: "+($qm -join '｜')) }
  }
}
Write-Output ("声明事件总数＝{0}（须与 README 批次表累计一致）" -f $sumDecl)
Write-Output ("引文片段＝{0}；未锚定＝{1}" -f $totalQ,$totalMiss)
if(($fail -gt 0) -or ($totalMiss -gt 0)){
  Write-Output '=== 质检未通过：请修复上述问题后重试 ==='
  exit 1
}
Write-Output '=== 质检通过：结构／计数守恒／字符／引文锚定 全部 OK ==='
exit 0
