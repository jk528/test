# ============================================================
# 称呼学解构工程 · 审计扫描脚本 v1（工作流包）
# 功能：关键词密度扫描法执行器——筛"漏收候选句"（含≥2 称谓关键词
#       且归一化后未出现在该回工程文档中的底本句子）。
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File "本脚本路径" `
#     -ProjectDir "四大名著\红楼梦\称呼学解构" `
#     -Chapters "043,044,045,046" [-TopN 12]
#   -Chapters 支持：逗号列表 "043,045" 或区间 "043-046" 或混合 "001-008,011"。
# 输出：每回"含≥2关键词句 X，已覆盖 Y，未覆盖 Z"＋前 TopN 条候选样本。
# 定位：审计兜底（不能替代精读——纯叙事里的称谓关系变化扫不到）。
#       候选需人工过滤：剔场景句/已收事件的引文层，真事件按 Nb 规则补入。
# 移植：其他名著改 $kw 关键词表（如三国加"主公/军师/都督/贤弟"）与
#       -SplitName 参数；目录约定与 03 质检脚本相同（工程与拆分目录同父级）。
# ============================================================
param(
  [string]$ProjectDir = '',
  [string]$Chapters   = '',
  [string]$SplitName  = '红楼梦_拆分',
  [int]$TopN          = 12
)
$ErrorActionPreference = 'Stop'

if(-not $ProjectDir -or -not $Chapters){
  Write-Output '用法：-ProjectDir <工程目录> -Chapters <回号列表，如 "043-046" 或 "043,044">'
  exit 1
}
if(-not (Test-Path -LiteralPath $ProjectDir)){ Write-Output "工程目录不存在：$ProjectDir"; exit 1 }
$proj = (Resolve-Path -LiteralPath $ProjectDir).Path
$splitDir = Join-Path (Split-Path -Parent $proj) $SplitName
if(-not (Test-Path -LiteralPath $splitDir)){ Write-Output "拆分底本目录不存在：$splitDir"; exit 1 }

# 回号解析：支持 "043-046" 区间与 "043,044" 列表混合
$nums=@()
foreach($part in ($Chapters -split '[,，]')){
  $p=$part.Trim()
  if(-not $p){ continue }
  if($p -match '^(\d{1,3})-(\d{1,3})$'){
    $a=[int]$Matches[1]; $b=[int]$Matches[2]
    if($a -gt $b){ $t=$a;$a=$b;$b=$t }
    for($i=$a;$i -le $b;$i++){ $nums += ('{0:D3}' -f $i) }
  } elseif($p -match '^\d{1,3}$'){
    $nums += ('{0:D3}' -f ([int]$p))
  } else {
    Write-Output "忽略无法解析的回号段：$p"
  }
}
if($nums.Count -eq 0){ Write-Output '未解析出任何回号'; exit 1 }

# 称谓关键词表（红楼梦版；移植他著时替换/增补）
$kw = @(
 '爷','奶奶','姑娘','嫂','太太','夫人','小姐','哥儿','丫头','小厮','老爷',
 '浑名','表字','小名','姨娘','舅舅','姨妈','姐姐','妹妹','哥哥','兄弟',
 '老太太','婆子','嬷嬷','媳妇','奴才','小子','亲家','老先生','学生','先生',
 '姊妹','婶子','婶娘','侄儿','孙子','外甥','大爷','二爷','三爷','母亲','父亲',
 '娘儿们','和尚','菩萨','天王','令郎','老货','妈妈','孙女','姑爷','姑奶奶',
 '老老','姥姥','婶子','姨太太','小老婆','公子','王孙','妃子','供奉','妞儿',
 '姐儿','舅爷','凤凰','魔星','姊妹们','娘娘'
)

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
    if($c -ge 0xFF01 -and $c -le 0xFF65){ continue }
    [void]$sb.Append($ch)
  }
  $sb.ToString()
}

foreach($num in $nums){
  $srcFile = Get-ChildItem -LiteralPath $splitDir | Where-Object { $_.Name -like "$num*" } | Select-Object -First 1
  if(-not $srcFile){ Write-Output "===== $num 未找到底本文件，跳过 ====="; continue }
  $txt = [System.IO.File]::ReadAllText($srcFile.FullName,$enc)
  $docFile = Get-ChildItem -LiteralPath $proj | Where-Object { $_.Name -match "^$num" -and $_.Name -match '\.md$' } | Select-Object -First 1
  if(-not $docFile){ Write-Output "===== $num 工程文档不存在，跳过 ====="; continue }
  $docNorm = Norm ([System.IO.File]::ReadAllText($docFile.FullName,$enc))

  $sents = $txt -split '[。！？\n]'
  $total=0; $covered=0; $uncov=0; $out=@()
  foreach($s in $sents){
    $sn = Norm $s
    if($sn.Length -lt 8){ continue }
    $hc=0
    foreach($k in $kw){ if($sn.Contains($k)){ $hc++ } }
    if($hc -ge 2){
      $total++
      if($docNorm.Contains($sn)){ $covered++ } else { $uncov++; $out += $s.Trim() }
    }
  }
  Write-Output ("===== $num 含>=2关键词句 $total，已覆盖 $covered，未覆盖 $uncov =====")
  if($out.Count -gt 0){
    Write-Output ("-- 前 $TopN 条候选（需人工核对底本后过滤）：")
    $out | Select-Object -First $TopN | ForEach-Object {
      Write-Output ("[候选] " + $_.Substring(0,[Math]::Min(55,$_.Length)))
    }
  }
}
Write-Output '=== 审计扫描完成：候选句须经人工核对底本语境过滤（剔除场景句/已收事件引文层），真事件按 Nb 规则补入，补后重跑 03 质检 ==='
exit 0
