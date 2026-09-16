---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '3ea2dadb-9047-4dcb-96f8-45eff2a45021'
  PropagateID: '3ea2dadb-9047-4dcb-96f8-45eff2a45021'
  ReservedCode1: '25a144ee-df1e-4410-b6da-b4db99f4f9f1'
  ReservedCode2: '25a144ee-df1e-4410-b6da-b4db99f4f9f1'
---

# 新闻联播每日总结 - Windows 任务计划自动化方案

> **当前运行模式（2026-09-16 起，以本节为准）**
>
> 本文档下方描述的 `auto_v2` / `semi_auto` / `ai_api` 三种模式**均已停用**，
> 保留作为历史记录。现行为 **oneshot 一键生成模式**：
>
> - 执行脚本：`../一键生成/xwlb_report.py`（v5.3.0，单一入口，仅依赖
>   Python 标准库 + requests，不调用任何付费 API）
> - 一条命令跑完：抓取 → 分类 → 六要素 → 渲染 → 内置质量自检 → 按日期落
>   `归档/YYYY年M月/新闻联播总结_YYYYMMDD.md`
> - 格式契约运行时从 `../旧版本/新闻联播总结_去敏感词模板.md` 抽取，
>   七部分结构与第六部分 10 列表头严格不变
> - 退出码：`0` 通过 / `1` 有 ERROR / `2` 有 CRITICAL（定时任务据此判成败）
> - 批量重建历史归档：`python ../一键生成/rebuild_archives.py [--all] [--dry-run]`
>
> 定时任务入口仍为 `scripts/run_daily_task.ps1`（每日 06:30，默认生成"昨天"，
> 也支持 `run_daily_task.ps1 20260915` 补跑指定日期）。
>
> **版本**：v1.1.0  
> **日期**：2026-09-16  
> **适用系统**：Windows 10 / Windows 11

---

## 一、可行性分析

### 1.1 结论：完全可行

Windows 任务计划程序（Task Scheduler）是系统内置功能，完全可以满足定时自动生成新闻联播总结的需求。

### 1.2 技术可行性

| 项目 | 状态 | 说明 |
|------|------|------|
| Python 环境 | ✅ 已具备 | 现有脚本基于 Python，可直接调用 |
| 定时触发 | ✅ 支持 | Windows 任务计划程序支持每日定时执行 |
| 无人值守 | ✅ 支持 | 后台静默运行，无需用户登录后操作 |
| 失败重试 | ✅ 支持 | 任务计划程序内置重试机制 + 脚本级重试 |
| 日志记录 | ✅ 支持 | 脚本自动记录运行日志 |
| 结果通知 | ⚠️ 可选 | 可扩展 Webhook / 邮件通知 |

### 1.3 现有资源可复用

- ✅ `gen_report_v2.py` — 全自动生成（正则提取六要素）
- ✅ `gen_report_final.py` — 分阶段生成（AI 填写六要素）
- ✅ `fill_elements_api.py` — 外部 AI API 自动填写六要素（不消耗 TeleAgent 积分）
- ✅ `sync_gitee.ps1` — Git 同步脚本
- ✅ `check_md_quality.py` — 质量检测脚本

---

## 二、三种自动化模式对比

### 2.1 模式对比表

| 维度 | 模式一：全自动 v2 | 模式二：半自动分阶段 | 模式三：AI API 全自动 ⭐推荐 |
|------|-------------------|---------------------|----------------------|
| **六要素质量** | 一般（正则提取） | 高（AI 手动填写） | 高（AI API 自动） |
| **人工干预** | 零 | 每日需手动填写 JSON | 零 |
| **生成耗时** | ~15 秒 | ~2 分钟 + 人工时间 | ~2 分钟 |
| **TeleAgent 积分** | 不消耗 | 不消耗 | 不消耗 |
| **外部 API 成本** | 无 | 无 | 低（DeepSeek约0.01元/天） |
| **稳定性** | 最高 | 中（依赖人工） | 较高（依赖 API） |
| **推荐场景** | 日常自用、对六要素要求不高 | 对质量要求高、有人工维护 | 追求质量 + 全自动 ✅ |

### 2.2 模式一：全自动 v2（入门）

```
每天 06:30 自动触发
    ↓
调用 gen_report_v2.py 生成完整报告
    ↓
质量检查 → Git 同步 → 完成
```

**特点**：
- 完全无需人工干预
- 六要素由正则表达式提取，覆盖率约 70%
- 适合日常浏览使用

### 2.3 模式二：半自动分阶段

```
每天 06:30 自动触发 Phase 1
    ↓
生成 1-5 部分 + 六要素数据源 JSON
    ↓
人工打开 JSON 文件，填写六要素
    ↓
检测到结果 JSON → 自动执行 Phase 3 合并
    ↓
完整报告生成 → Git 同步 → 完成
```

**特点**：
- 六要素质量高（人工/AI 填写）
- 每日需 5-10 分钟人工填写
- 适合对报告质量要求高的场景

### 2.4 模式三：AI API 全自动 ⭐推荐

```
每天 06:30 自动触发
    ↓
Phase 1: 脚本生成1-5部分 + 六要素数据源JSON（~15秒）
    ↓
Phase 2: 调用外部AI API自动填写六要素JSON（~30秒）
    ↓
Phase 3: 脚本合并生成完整报告（<1秒）
    ↓
质量检查 → Git 同步 → 完成
```

**特点**：
- 全自动 + 高质量（与 TeleAgent 手动生成质量一致）
- **不消耗 TeleAgent 积分**
- 使用外部 AI API（DeepSeek/通义千问等），每日成本约 0.01 元
- 支持任何 OpenAI 兼容接口（含本地 Ollama）

**支持的 AI API**：

| API 提供商 | base_url | 推荐模型 | 费用 |
|-----------|----------|---------|------|
| DeepSeek（推荐） | `https://api.deepseek.com/v1` | `deepseek-chat` | ~0.01元/天 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | ~0.02元/天 |
| Moonshot/Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | ~0.03元/天 |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:14b` | 免费 |

---

## 三、快速开始

### 3.1 目录结构

```
自动化任务/
├── config/
│   └── config.json          # 配置文件
├── scripts/
│   ├── register_task.ps1    # 注册任务计划（右键运行）
│   ├── unregister_task.ps1  # 卸载任务计划（右键运行）
│   ├── run_daily_task.ps1   # 主执行脚本（被任务计划调用）
│   ├── run_now.ps1          # 手动立即运行（右键运行）
│   ├── check_status.ps1     # 查看状态和日志（右键运行）
│   └── check_and_merge.ps1  # 半自动模式合并检测
└── logs/                    # 日志目录（自动生成）
    └── task_YYYYMMDD.log

分阶段生成方案/                # Python 脚本目录
├── gen_report_v2.py         # 全自动正则版
├── gen_report_final.py      # 分阶段生成版（Phase 1/3）
├── fill_elements_api.py     # AI API 六要素填写（Phase 2）⭐新增
├── fetch_xwlb.py            # 央视网抓取
├── fetch_iqilu.py           # 齐鲁网抓取
└── check_md_quality.py      # 质量检测
```

### 3.2 快速上手（AI API 全自动模式 ⭐推荐）

#### 第一步：配置 AI API Key

打开 `config\config.json`，填入你的 API Key：

```json
{
  "mode": "ai_api",
  "modes": {
    "ai_api": {
      "api_key": "你的API Key",
      "api_base_url": "https://api.deepseek.com/v1",
      "api_model": "deepseek-chat"
    }
  }
}
```

> **获取 DeepSeek API Key**：访问 https://platform.deepseek.com 注册后创建 API Key，新用户有免费额度。

#### 第二步：注册任务

1. 进入 `scripts\` 文件夹
2. **右键** `register_task.ps1` → **使用 PowerShell 运行**
3. 等待提示"任务计划创建成功"

#### 第三步：验证

运行 `check_status.ps1` 查看任务状态，或运行 `run_now.ps1` 手动测试一次。

### 3.3 快速上手（全自动 v2 模式）

#### 第一步：确认配置

打开 `config\config.json`，确认：

```json
{
  "mode": "auto_v2"
}
```

#### 第二步：注册任务

1. 进入 `scripts\` 文件夹
2. **右键** `register_task.ps1` → **使用 PowerShell 运行**
3. 等待提示"任务计划创建成功"

#### 第三步：验证

运行 `check_status.ps1` 查看任务状态，或运行 `run_now.ps1` 手动测试一次。

---

## 四、配置说明

### 4.1 完整配置项

```json
{
  "task_name": "新闻联播每日总结",          // 任务名称（显示在任务计划程序中）
  "task_description": "...",                // 任务描述
  
  "schedule": {
    "enabled": true,                        // 是否启用
    "time": "06:30",                        // 每日执行时间（24小时制）
    "timezone": "China Standard Time",      // 时区
    "run_if_missed": true                   // 错过时间后是否补跑
  },
  
  "mode": "ai_api",                         // 运行模式：auto_v2 / semi_auto / ai_api
  
  "modes": {
    "ai_api": {                              // AI API 全自动模式配置
      "api_provider": "deepseek",             // API 提供商
      "api_key": "",                          // API Key（必填）
      "api_base_url": "https://api.deepseek.com/v1",  // API Base URL
      "api_model": "deepseek-chat",           // 模型名称
      "max_tokens": 4096,                    // 最大输出 token 数
      "temperature": 0.3                     // 生成温度（越低越稳定）
    }
  },
  
  "paths": {
    "python_exe": "python",                 // Python 可执行文件路径
    "script_dir": "../分阶段生成方案",       // Python脚本目录
    "gen_v2_script": "gen_report_v2.py",    // v2全自动脚本
    "gen_final_script": "gen_report_final.py", // 分阶段脚本
    "fill_elements_script": "fill_elements_api.py", // AI API填写脚本
    "output_dir": "../../归档",             // 输出目录
    "log_dir": "./logs"                     // 日志目录
  },
  
  "quality": {
    "run_quality_check": true,              // 是否运行质量检查
    "min_file_size_kb": 10                  // 最小文件大小（KB）
  },
  
  "sync": {
    "enabled": true,                        // 是否启用Git同步
    "sync_script": "../旧版本/sync_gitee.ps1" // 同步脚本路径
  },
  
  "retry": {
    "max_retries": 3,                       // 最大重试次数
    "retry_interval_seconds": 300           // 重试间隔（秒）
  }
}
```

### 4.2 修改执行时间

编辑 `config.json` 中的 `schedule.time`：

```json
"schedule": {
  "time": "07:00"  // 改成你想要的时间，格式 HH:mm
}
```

修改后**无需重新注册任务**，下次执行时自动读取新配置。

### 4.3 配置 AI API（ai_api 模式）

#### 方式一：在 config.json 中配置

```json
{
  "mode": "ai_api",
  "modes": {
    "ai_api": {
      "api_key": "sk-xxxxxxxxxxxx",
      "api_base_url": "https://api.deepseek.com/v1",
      "api_model": "deepseek-chat"
    }
  }
}
```

#### 方式二：通过环境变量配置（推荐，避免 Key 写入文件）

```powershell
# 在 PowerShell 中设置环境变量（持久化）
[Environment]::SetEnvironmentVariable("XWLB_AI_API_KEY", "sk-xxxxxxxxxxxx", "User")
[Environment]::SetEnvironmentVariable("XWLB_AI_BASE_URL", "https://api.deepseek.com/v1", "User")
[Environment]::SetEnvironmentVariable("XWLB_AI_MODEL", "deepseek-chat", "User")
```

设置后 config.json 中的 api_key 可留空，脚本会自动读取环境变量。

#### 方式三：使用本地 Ollama（完全免费）

1. 安装 [Ollama](https://ollama.com)
2. 下载模型：`ollama pull qwen2.5:14b`
3. 配置：

```json
{
  "modes": {
    "ai_api": {
      "api_key": "ollama",
      "api_base_url": "http://localhost:11434/v1",
      "api_model": "qwen2.5:14b"
    }
  }
}
```

### 4.4 切换运行模式

修改 `config.json` 中的 `mode` 字段：

```json
"mode": "auto_v2"     // 全自动正则模式（无需API）
"mode": "semi_auto"   // 半自动分阶段模式
"mode": "ai_api"      // AI API全自动模式（推荐）
```

**半自动模式使用流程**：
1. 每天早上自动生成 1-5 部分 + 数据源 JSON
2. 你手动打开 `归档/YYYY年M月/六要素数据源_YYYYMMDD.json`
3. 用 AI（或手动）填写每条的 `elements` 字段
4. 另存为 `六要素结果_YYYYMMDD.json`（同目录）
5. 运行 `check_and_merge.ps1` 自动检测并合并

---

## 五、脚本说明

### 5.1 register_task.ps1 — 注册任务

| 项目 | 说明 |
|------|------|
| 用途 | 将定时任务注册到 Windows 任务计划程序 |
| 权限 | 需要管理员权限（自动请求提升） |
| 运行方式 | 右键 → 使用 PowerShell 运行 |

**注册后可在"任务计划程序"中看到**：
- 开始菜单搜索"任务计划程序"
- 左侧导航到"任务计划程序库"
- 找到名称为"新闻联播每日总结"的任务

### 5.2 unregister_task.ps1 — 卸载任务

| 项目 | 说明 |
|------|------|
| 用途 | 从任务计划程序中移除定时任务 |
| 注意 | 不会删除日志文件和已生成的报告 |

### 5.3 run_now.ps1 — 立即运行

| 项目 | 说明 |
|------|------|
| 用途 | 手动触发一次任务执行（用于测试） |
| 输出 | 实时显示执行过程和结果 |

### 5.4 check_status.ps1 — 查看状态

显示内容包括：
- 任务计划状态（启用/禁用、下次运行时间）
- 最近执行结果
- 今日日志最后 20 行
- 最近生成的 5 份报告

### 5.5 run_daily_task.ps1 — 主执行脚本

被任务计划程序调用，负责：
1. 读取配置文件
2. 根据模式执行对应生成逻辑
3. 失败自动重试（最多 3 次）
4. 质量检查
5. Git 同步
6. 记录完整日志

---

## 六、日志与监控

### 6.1 日志文件

日志保存在 `logs\` 目录下，按天生成：

```
logs/
├── task_20260913.log
├── task_20260912.log
└── ...
```

### 6.2 日志格式

```
[2026-09-13 06:30:01] [INFO] ============================================================
[2026-09-13 06:30:01] [INFO]   新闻联播每日总结 - 定时任务开始执行
[2026-09-13 06:30:01] [INFO] ============================================================
[2026-09-13 06:30:01] [INFO] 目标日期: 20260912
[2026-09-13 06:30:01] [INFO] 执行模式: auto_v2
[2026-09-13 06:30:02] [INFO] ========== 模式: 全自动 v2（正则版） ==========
[2026-09-13 06:30:15] [SUCCESS] v2 报告生成成功
[2026-09-13 06:30:16] [SUCCESS] 质量检查通过
[2026-09-13 06:30:20] [SUCCESS] Git同步完成
[2026-09-13 06:30:20] [SUCCESS] 任务执行成功！
```

### 6.3 异常排查

| 现象 | 可能原因 | 排查方法 |
|------|---------|---------|
| 任务没运行 | 任务未启用 / 电脑未开机 | 运行 check_status.ps1 查看下次运行时间 |
| 运行失败 | Python 未安装 / 路径错误 | 查看 logs\ 下当天日志 |
| 生成的报告很小 | 网络问题 / 数据源异常 | 检查日志中的错误信息 |
| Git 同步失败 | 仓库配置问题 / 权限 | 手动运行 sync_gitee.ps1 查看错误 |

---

## 七、常见问题

### Q1: 任务计划程序需要一直开着电脑吗？

**A**: 是的。任务计划程序只在电脑运行时触发。如果电脑关机，任务会在下次开机时自动补跑（`run_if_missed: true`）。

### Q2: 可以修改执行时间吗？

**A**: 可以。编辑 `config.json` 中的 `schedule.time` 即可，无需重新注册任务。

### Q3: 如何临时暂停任务？

**A**: 打开"任务计划程序"，找到任务，右键 → "禁用"。需要时再"启用"。

### Q4: 全自动 v2 模式的六要素质量如何？

**A**: 根据测试，正则提取的六要素覆盖率约 70%。人物、地点、事件类提取较准确，原因和方式类可能为"—"。对质量要求高建议使用半自动模式。

### Q5: 半自动模式可以让 AI 自动填写吗？

**A**: 可以。你可以用任意 AI 工具读取数据源 JSON 并填写结果，保存为指定文件名即可。脚本只检测文件是否存在，不关心填写方式。也可以使用 `ai_api` 模式全自动填写。

### Q6: AI API 模式如何配置？

**A**: 三种方式：
1. 在 `config.json` 的 `modes.ai_api.api_key` 中填写 API Key
2. 设置环境变量 `XWLB_AI_API_KEY`
3. 使用本地 Ollama（完全免费），详见 4.3 节

推荐使用 DeepSeek（性价比最高，新用户有免费额度）。

### Q7: AI API 模式生成质量如何？

**A**: AI API 模式使用与 TeleAgent 相同的分阶段流程（Phase 1-3），六要素由外部 AI API 填写，质量与 TeleAgent 手动生成一致。仅消耗外部 API 费用（DeepSeek 约 0.01 元/天），不消耗 TeleAgent 积分。

### Q8: AI API 调用失败怎么办？

**A**: 脚本内置 3 次重试机制。如果全部失败：
- 检查 API Key 是否正确
- 检查网络连接
- 查看 `logs/` 目录下的日志
- 可手动填写六要素后运行 `check_and_merge.ps1` 合并
- 或临时切换到 `auto_v2` 模式（正则提取，质量稍低但零依赖）

---

## 八、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-09-13 | 初始版本：支持 auto_v2 / semi_auto 两种模式，任务计划注册/卸载，日志监控 |
| v1.1.0 | 2026-09-16 | 新增 ai_api 模式：外部 AI API 全自动填写六要素，不消耗 TeleAgent 积分，支持 DeepSeek/通义千问/Ollama 等 OpenAI 兼容接口 |

> AI生成