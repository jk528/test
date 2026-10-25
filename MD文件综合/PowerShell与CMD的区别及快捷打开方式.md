# PowerShell 与 CMD 的区别及快捷打开方式

> 整理日期：2026-10-25
> 适用系统：Windows 10 / Windows 11

---

## 目录

- [一、核心区别对比](#一核心区别对比)
- [二、详细差异说明](#二详细差异说明)
- [三、快捷打开方式](#三快捷打开方式)
- [四、如何选择](#四如何选择)

---

## 一、核心区别对比

| 对比维度 | CMD（命令提示符） | PowerShell |
|---------|------------------|------------|
| 首次发布 | 1987 年（MS-DOS 时代沿袭） | 2006 年（PowerShell 1.0） |
| 本质定位 | 传统命令行解释器 | 面向对象的自动化 Shell + 脚本平台 |
| 输出类型 | 纯文本 | .NET 对象（可传递属性与方法） |
| 脚本能力 | 批处理（.bat / .cmd），功能弱 | .ps1 脚本，功能强大，支持函数、模块、异常处理 |
| 命令体系 | DOS 命令（dir、copy 等） | Cmdlet（动词-名词，如 Get-Process），兼容大部分 DOS 命令别名 |
| 管道机制 | 传递文本流 | 传递结构化对象 |
| 跨平台 | 仅 Windows | PowerShell 7+ 支持 Windows / Linux / macOS |
| 注册表/WMI 操作 | 不支持或极弱 | 原生支持（注册表可当作磁盘浏览） |
| 远程管理 | 不支持 | 原生支持（Enter-PSSession、Invoke-Command） |
| 默认颜色 | 黑底白字 | 蓝底白字（经典版） |
| 当前状态 | 维护模式，不再新增功能 | 持续更新（PowerShell 7.x 为现代版本） |

---

## 二、详细差异说明

### 1. 对象 vs 文本

CMD 中管道传递的是纯文本，需要靠字符串解析提取信息；PowerShell 传递的是 .NET 对象，可直接按属性筛选：

```powershell
# PowerShell：找出内存占用超过 500MB 的进程
Get-Process | Where-Object { $_.WorkingSet -gt 500MB } | Sort-Object WorkingSet -Descending
```

同样的需求在 CMD 中几乎无法简洁实现。

### 2. 命令命名规范

PowerShell 命令遵循「动词-名词」规范，可读性强：

| 操作 | CMD | PowerShell |
|------|-----|-----------|
| 查看目录 | `dir` | `Get-ChildItem`（别名 `ls` / `dir`） |
| 复制文件 | `copy` | `Copy-Item`（别名 `cp`） |
| 查看内容 | `type` | `Get-Content`（别名 `cat`） |
| 结束进程 | `taskkill /im xx.exe` | `Stop-Process -Name xx` |

### 3. 脚本能力

- CMD 批处理：适合简单的顺序命令执行，变量、判断、循环语法简陋。
- PowerShell 脚本：支持函数、模块、try/catch、类、远程执行、调用 .NET 类库，可调用 COM、WMI、注册表、文件系统等一切系统资源。

### 4. 版本说明

| 版本 | 说明 |
|------|------|
| Windows PowerShell 5.1 | Windows 10/11 系统自带，蓝底窗口，仅支持 Windows |
| PowerShell 7.x（pwsh） | 现代跨平台版本，需单独安装，黑底窗口，性能更强 |

---

## 三、快捷打开方式

### 通用方法（CMD 与 PowerShell 均适用）

| 方法 | 操作步骤 |
|------|---------|
| Win + R 运行框 | 按 `Win + R`，输入 `cmd` 或 `powershell`，回车 |
| 开始菜单搜索 | 按 `Win` 键，输入 `cmd` 或 `powershell`，点击搜索结果 |
| 任务管理器 | `Ctrl + Shift + Esc` 打开任务管理器 → 文件 → 运行新任务 → 输入命令 |
| 地址栏输入法 | 在任意文件夹的资源管理器地址栏输入 `cmd` 或 `powershell`，回车后**以当前路径**打开 |
| Shift + 右键 | 在文件夹空白处按住 `Shift` 右键 → 选择「在此处打开 PowerShell 窗口」（Win10） |

### 以管理员身份打开

| 方法 | 操作步骤 |
|------|---------|
| 快捷键（推荐） | 按 `Win + X`，再按 `A`（Win10 旧版直接显示；Win11 打开的是终端管理员版） |
| 搜索 + Ctrl Shift Enter | 开始菜单搜索 `cmd` 或 `powershell`，按 `Ctrl + Shift + Enter` 以管理员运行 |
| 右键选项 | 搜索到程序后右键 → 「以管理员身份运行」 |

### Windows 11 专属

| 方法 | 操作步骤 |
|------|---------|
| Win + X 菜单 | `Win + X` → 选择「终端」或「终端（管理员）」，默认打开 PowerShell |
| 终端内切换 | 打开 Windows Terminal 后，点击标签页右侧 `∨` 下拉箭头，可切换 PowerShell / CMD / Azure Cloud Shell |
| 右键菜单 | 文件夹空白处右键 → 「在终端中打开」 |

### 常用快捷键一览

| 快捷键 | 作用 |
|--------|------|
| `Win + R` | 打开运行框 |
| `Win + X` | 打开快速链接菜单（含终端入口） |
| `Ctrl + Shift + Esc` | 打开任务管理器 |
| `Alt + D` | 定位到资源管理器地址栏（配合输入 cmd 使用极佳） |
| `Ctrl + Shift + Enter` | 以管理员身份运行搜索到的程序 |

---

## 四、如何选择

| 场景 | 推荐工具 |
|------|---------|
| 运行老旧批处理脚本（.bat） | CMD |
| 简单的 ipconfig、ping 等网络命令 | 均可（CMD 更轻量） |
| 系统管理、批量自动化、远程运维 | PowerShell |
| 处理文本需复杂筛选、格式化 | PowerShell（对象管道） |
| 跨平台脚本（Windows + Linux + macOS） | PowerShell 7+ |
| 日常现代使用 | PowerShell（微软官方主推，CMD 已停止功能更新） |

**一句话总结**：CMD 是上个时代的命令行工具，只处理文本；PowerShell 是现代化的自动化平台，处理结构化对象，能力全面覆盖并超越 CMD。日常建议优先使用 PowerShell。
