# Shell / PowerShell / CMD 的区别、后缀名文件及快捷打开方式

> 整理日期：2026-10-25
> 适用系统：Windows 10 / Windows 11（Shell 概念涵盖 macOS / Linux）

---

## 目录

- [一、基本概念](#一基本概念)
- [二、三者核心区别对比](#二三者核心区别对比)
- [三、详细差异说明](#三详细差异说明)
- [四、后缀名（脚本文件扩展名）](#四后缀名脚本文件扩展名)
- [五、快捷打开方式](#五快捷打开方式)
- [六、定时任务查询与任务计划程序](#六定时任务查询与任务计划程序)
- [七、权限查询与切换（提权）](#七权限查询与切换提权)
- [八、变量、作用域与空值](#八变量作用域与空值)
- [九、如何选择](#九如何选择)

---

## 一、基本概念

先理清三者的关系：**Shell 是「壳」，CMD 和 PowerShell 是具体的壳实现。**

| 名称 | 概念层级 | 一句话说明 |
|------|---------|-----------|
| **Shell（壳）** | 总概念 | 任何「接收用户命令 → 调用操作系统内核执行 → 返回结果」的命令行解释程序统称。Shell 不是某一个具体软件，而是一类程序。常见 Shell 有 CMD、PowerShell、Bash、Zsh、Fish 等 |
| **CMD（命令提示符）** | 具体 Shell | Windows 时代从 MS-DOS 沿袭而来的传统命令行 Shell，处理纯文本 |
| **PowerShell** | 具体 Shell | 微软推出的现代化、面向对象的自动化 Shell，基于 .NET，处理结构化对象 |

> 类比：如果把操作系统比作「电脑」，Shell 就是「显示器+键鼠」这个交互层总称；CMD 是老式 CRT 显示器，PowerShell 是 4K 触控显示器。

---

## 二、三者核心区别对比

### 2.1 Shell 大类对比（CMD、PowerShell、Bash）

| 对比维度 | CMD | PowerShell | Bash（Linux/macOS 默认 Shell） |
|---------|-----|-----------|-------------------------------|
| 所属系统 | Windows 自带 | Windows 自带（7+ 跨平台） | Linux / macOS 自带 |
| 首次发布 | 1987 年 | 2006 年 | 1989 年 |
| 输出类型 | 纯文本 | .NET 对象 | 纯文本（字符串流） |
| 脚本扩展名 | .bat / .cmd | .ps1 | .sh |
| 脚本语言 | 批处理（语法简陋） | PowerShell 脚本语言（完整） | Bash 脚本语言（完整） |
| 命令风格 | DOS 命令（dir、copy） | Cmdlet（Get-Process 等） | Unix 命令（ls、cp） |
| 管道传递 | 文本 | 对象 | 文本 |
| 远程管理 | 不支持 | 原生支持（WinRM） | 通过 SSH |
| 跨平台 | 否 | 是（7+） | 是 |
| 当前状态 | 维护，不再更新 | 持续更新 | 持续更新 |

### 2.2 CMD vs PowerShell 核心差异

| 对比维度 | CMD（命令提示符） | PowerShell |
|---------|------------------|------------|
| 首次发布 | 1987 年（MS-DOS 时代沿袭） | 2006 年（PowerShell 1.0） |
| 本质定位 | 传统命令行解释器 | 面向对象的自动化 Shell + 脚本平台 |
| 输出类型 | 纯文本 | .NET 对象（可传递属性与方法） |
| 脚本能力 | 批处理（.bat / .cmd），功能弱 | .ps1 脚本，支持函数、模块、异常处理 |
| 命令体系 | DOS 命令（dir、copy 等） | Cmdlet（动词-名词，如 Get-Process），兼容大部分 DOS 命令别名 |
| 管道机制 | 传递文本流 | 传递结构化对象 |
| 跨平台 | 仅 Windows | PowerShell 7+ 支持 Windows / Linux / macOS |
| 注册表/WMI 操作 | 不支持或极弱 | 原生支持（注册表可当作磁盘浏览） |
| 远程管理 | 不支持 | 原生支持（Enter-PSSession、Invoke-Command） |
| 默认颜色 | 黑底白字 | 蓝底白字（经典版 5.1） |
| 当前状态 | 维护模式，不再新增功能 | 持续更新（PowerShell 7.x 为现代版本） |

---

## 三、详细差异说明

### 1. 对象 vs 文本

CMD 中管道传递的是纯文本，需要靠字符串解析提取信息；PowerShell 传递的是 .NET 对象，可直接按属性筛选：

```powershell
# PowerShell：找出内存占用超过 500MB 的进程
Get-Process | Where-Object { $_.WorkingSet -gt 500MB } | Sort-Object WorkingSet -Descending
```

同样的需求在 CMD 中几乎无法简洁实现。

### 2. 命令命名规范

PowerShell 命令遵循「动词-名词」规范，可读性强：

| 操作 | CMD | PowerShell | Bash |
|------|-----|-----------|------|
| 查看目录 | `dir` | `Get-ChildItem`（别名 `ls` / `dir`） | `ls` |
| 复制文件 | `copy` | `Copy-Item`（别名 `cp`） | `cp` |
| 查看内容 | `type` | `Get-Content`（别名 `cat`） | `cat` |
| 删除文件 | `del` | `Remove-Item`（别名 `rm`） | `rm` |
| 结束进程 | `taskkill /im xx.exe` | `Stop-Process -Name xx` | `kill` / `pkill` |

### 3. 语法差异踩坑点（Windows 下最常见）

| 场景 | CMD 写法 | PowerShell 写法 | 说明 |
|------|---------|----------------|------|
| 重定向输入 | `mysql < db.sql` | `Get-Content db.sql \| mysql` | PowerShell 不支持 `<` 输入重定向 |
| 调用外部程序 | `"C:\Program Files\node.exe" app.js` | `& "C:\Program Files\node.exe" app.js` | 含空格路径需用调用运算符 `&` |
| 网络请求 | `curl http://x` | `Invoke-WebRequest` / `curl.exe` | PowerShell 中 `curl` 是 `Invoke-WebRequest` 别名，参数不兼容 |
| 路径分隔符 | 反斜杠 `\` | 正斜杠 `/` 或反斜杠 `\` 均可 | PowerShell 两种都支持 |
| 变量引用 | `%VAR%` | `$VAR` 或 `${VAR}` | 语法完全不同 |
| 注释 | `:: remark` 或 `rem remark` | `# comment` | PowerShell 用 `#` |

### 4. 脚本能力

- **CMD 批处理**：适合简单的顺序命令执行，变量、判断、循环语法简陋。
- **PowerShell 脚本**：支持函数、模块、try/catch、类、远程执行、调用 .NET 类库，可调用 COM、WMI、注册表、文件系统等一切系统资源。
- **Bash 脚本**：Linux 世界的主力脚本语言，语法成熟，配合 grep/awk/sed 文本处理能力极强。

### 5. 版本说明

| 版本 | 说明 |
|------|------|
| Windows PowerShell 5.1 | Windows 10/11 系统自带，蓝底窗口，仅支持 Windows |
| PowerShell 7.x（pwsh） | 现代跨平台版本，需单独安装，黑底窗口，性能更强 |

---

## 四、后缀名（脚本文件扩展名）

不同 Shell 对应不同的脚本文件扩展名，系统通过扩展名或文件头（Shebang）识别脚本类型。

### 4.1 各 Shell 对应扩展名

| Shell | 脚本扩展名 | 可执行文件扩展名 | 说明 |
|-------|-----------|----------------|------|
| CMD | `.bat`、`.cmd` | `.bat`、`.cmd` | 两者几乎等价，`.cmd` 是较新的命名 |
| PowerShell | `.ps1` | `.ps1` | 模块文件用 `.psm1`，模块清单用 `.psd1` |
| Bash | `.sh` | `.sh`（或无扩展名） | 通过文件头 `#!/bin/bash` 识别 |
| 其他 Unix Shell | `.sh`、`.zsh`、`.fish` | 同脚本扩展名 | Zsh / Fish 等现代 Shell |

### 4.2 Windows 下相关后缀详解

| 扩展名 | 全称 | 说明 |
|--------|------|------|
| `.bat` | Batch（批处理） | 源自 MS-DOS，最古老的 Windows 批处理脚本格式，由 CMD 解释执行 |
| `.cmd` | Command | Windows NT 时代引入的批处理脚本，与 `.bat` 几乎等价，但有少量行为差异（如 `ERRORLEVEL` 处理） |
| `.ps1` | PowerShell Script | PowerShell 脚本，默认双击会用记事本打开而非执行（安全策略），需在 PowerShell 中运行 |
| `.psm1` | PowerShell Module | PowerShell 模块文件，封装函数、Cmdlet 供其他脚本 import |
| `.psd1` | PowerShell Data / Module Manifest | 模块清单文件，描述模块元数据（版本、依赖等） |
| `.ps1xml` | PowerShell XML | PowerShell 类型/格式扩展定义文件 |
| `.exe` | Executable | 可执行二进制文件，与 Shell 无关，但常由 Shell 调用 |
| `.com` | Command | 老式 DOS 可执行文件格式，现今少见 |

### 4.3 运行方式对照

| 脚本类型 | 运行方式 |
|---------|---------|
| `.bat` / `.cmd` | 直接双击，或在 CMD/PowerShell 中输入路径执行 |
| `.ps1` | 在 PowerShell 中执行 `.\script.ps1`（需满足执行策略），或右键 → 用 PowerShell 运行 |
| `.sh` | 在 WSL / Linux / macOS 中 `bash script.sh` 或 `./script.sh`（需可执行权限） |

### 4.4 PowerShell 执行策略（运行 .ps1 常见坑）

默认情况下 Windows 禁止运行 `.ps1` 脚本，需先设置执行策略：

```powershell
# 查看当前执行策略
Get-ExecutionPolicy

# 设置为允许本地脚本运行（推荐，仅需执行一次）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

| 策略 | 说明 |
|------|------|
| `Restricted` | 默认，禁止任何脚本运行 |
| `RemoteSigned` | 本地脚本可运行，网络下载的脚本需签名（推荐） |
| `AllSigned` | 所有脚本必须签名 |
| `Unrestricted` | 全部允许（不推荐） |

---

## 五、快捷打开方式

### 5.1 通用方法（CMD 与 PowerShell 均适用）

| 方法 | 操作步骤 |
|------|---------|
| Win + R 运行框 | 按 `Win + R`，输入 `cmd` 或 `powershell`，回车 |
| 开始菜单搜索 | 按 `Win` 键，输入 `cmd` 或 `powershell`，点击搜索结果 |
| 任务管理器 | `Ctrl + Shift + Esc` 打开任务管理器 → 文件 → 运行新任务 → 输入命令 |
| 地址栏输入法 | 在任意文件夹的资源管理器地址栏输入 `cmd` 或 `powershell`，回车后**以当前路径**打开 |
| Shift + 右键 | 在文件夹空白处按住 `Shift` 右键 → 选择「在此处打开 PowerShell 窗口」（Win10） |

### 5.2 以管理员身份打开

| 方法 | 操作步骤 |
|------|---------|
| 快捷键（推荐） | 按 `Win + X`，再按 `A`（Win10 旧版直接显示；Win11 打开的是终端管理员版） |
| 搜索 + Ctrl Shift Enter | 开始菜单搜索 `cmd` 或 `powershell`，按 `Ctrl + Shift + Enter` 以管理员运行 |
| 右键选项 | 搜索到程序后右键 → 「以管理员身份运行」 |

### 5.3 Windows 11 专属

| 方法 | 操作步骤 |
|------|---------|
| Win + X 菜单 | `Win + X` → 选择「终端」或「终端（管理员）」，默认打开 PowerShell |
| 终端内切换 | 打开 Windows Terminal 后，点击标签页右侧 `∨` 下拉箭头，可切换 PowerShell / CMD / Azure Cloud Shell |
| 右键菜单 | 文件夹空白处右键 → 「在终端中打开」 |

### 5.4 常用快捷键一览

| 快捷键 | 作用 |
|--------|------|
| `Win + R` | 打开运行框 |
| `Win + X` | 打开快速链接菜单（含终端入口） |
| `Ctrl + Shift + Esc` | 打开任务管理器 |
| `Alt + D` | 定位到资源管理器地址栏（配合输入 cmd 使用极佳） |
| `Ctrl + Shift + Enter` | 以管理员身份运行搜索到的程序 |

### 5.5 macOS / Linux 打开 Shell 终端

| 系统 | 打开方式 |
|------|---------|
| macOS | `Cmd + Space` 搜索「终端」或按 `Launchpad → 其他 → 终端` |
| Ubuntu (GNOME) | `Ctrl + Alt + T` |
| KDE | `Ctrl + Alt + T`（可配置） |
| 通用 | 应用菜单搜索「Terminal」 |

---

## 六、定时任务查询与任务计划程序

### 6.1 三者与「任务计划程序」的关系

> **关键结论**：Windows 下的定时任务统一由**任务计划程序（Task Scheduler）**管理，CMD、PowerShell、Bash 都只是「调用方」，本身不具备调度能力。

| 角色 | 说明 |
|------|------|
| 任务计划程序（Task Scheduler） | Windows 内核级定时调度服务，真正负责「到点触发执行」。所有定时任务都登记在这里 |
| CMD | 通过 `schtasks` 命令行工具调用任务计划程序（增删改查） |
| PowerShell | 通过 `ScheduledTasks` 模块（Get-ScheduledTask 等 Cmdlet）调用任务计划程序 |
| Bash（WSL） | WSL 内的 `cron` 与 Windows 任务计划程序是两套独立系统；若要调度 Windows 程序，仍需用 `schtasks` 或 PowerShell |

**类比**：任务计划程序是「闹钟本身」，CMD/PowerShell/Bash 是「设置闹钟的遥控器」。闹钟响不响，由任务计划程序决定。

> 注意：在 WSL 中运行 `cron` 时，cron 任务仅在 WSL 实例运行期间生效；若 Windows 重启后 WSL 未自动启动，cron 不会自动触发。要保证开机即执行，应使用 Windows 任务计划程序。

### 6.2 三者查询定时任务清单的命令

#### CMD —— 使用 `schtasks`

```bat
:: 列出所有定时任务（含任务名、下次运行时间、状态、上次运行结果）
schtasks /query

:: 以表格格式列出所有任务（更紧凑）
schtasks /query /fo TABLE

:: 列出指定任务的详细信息
schtasks /query /tn "任务名" /v

:: 列出所有任务并导出为 CSV
schtasks /query /fo CSV /nh > tasks.csv
```

常用参数：
- `/query`：查询任务
- `/tn "任务名"`：指定任务名
- `/v`：详细信息（verbose）
- `/fo`：输出格式（TABLE / LIST / CSV）
- `/nh`：CSV 模式下不输出表头

#### PowerShell —— 使用 ScheduledTasks 模块（推荐）

```powershell
# 列出所有定时任务的基本信息（任务名、任务路径、状态）
Get-ScheduledTask

# 列出所有任务及其触发器和下次运行时间
Get-ScheduledTask | Select-Object TaskName, State, @{N='NextRunTime';E={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}}

# 查看指定任务的详细信息（触发器、动作、运行账户等）
Get-ScheduledTask -TaskName "任务名" | Format-List *

# 查看任务的运行状态（上次运行时间、结果、下次运行时间）
Get-ScheduledTaskInfo -TaskName "任务名"

# 按状态筛选已禁用的任务
Get-ScheduledTask | Where-Object State -eq 'Disabled'
```

**PowerShell 优势**：可直接拿到结构化对象，能按状态、触发器类型、下次运行时间等字段筛选排序，比 `schtasks` 强大得多。

#### Bash（Linux/macOS / WSL）—— 使用 `crontab` 和 `at`

```bash
# 列出当前用户的 cron 定时任务
crontab -l

# 列出指定用户的 cron 任务（需 root）
crontab -u username -l

# 列出系统级 cron 任务
ls -la /etc/cron.d/
cat /etc/crontab

# 列出 at 队列中的一次性任务
atq

# 查看 systemd timer（现代 Linux 推荐）
systemctl list-timers --all
```

### 6.3 Windows 任务计划程序图形界面查询

| 方式 | 操作 |
|------|------|
| Win + R 运行框 | 输入 `taskschd.msc`，回车 |
| 控制面板 | 控制面板 → 管理工具 → 任务计划程序 |
| 此电脑右键 → 管理 | 计算机管理 → 任务计划程序 → 任务计划程序库 |

打开后左侧树形目录即为所有任务分组，中间列显示任务名、触发器、状态、上次运行结果、下次运行时间。

### 6.4 三者创建定时任务对照

#### CMD —— `schtasks /create`

```bat
:: 每天 9:00 运行脚本
schtasks /create /tn "每日备份" /tr "C:\backup.bat" /sc daily /st 09:00

:: 开机时运行
schtasks /create /tn "开机启动" /tr "C:\start.bat" /sc onstart
```

#### PowerShell —— `Register-ScheduledTask`

```powershell
# 每天 9:00 运行脚本
$action = New-ScheduledTaskAction -Execute "C:\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "每日备份" -Action $action -Trigger $trigger

# 开机时运行（需管理员权限）
$action = New-ScheduledTaskAction -Execute "C:\start.ps1"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "开机启动" -Action $action -Trigger $trigger -RunLevel Highest
```

#### Bash —— `crontab -e`

```bash
# 编辑当前用户的 cron 任务
crontab -e

# 示例：每天 9:00 运行备份脚本
0 9 * * * /home/user/backup.sh
```

### 6.5 实战避坑（来自踩坑经验）

| 坑点 | 说明与解决 |
|------|-----------|
| 创建开机启动任务报「Access is denied」 | `AtStartup` 类型任务需**管理员权限**运行 PowerShell，且使用 `-RunLevel Highest` |
| `.ps1` 脚本在任务计划中不执行 | 任务 Action 的程序应填 `powershell.exe`，参数填 `-ExecutionPolicy Bypass -File "C:\脚本路径.ps1"` |
| 需要重定向日志 `>> log.txt 2>&1` | 任务计划中直接重定向不生效，应把 Action 程序设为 `cmd.exe`，参数设为 `/c "你的命令 >> log.txt 2>&1"` |
| 判断任务是否真的创建成功 | 不要只看脚本输出，要用 `Get-ScheduledTask -TaskName "任务名"` 或 `schtasks /query /tn "任务名"` 实查，并看 `NextRunTime` 和 `LastTaskResult` |
| WSL 的 cron 任务不执行 | 确认 WSL 实例已启动；要开机自启需用 Windows 任务计划程序调用 `wsl -e cron` |
| `LastTaskResult = 0x0` 表示成功，非 0 为失败码 | 对照 Windows 错误码排查 |

### 6.6 一句话总结

- **查询 Windows 定时任务**：CMD 用 `schtasks /query`，PowerShell 用 `Get-ScheduledTask`（更强大），两者查的是同一个「任务计划程序」里的数据。
- **查询 Linux/macOS 定时任务**：用 `crontab -l` 或 `systemctl list-timers`。
- **关系**：Shell 只是操作任务计划程序的工具，真正的调度执行由系统的任务计划服务（Task Scheduler / cron / systemd timer）负责。

---

## 七、权限查询与切换（提权）

### 7.1 权限模型概述

Windows 和类 Unix 系统的权限模型不同，权限获取方式也不同：

| 系统 | 最高权限账户 | 普通用户提权方式 | 权限确认机制 |
|------|------------|----------------|------------|
| Windows | Administrator（管理员） | UAC 弹窗确认 | 用户账户控制（UAC） |
| Linux / macOS | root | `sudo` 命令 | 输入当前用户密码 |

> 关键概念：**「以管理员身份运行」≠「切换到 Administrator 账户」**。在 Windows 上，即使用当前登录的用户本身就是管理员组的成员，默认仍以普通权限运行程序，需要通过 UAC 确认才能提升到管理员权限令牌。

### 7.2 查询当前权限

#### CMD —— 查询当前权限

```bat
:: 查看当前用户所属组（看是否在 Administrators 组）
whoami /groups

:: 查看当前权限令牌（看是否有高完整性级别 High Mandatory Level）
whoami /priv

:: 查看当前登录用户名
whoami

:: 查看是否是管理员（通过访问受限目录判断）
net session >nul 2>&1 && echo 管理员权限 || echo 非管理员权限
```

判断要点：
- `whoami /groups` 输出中若包含 `Mandatory Label\High Mandatory Level`，说明当前是管理员权限
- `net session` 命令普通用户无法执行，可作为管理员权限检测的简易判断

#### PowerShell —— 查询当前权限

```powershell
# 查看当前用户
[System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# 判断当前是否以管理员身份运行（最准确）
$principal = New-Object System.Security.Principal.WindowsPrincipal([System.Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "是否管理员: $isAdmin"

# 一行简化版
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")

# 查看当前进程的完整性级别（Low/Medium/High/System）
whoami /groups | findstr "Mandatory"
```

#### Bash（Linux/macOS）—— 查询当前权限

```bash
# 查看当前用户
whoami

# 查看当前用户 ID 和所属组
id

# 判断是否是 root（uid=0）
id -u   # 输出 0 表示 root

# 查看是否能使用 sudo
sudo -v && echo "有 sudo 权限" || echo "无 sudo 权限"

# 查看 sudo 可执行哪些命令
sudo -l
```

### 7.3 切换/提升权限

#### Windows —— 以管理员身份运行

**方式一：图形界面（最常用）**

| 操作 | 说明 |
|------|------|
| 开始菜单搜索 → 右键程序 → 「以管理员身份运行」 | 单次提权 |
| `Ctrl + Shift + Enter` | 搜索到程序后用此快捷键直接以管理员启动 |
| `Win + X` → `A` | 打开管理员终端（Win11 为终端管理员） |

**方式二：PowerShell 自我提权（脚本内检测并重启）**

```powershell
# 检测当前是否管理员，不是则以管理员身份重新启动自身
$principal = New-Object System.Security.Principal.WindowsPrincipal([System.Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "正在请求管理员权限..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}
Write-Host "已获得管理员权限" -ForegroundColor Green
```

**方式三：CMD 中调用 PowerShell 提权运行**

```bat
:: 从 CMD 提权运行 PowerShell 脚本
powershell -Command "Start-Process powershell -ArgumentList '-File C:\script.ps1' -Verb RunAs"
```

**方式四：runas 命令（需输入管理员密码）**

```bat
:: 以指定管理员账户运行程序（会弹出密码输入框）
runas /user:Administrator cmd.exe

:: 以管理员身份运行脚本
runas /user:Administrator "powershell -File C:\script.ps1"
```

> `runas` 会要求输入目标账户的密码，且不会触发 UAC 静默提权，适合域环境下使用其他账户运行。

#### Linux/macOS —— sudo 提权

```bash
# 以 root 身份执行单条命令
sudo apt install vim

# 以 root 身份启动一个交互式 shell
sudo -i
# 或
sudo su -

# 以其他用户身份执行命令
sudo -u username command

# 临时切换到 root 并保持环境变量
sudo -s

# 免密执行某条命令（需在 /etc/sudoers 配置）
sudo /usr/bin/systemctl restart nginx
```

### 7.4 提权的风险

> **核心原则：权限最小化。能不用管理员权限就不用，必须用的时候用完即降。**

| 风险 | 说明 | 建议 |
|------|------|------|
| **恶意脚本直接控制系统** | 管理员权限下，恶意脚本可修改注册表、安装驱动、加密文件（勒索）、禁用安全软件 | 不运行来路不明的 `.ps1`/`.bat`/`.sh`，执行前先看内容 |
| **误操作不可逆** | 管理员权限下 `rm -rf /`（Linux）或 `Remove-Item -Recurse C:\`（PowerShell）会直接删除系统文件 | 删除前先 `echo` 或加 `-WhatIf` 预览（PowerShell），删除系统盘前务必三思 |
| **环境变量污染** | 管理员 shell 的环境变量、PATH 可能与普通用户不同，导致「在我这能跑在你那不能跑」 | 脚本不要假设管理员环境，显式指定完整路径 |
| **UAC 绕过/被静默** | 被 UAC 弹窗反复确认会让人麻木点击「是」，忽略了实际执行内容 | UAC 弹窗时**先看清楚要运行什么程序**再点确认 |
| **sudo 密码泄露** | 终端中输入的 sudo 密码可能被键盘记录器截获 | 不在公共/不可信机器上使用 sudo；定期更换密码 |
| **定时任务以管理员运行** | 开机启动或定时任务以高权限运行，一旦脚本被篡改 = 系统后门 | 定时任务脚本放在只有管理员可写的目录，定期检查任务列表 |
| **权限滥用留下痕迹风险** | 长期以管理员身份浏览网页、打开文档，恶意宏/漏洞可直接获取系统权限 | 日常操作使用普通权限，仅在安装软件/改系统时提权 |
| **无法回滚的配置更改** | 管理员改了系统服务、防火墙、注册表后，普通用户无法自行恢复 | 改配置前先记录原值或创建系统还原点 |

### 7.5 安全建议清单

- [ ] **不用管理员账户日常登录**：日常用普通用户账户，需要时才提权
- [ ] **脚本执行前审查内容**：尤其从网上复制的 `.ps1`/`.sh`，先 `cat` 看清楚
- [ ] **删除操作先预览**：PowerShell 用 `-WhatIf`，Linux 用 `echo` 模拟
- [ ] **限制 PowerShell 执行策略**：保持 `RemoteSigned`，不要设成 `Unrestricted`
- [ ] **sudo 配置最小化**：`/etc/sudoers` 只给需要的命令，不要给 `ALL`
- [ ] **敏感脚本加签名**：PowerShell 可对 `.ps1` 签名，防止被篡改后执行
- [ ] **定期审计定时任务**：检查是否有可疑的高权限计划任务
- [ ] **UAC 保持默认或最高**：不要关闭 UAC，否则所有程序默认管理员权限

### 7.6 一句话总结

- **查权限**：CMD 用 `whoami /groups` 看完整性级别；PowerShell 用 `WindowsPrincipal.IsInRole` 判断；Bash 用 `id -u`。
- **提权**：Windows 用 UAC/`-Verb RunAs`；Linux/macOS 用 `sudo`。
- **风险**：管理员权限下误操作不可逆、恶意脚本可控制系统，务必遵循「最小权限、用完即降」原则。

---

## 八、变量、作用域与空值

### 8.1 普通用户与管理员的作用域差异

> **核心概念**：用户身份决定了「能访问什么、能改什么」。权限作用域是操作系统层面的边界，而非脚本语言层面。

| 维度 | 普通用户 | 管理员（Administrator/root） |
|------|---------|------------------------------|
| 文件系统访问范围 | 仅自己的用户目录（`C:\Users\xxx`、`/home/xxx`）+ 系统只读目录 | 全部目录可读可写，含系统目录（`C:\Windows`、`/etc`、`/System`） |
| 注册表 | 只能改 `HKCU`（当前用户） | 可改 `HKLM`（本地机器）等所有注册表项 |
| 系统服务 | 只能查看，不能启动/停止/安装 | 可安装、启动、停止、删除任意服务 |
| 进程管理 | 只能操作自己启动的进程 | 可操作所有进程，包括系统进程 |
| 定时任务 | 只能创建/查看自己的任务 | 可创建/查看所有用户的任务 |
| 防火墙/网络 | 不能改防火墙规则、不能监听 1024 以下端口 | 可改防火墙、监听任意端口 |
| 环境变量 | 只能改用户级环境变量 | 可改系统级环境变量（影响所有用户） |

**类比**：普通用户像「租客」，只能动自己房间的东西；管理员像「房东」，可以改整栋楼的水电结构。

### 8.2 作用域（Scope）是什么

**作用域 = 变量/函数/命令在哪些范围内「可见、可访问」。** 超出作用域就访问不到，或者会访问到另一个同名实体。

常见作用域层级（从大到小）：

| 作用域层级 | 说明 | 类比 |
|-----------|------|------|
| 系统级（System） | 所有用户、所有进程都能访问（如系统环境变量 PATH） | 小区公共设施 |
| 用户级（User） | 仅当前登录用户的所有进程可访问（如用户环境变量） | 你家的家具 |
| 进程级（Process） | 仅当前运行的程序可访问 | 你手里的东西 |
| 脚本/会话级（Session） | 仅当前 Shell 窗口/脚本内可访问 | 你口袋里的东西 |
| 函数/局部级（Local） | 仅当前函数/代码块内可访问 | 你手里正握着的东西 |

### 8.3 局部变量 vs 公共（全局）变量

#### 三者对比

| 对比项 | 局部变量（Local） | 公共/全局变量（Global/Environment） |
|--------|------------------|--------------------------------------|
| 定义位置 | 函数内部或脚本内部 | Shell 顶层或用 `export` 导出 |
| 可见范围 | 仅当前函数/脚本 | 当前 Shell 及其子进程 |
| 生命周期 | 函数/脚本结束即销毁 | Shell 窗口关闭才销毁 |
| 跨进程传递 | 不能 | 通过环境变量传递给子进程 |
| 命名风险 | 同名不冲突（作用域隔离） | 全局命名污染，易冲突 |

#### CMD —— 变量作用域

```bat
:: 普通变量（仅当前 CMD 窗口可见）
set MYVAR=hello
echo %MYVAR%

:: 环境变量（全局，子进程可见）
setx MYVAR "hello"
:: 注意：setx 设置后，需新开 CMD 窗口才能生效

:: 批处理脚本内的局部变量（setlocal/endlocal 隔离）
@echo off
setlocal
set TEMP_VAR=inside
echo %TEMP_VAR%   :: 输出 inside
endlocal
echo %TEMP_VAR%   :: 空，因为 setlocal 范围内的变量已销毁

:: 函数内的局部变量（用 setlocal 模拟）
:myFunc
setlocal
set localVar=func
echo %localVar%
endlocal
goto :eof
```

CMD 关键规则：
- `set` 设置的变量只在当前 CMD 窗口有效，关闭即消失
- `setx` 设置的是**用户级**环境变量，持久化到注册表，新开窗口才生效
- `setlocal` / `endlocal` 是批处理中隔离变量的唯一手段

#### PowerShell —— 变量作用域

PowerShell 有**显式的作用域修饰符**，比 CMD 精细得多：

```powershell
# 局部变量（默认，仅当前作用域）
$localVar = "局部"

# 脚本级变量（整个 .ps1 文件内可见）
$script:scriptVar = "脚本级"

# 全局变量（整个 PowerShell 会话可见，跨脚本）
$global:globalVar = "全局"

# 私有变量（仅当前作用域，子作用域不可见也不可改）
$private:privateVar = "私有"

# 环境变量（传给子进程）
$env:MYENV = "环境变量"

# 查看各作用域变量
Get-Variable -Scope Local
Get-Variable -Scope Script
Get-Variable -Scope Global
```

PowerShell 作用域修饰符速查：

| 修饰符 | 范围 |
|--------|------|
| `$local:` | 当前作用域（默认） |
| `$script:` | 当前脚本文件 |
| `$global:` | 整个 PowerShell 会话 |
| `$private:` | 当前作用域，子作用域不可见 |
| `$env:` | 环境变量，传给子进程 |

#### Bash —— 变量作用域

```bash
# 局部变量（仅当前 Shell 会话）
myvar="hello"
echo $myvar

# 环境变量（导出给子进程）
export MYVAR="hello"

# 函数内的局部变量（用 local 关键字）
myfunc() {
    local localVar="函数内局部"
    echo $localVar
}
myfunc
echo $localVar   # 空，local 变量在函数外不可见

# 查看所有环境变量
env
# 或
printenv

# 查看所有变量（含局部）
set

# 删除变量
unset MYVAR
```

Bash 关键规则：
- 不加 `export` 的变量只在当前 Shell 可见，子进程看不到
- `export` 导出的变量会传递给子进程，但子进程改了不会传回父进程
- 函数内用 `local` 声明的变量仅函数内可见

### 8.4 访问空值（未定义变量）的处理

> **核心风险**：访问未定义或为空的变量，可能导致命令参数缺失、路径拼接错误、甚至执行危险操作（如 `rm -rf $DIR/` 当 `$DIR` 为空时变成 `rm -rf /`）。

#### CMD —— 空值处理

```bat
:: 判断变量是否为空
if "%VAR%"=="" (
    echo 变量为空或未定义
) else (
    echo 变量值为: %VAR%
)

:: 安全用法：未定义时给默认值
set VAR=%VAR:-default_value-%

:: 危险示例：变量为空导致路径错误
set DIR=
del %DIR%\*.tmp   :: 变量为空时变成 del \*.tmp，可能误删根目录文件！
```

#### PowerShell —— 空值处理

```powershell
# 判断变量是否为空（$null 或空字符串）
if ($null -eq $var -or $var -eq "") {
    Write-Host "变量为空或未定义"
}

# 安全访问：未定义时给默认值（?? 空合并运算符，PowerShell 7+）
$result = $var ?? "默认值"

# 或用 If 写法（兼容 5.1）
if ($null -eq $var) { $result = "默认值" } else { $result = $var }

# 判断字符串是否为空或空白
if ([string]::IsNullOrWhiteSpace($var)) {
    Write-Host "变量为空、空白或未定义"
}

# 危险示例：变量为空导致删除错误
$dir = $null
Remove-Item "$dir\*.tmp"   # 路径变成 "\*.tmp"，可能误删！
# 安全做法：先检查再操作
if ($dir -and (Test-Path $dir)) {
    Remove-Item "$dir\*.tmp"
}
```

PowerShell 特有的空值类型：

| 空值类型 | 说明 |
|---------|------|
| `$null` | 未定义或显式赋值为 null |
| `""` | 空字符串 |
| `@()` | 空数组 |
| `[string]::Empty` | 等价于 `""` |
| `$null` 属性 | 对象的属性不存在时访问返回 `$null` |

#### Bash —— 空值处理

```bash
# 判断变量是否为空
if [ -z "$VAR" ]; then
    echo "变量为空或未定义"
fi

# 判断变量是否非空
if [ -n "$VAR" ]; then
    echo "变量非空"
fi

# 安全用法：未定义时给默认值
result=${VAR:-default_value}    # VAR 未定义或为空时用 default
result=${VAR-default_value}     # VAR 仅未定义时用 default（为空保留空）

# 危险示例：变量为空导致灾难
DIR=
rm -rf "$DIR/"*   # 变量为空时变成 rm -rf /*，删除根目录所有文件！
# 安全做法：加引号 + 先检查
if [ -n "$DIR" ] && [ -d "$DIR" ]; then
    rm -rf "$DIR"/*
fi
```

Bash 变量默认值语法速查：

| 语法 | 说明 |
|------|------|
| `${VAR:-default}` | VAR 未定义或为空时，返回 default（VAR 不变） |
| `${VAR-default}` | VAR 仅未定义时，返回 default |
| `${VAR:=default}` | VAR 未定义或为空时，返回 default 并赋值给 VAR |
| `${VAR:?error}` | VAR 未定义或为空时，打印 error 并退出脚本 |
| `${VAR:+other}` | VAR 已定义且非空时，返回 other，否则返回空 |

### 8.5 作用域与权限的交叉陷阱

| 场景 | 风险 | 正确做法 |
|------|------|---------|
| 普通用户脚本里改了 `$env:PATH` | 只改了当前进程，不影响系统，管理员脚本运行时 PATH 可能不同 | 管理员脚本中显式 `$env:PATH = ...` 或用绝对路径 |
| 用 `setx` 设了环境变量 | 只写入用户级注册表，当前 CMD 不生效，定时任务可能也看不到 | 设置后用 `[Environment]::SetEnvironmentVariable` 或重启进程 |
| 脚本里定义了 `$global:var` | 只在当前 PowerShell 会话有效，定时任务/新窗口中不存在 | 需要持久化用注册表或配置文件 |
| 子脚本改了父脚本的变量 | PowerShell 中默认子脚本不能改父作用域变量（除非 `$script:`） | 用 `return` 值或 `$script:` 修饰符显式传递 |
| 以管理员运行后环境变量变了 | 管理员 shell 的 PATH、HOME 可能与普通用户不同 | 脚本内不要假设环境，显式指定路径 |

### 8.6 一句话总结

- **权限作用域**：普通用户只能动自己的目录和 `HKCU`，管理员能改系统级一切；用户环境变量 vs 系统环境变量也是同理。
- **变量作用域**：CMD 用 `setlocal/endlocal` 隔离，PowerShell 用 `$local/$script/$global` 修饰符，Bash 用 `local` 关键字和 `export`。
- **空值访问**：核心风险是变量为空导致路径/命令拼接错误，务必先判断非空再操作，Bash 用 `${VAR:-default}`，PowerShell 用 `??` 或 `if ($null -eq $var)`。

---

## 九、如何选择

| 场景 | 推荐工具 |
|------|---------|
| 运行老旧批处理脚本（.bat / .cmd） | CMD |
| 简单的 ipconfig、ping 等网络命令 | 均可（CMD 更轻量） |
| 系统管理、批量自动化、远程运维 | PowerShell |
| 处理文本需复杂筛选、格式化 | PowerShell（对象管道）或 Bash（grep/awk） |
| 跨平台脚本（Windows + Linux + macOS） | PowerShell 7+ 或 Bash |
| 日常现代使用（Windows） | PowerShell（微软官方主推，CMD 已停止功能更新） |
| Linux / macOS 日常使用 | Bash（或 Zsh） |

### 一句话总结

- **Shell** 是命令行解释程序的总称，CMD、PowerShell、Bash 都是 Shell 的具体实现。
- **CMD** 是上个时代的工具，只处理文本，已停止功能更新。
- **PowerShell** 是现代化的自动化平台，处理结构化 .NET 对象，能力全面超越 CMD，Windows 下日常优先使用 PowerShell。
- **Bash** 是 Linux/macOS 世界的主力 Shell，文本处理能力强，配合 grep/awk/sed 极为灵活。
