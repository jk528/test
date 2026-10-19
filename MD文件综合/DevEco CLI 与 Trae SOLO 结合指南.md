# DevEco CLI 与 Trae SOLO 结合指南

> 面向 HarmonyOS（鸿蒙）应用开发的「AI 自主开发」实践手册
> 更新时间：2026-10-19

---

## 一、先认识这两个工具

### 1.1 DevEco CLI（命令名 `devecocli`）

DevEco CLI 是华为面向 HarmonyOS 应用开发推出的**统一命令行入口**。它没有另起炉灶，而是把 DevEco Studio 已有的工具链**原子化封装**到一个命令下：

| 内置能力 | 说明 | 类比 |
| --- | --- | --- |
| `ohpm` | 鸿蒙包管理 | 类 npm |
| `hvigor` | 构建工具链 | 类 Gradle |
| `hdc` | 设备连接调试 | 类 adb |
| `emulator` | 模拟器管理 | 类 AVD |
| `hilog` | 系统日志 | 类 logcat |

在此基础上，DevEco CLI 还额外集成了：

- **项目脚手架**（`create`）
- **本地 HarmonyOS 官方文档检索**（`docs`，约 2000 万字离线文档库）
- **HarmonyOS 技能市场**（`skills`）
- **MCP 服务**与**面向 AI Agent 的 Skill 安装**（`init` / `serve mcp`）

**核心定位**：它是 AI 的「手脚」——把「构建工程、安装真机、抓日志、点 UI」这些物理动作交给命令行执行，让 AI 从「纸上谈兵」变成「真正跑得起来」。

### 1.2 Trae 与 SOLO 模式

Trae 是字节跳动推出的 AI 原生 IDE，包含面向开发者/企业的 **TraeCode（AI IDE）**。它有两大开发模式：

- **IDE 模式**：AI 辅助，人强控制，逐行/逐块协作；
- **SOLO 模式**：**AI 主导**，自动完成「规划 → 执行 → 验证」全流程。

SOLO 模式的关键能力：

- **自带模型池**：如 Doubao-Seed-2.0-Code（前端/UI）、GLM-5（架构/复杂任务）、MiniMax-M2.5（跨语言）、Kimi-K2.5（超长上下文）；
- **多任务并行**：多个任务窗口互不干扰，各记各的上下文；
- **DiffView 差异审查**：每步改动可见、可回退，识别越界修改；
- **上下文压缩（Compact）**：长对话自动/手动压缩，避免跑偏；
- **Skills / Rules / 记忆 / MCP**：构成 AI 的「长期素养」与外部工具接入。

**核心定位**：它是 AI 的「大脑」——负责思考、调度、规划与验证。

### 1.3 为什么要把两者结合

一句话：**大脑（Trae SOLO）+ 手脚（DevEco CLI）+ 经验（Skill/MCP）= 鸿蒙 Vibe Coding 闭环。**

- 只有大脑，AI 写完代码跑不起来、改完代码只能靠猜；
- 只有手脚，开发者还得自己记大量命令；
- 把 DevEco CLI 作为 Skill / MCP 装进 Trae 后，SOLO 模式即可**用自然语言驱动鸿蒙工具链**，自动构建、部署、抓日志、查文档、跑 UI 自动化。

---

## 二、结合的总体思路

```
┌─────────────────────────────────────────────┐
│  Trae SOLO（大脑）                            │
│  规划 → 执行 → 验证，自然语言驱动全流程        │
└───────────────┬─────────────────────────────┘
                │  Skill / MCP（神经连接）
                ▼
┌─────────────────────────────────────────────┐
│  DevEco CLI（手脚）                           │
│  create / build / run / device / log / docs  │
│  ui / emulator / check / signature           │
└───────────────┬─────────────────────────────┘
                ▼
         HarmonyOS 工程 / 真机 / 模拟器
```

**职责分工（重要）**：

- **MCP 负责「眼睛」**：只读能力——文档检索、基于 LSP 的语法检查/跳转/引用等诊断；
- **命令行负责「手脚」**：有副作用的写操作——构建、签名、部署、模拟器、UI 自动化。

> 注：DevEco CLI 的 MCP 服务近期已**收缩**，`build_project`、`start_app` 等构建/执行类工具被移除，回归命令行。这样做是为了安全边界与可审计性（写操作走终端，可见可控可拦截）。因此**推荐以 Skill 方式集成，让 AI 直接调用 `devecocli` 命令**。

---

## 三、详细步骤

### 步骤 0：环境准备

在集成前，本机需满足：

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 或 macOS（部分版本暂不支持 Linux / 鸿蒙 PC，以官方为准） |
| Node.js | ≥ 18，**推荐 22 及以上** |
| DevEco Studio | ≥ 6.1.0（macOS 必须装在 `~/Applications` 或 `/Applications`） |
| Trae | 已安装 TraeCode（国内版即 `trae-cn`），建议使用较新版本 |

**路径规范**：安装路径不要包含中文、空格、特殊字符。

---

### 步骤 1：安装 DevEco CLI

```bash
npm install -g @deveco/deveco-cli@latest
```

验证安装：

```bash
devecocli --version
devecocli help
```

> Windows PowerShell 若提示禁止运行 `devecocli.ps1`，可改用 `devecocli.cmd`，或在普通命令提示符中执行。

---

### 步骤 2：登录授权（1.3.0 版本起）

部分功能需授权后使用：

```bash
devecocli auth login      # 按指引登录华为账号
devecocli auth status     # 查询当前登录用户
devecocli auth team list  # 查询所在团队
```

---

### 步骤 3：把 DevEco CLI 集成到 Trae（关键步骤）

`devecocli init` 支持把 **Skill** 或 **MCP 服务**配置进 AI Agent，且**内置对 `trae-cn` 的支持**。

#### 方式一：安装 Skill（推荐，适合绝大多数用户）

```bash
# 安装/更新，并覆盖已存在项
devecocli init -f

# 仅安装 Skill
devecocli init --skill

# 指定 Agent 与工程路径（把 Skill 装到具体项目里）
devecocli init --skill --agent trae-cn --project .\MyApp

# 全局安装到 Trae（用户级）
devecocli init --agent trae-cn
```

#### 方式二：配置 MCP 服务（需要只读诊断/文档能力时）

```bash
# 用户级 MCP 服务
devecocli init --mcp

# 指定 Agent
devecocli init --mcp --agent trae-cn

# 工程级 MCP 服务（与 --project 一起用）
devecocli init --mcp --project .\MyApp -f
```

**`init` 主要参数速查**：

| 参数 | 说明 |
| --- | --- |
| `--agent` | 智能体名称，多个用英文逗号分隔；缺省=配置到所有已检测到的智能体 |
| `--project` | 指定工程路径，装到该工程；缺省=个人用户目录 |
| `--path` | 指定 Skill 配置路径（不可与 `--project`/`--agent`/`--mcp` 同用） |
| `--skill` | 安装 Skill（与 `--mcp` 互斥；都不填时默认执行 `--skill`） |
| `--mcp` | 配置 MCP 服务 |
| `-f, --force` | 目标已存在时覆盖重装 |

---

### 步骤 4：验证集成是否生效

**Skill 方式**——检查 Trae 技能目录：

- 国内版 TraeCode 期望目录：`.trae/skills/deveco-cli/SKILL.md`
- 实测中 CLI 可能写入 `.trae-cn/skills/deveco-cli/SKILL.md`

> 注意：目录结构应为 `.trae/skills/deveco-cli/SKILL.md`，而**不是**把 `SKILL.md` 直接放在 `.trae/skills/` 下。若两个目录不一致，可把 CLI 包内自带的原始 `SKILL.md`（位于 npm 全局包 `@deveco/deveco-cli` 内）复制到 IDE 官方路径，并用 SHA-256 校验两份哈希一致。

复制示例（PowerShell）：

```powershell
$cliPackageRoot = Join-Path (npm root -g).Trim() '@deveco\deveco-cli'
$skillSource    = Join-Path $cliPackageRoot 'SKILL.md'
$skillDirectory = 'D:\HarmonyLab\TraeLogin\.trae\skills\deveco-cli'
$skillTarget    = Join-Path $skillDirectory 'SKILL.md'
New-Item -ItemType Directory -Path $skillDirectory -Force | Out-Null
Copy-Item -LiteralPath $skillSource -Destination $skillTarget
Get-FileHash -LiteralPath $skillSource -Algorithm SHA256
Get-FileHash -LiteralPath $skillTarget -Algorithm SHA256
```

**MCP 方式**——在 Trae 的 MCP 配置页确认服务已加载，或调用 MCP 的 `status` 工具确认 `devecocli` / 文档库 / 工程三项就绪。

集成成功后，在 Trae 中即可看到 `deveco-cli` 技能，Trae 的技能列表会出现对应条目。

---

### 步骤 5：在 Trae SOLO 中开工（推荐实操流程）

结合 SOLO 模式的「先想清楚、再动手、后复查」协作节奏：

1. **Plan（方案先行）**：用自然语言提需求，先让 SOLO 给出方案，重点看边界情况（异常处理、并发、事务边界）；
2. **测试先行**：让它先写测试用例（如 3 个正常 + 2 个异常场景），再实现功能；
3. **执行**：SOLO 自动调用 `devecocli` 命令完成 `create` → `build` → `run` 闭环；
4. **DiffView 复查**：查看每步改动，确认没有引入意外依赖、没有改动不该改的文件；
5. **验证反馈**：让 AI 用 `devecocli log` 抓日志、`ui screenshot` 截图、`docs search` 查官方文档验证 API 用法，自主修复直到通过；
6. **收尾**：拿到处理报告，人工做线上验证。

**示例指令（可直接对 SOLO 说）**：

```
用 devecocli 创建一个 HarmonyOS 应用工程，应用名 CalendarPicker，
包名 com.example.calendarpicker，API Level 用当前 SDK 支持的最高版本，
全局使用状态管理（V2）装饰器。
```

```
帮我打开模拟器并进行调试。
```

```
查一下官方文档里 TextInput 密码输入和 ArkUI 状态管理的用法，
再按文档实现登录页。
```

---

### 步骤 6：沙箱与白名单（易踩坑，务必处理）

Trae 有命令沙箱机制。**若在沙箱中编译，可能导致构建出错**。建议二选一：

- 把 `devecocli` 命令**加入白名单**（推荐，安全边界内放行）；
- 或让相关命令**不在沙箱中运行**。

这样既保证构建成功，又保留了终端层的可审计性。

---

## 四、DevEco CLI 常用命令速查

| 能力维度 | 核心命令 | 作用 |
| --- | --- | --- |
| 工程管理 | `create` / `build` / `build clean` / `run` | 创建 → 构建 → 清理 → 安装运行，一条龙 |
| 设备管理 | `device list` / `device view` | 查看已连接的真机与模拟器 |
| 模拟器 | `emulator list/create/start/stop/delete` | 完整模拟器生命周期 |
| 日志调试 | `log` | 查看 hilog，支持级别/包名/关键词过滤、崩溃日志、实时追踪 |
| 文档检索 | `docs search` / `docs read` / `docs catalog` | 本地官方文档检索与阅读 |
| 技能市场 | `skills list/find/add/remove` | 查询、安装、管理 HarmonyOS Skill |
| 代码检查 | `check lint` / `check compat` | Code Linter 规范检查 / SDK 版本 API 变更扫描 |
| UI 自动化 | `ui layout` / `ui screenshot` / `ui click·swipe·text` | 控件树、截图、点击/滑动/输入 |
| 签名 | `signature generate` | 自动生成调试签名并写入工程配置 |
| AI 集成 | `init` / `serve mcp` | 配置 Skill 或 MCP 到 AI Agent；启动内置 MCP 服务 |

**构建示例**：

```bash
devecocli build                                   # 单模块工程直接构建
devecocli build --modules entry library           # 指定模块
devecocli build --product default --build-mode release
```

**文档检索示例**：

```bash
devecocli docs search TextInput 密码输入 ArkUI 状态管理 --limit 20
devecocli docs search '@State' '@Prop' --catalog best-practices --limit 10
devecocli docs read <documentId>
```

---

## 五、应用场景

### 场景 1：鸿蒙应用从零生成（Vibe Coding）

用自然语言描述需求，SOLO 规划 + 生成 ArkTS/ArkUI 代码，DevEco CLI 负责创建工程、构建、跑到设备上。适合快速原型、Demo、内部工具。

### 场景 2：复杂需求的多步拆解开发

把一个复杂 UI（如日历选择器：单选/多选/区间渲染/信息栏）按开发顺序拆成多个独立步骤，每步只描述一个目标，让 SOLO 逐步实现、逐步验证，出错可控。

### 场景 3：AI 自动查官方文档验证 API

通过集成的 `docs` 能力，AI 写代码时自动检索 2000 万字官方文档，避免「编造不存在的 API」，提升生成准确率。

### 场景 4：自动构建与真机/模拟器部署

AI 完成代码后自动 `build` → `run`，把 HAP 装到真机或模拟器并启动，人工无需手动敲命令。

### 场景 5：日志抓取与自主排错

用 `log` 抓 hilog、崩溃日志，AI 根据报错定位问题并修复，形成「改 → 跑 → 看日志 → 再改」的自动闭环。

### 场景 6：UI 自动化测试与截图回归

用 `ui layout / screenshot / click / swipe / text` 做控件树获取、截图比对、UI 自动化操作，可用于回归测试或自动化验证。

### 场景 7：跨 AI 工具的迁移复用

同一套 DevEco CLI Skill/MCP 可配置到 Trae、Cursor、Claude Code、CodeBuddy、Qoder、opencode、codex 等多个 AI 工具，团队可统一到同一套鸿蒙自动化工作流。

### 场景 8：CI / 团队协作

`devecocli build` 参数收敛清晰（product/modules/build-mode），适合写入自动化脚本与持续集成流水线。

---

## 六、避坑与注意事项

1. **MCP 已收缩写能力**：不要再依赖 MCP 的 `build_project`/`start_app`，构建/部署要用命令行 `devecocli build`/`run`；必要时让项目记忆固化这些命令习惯。
2. **Skill 目录不匹配**：CLI 写入 `.trae-cn/skills/...`，IDE 官方期望 `.trae/skills/...`，需核对并按需复制、校验哈希。
3. **沙箱导致编译失败**：把 `devecocli` 加白名单或关闭沙箱。
4. **路径含中文/空格**：会导致工具链定位失败，务必使用纯英文、无空格路径。
5. **macOS 安装位置**：DevEco Studio 必须在 `~/Applications` 或 `/Applications`，否则 CLI 找不到工具链。
6. **Node.js 版本**：低于 18 会失败，推荐 22+。
7. **已有同名 Skill 先看内容**：避免自定义规则被直接覆盖。
8. **首次 `docs` 命令会自动初始化文档库**，首次可能稍慢。
9. **人工把关三节点**：方案评审、代码 Diff、线上验证——SOLO 再强也应守住这三道关。

---

## 七、参考来源

- 华为开发者联盟：《DevEco CLI 初探索：试着用一条命令行跑通鸿蒙开发》
- 华为开发者文档：《DevEco CLI 命令选项》（developer.huawei.com / HarmonyOS-Guides / ide-deveco-cli-options）
- 华为开发者联盟：《在 Trae 中集成 DevEco CLI 实现日历选择功能》
- CSDN：《Trae + DevEco CLI：鸿蒙 Vibecoding 全流程实战指南》
- 51CTO：《鸿蒙应用开发利器 DevEcoCli》
- 腾讯云开发者社区：《TRAE 的模型选择指南与实战教程（SOLO 模式）》
- CSDN：《Trae 中 MCP Server 使用指南》
- 开源项目：`openharmony-sig/deveco-cli`、`kelai141/devecocli-mcp`

> 说明：产品版本迭代较快，文中命令、参数与目录以本机实际安装版本为准，请以华为与 Trae 官方最新文档为最终依据。