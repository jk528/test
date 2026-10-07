# 不用积分方案 — Windows 任务计划程序自动化

> **版本**：v1.0.0（2026-10-07）
> **性质**：自包含发布包，复制到任意 Windows 电脑即可复现
> **核心特点**：**不消耗 TeleAgent 积分**，纯 Windows 任务计划程序 + Python 脚本

---

## 一、方案对比

| 维度 | 不用积分（本方案） | 用积分（定时任务配置.md） |
|------|-------------------|-------------------------|
| **执行方式** | Windows 任务计划程序跑纯 Python 脚本 | TeleAgent 定时任务唤醒 AI 执行 |
| **积分消耗** | 零 | 每天 1 次 TeleAgent 会话 |
| **六要素质量** | 一般（正则提取，覆盖率约 70%） | 高（AI 精读正文，覆盖率 > 95%） |
| **人工干预** | 零 | 零 |
| **生成耗时** | ~15 秒 | ~2-5 分钟 |
| **外部依赖** | 仅 Python + requests | TeleAgent 桌面端运行中 |
| **适用场景** | 日常自用、对六要素要求不高 | 追求高质量报告 |

**可选升级**：不用积分方案也支持 `ai_api` 模式——调用外部 AI API（如 DeepSeek）填六要素，质量与用积分方案接近，费用约 0.01 元/天，仍不消耗 TeleAgent 积分。

---

## 二、目录结构

```
最新版本\
├── 不用积分\                ← 本文件夹
│   ├── README.md            ← 本文件
│   ├── config\
│   │   └── config.json      ← 配置文件（路径已指向 ../代码/）
│   └── scripts\
│       ├── register_task.ps1    ← 注册 Windows 任务计划程序
│       ├── unregister_task.ps1  ← 卸载任务
│       ├── run_now.ps1          ← 手动立即运行（与任务动作一致）
│       ├── check_status.ps1     ← 查看任务状态与报告
│       ├── run_daily_task.ps1   ← [历史] 旧外壳脚本（多模式分发）
│       └── check_and_merge.ps1  ← [历史] 半自动模式合并检测
└── 代码\                    ← Python 脚本（被本方案调用）
    ├── xwlb_report.py       ← 一键生成器（oneshot 模式入口）
    ├── gen_report_v2.py     ← 基础模块
    ├── gen_report_final.py  ← 分阶段生成（ai_api 模式用）
    ├── fetch_xwlb.py        ← 央视网抓取
    ├── fetch_iqilu.py       ← 齐鲁网抓取
    ├── fill_elements_api.py ← 外部 AI API 填六要素（ai_api 模式用）
    ├── check_md_quality.py  ← 质检
    └── rebuild_archives.py  ← 批量重建历史归档
```

---

## 三、快速配置（4 步）

### 步骤 1：确认 Python 环境

```powershell
python --version                    # 需 3.10+
python -c "import requests"         # 需已安装 requests
```

若缺 requests：
```powershell
python -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
```

记下 Python 完整路径：
```powershell
(Get-Command python).Source
# 例如：C:\Users\用户名\AppData\Local\Programs\Python\Python312\python.exe
```

### 步骤 2：修改配置文件

打开 `不用积分\config\config.json`，修改 `python_exe` 为你的 Python 路径：

```json
{
  "paths": {
    "python_exe": "C:\\Users\\你的用户名\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
  }
}
```

> 其他路径已预置为相对路径（`../代码`、`../../归档`），无需修改。

### 步骤 3：手动验证

```powershell
# 切到 scripts 目录
cd "<你的路径>\最新版本\不用积分\scripts"

# 立即运行一次（生成昨天的报告）
powershell -ExecutionPolicy Bypass -File .\run_now.ps1
# 预期退出码 0 = 成功
```

验证报告已生成：
```powershell
powershell -ExecutionPolicy Bypass -File .\check_status.ps1
# 预期显示"已就位: 新闻联播总结_YYYYMMDD.md"
```

### 步骤 4：注册定时任务

**以管理员身份**运行：

```powershell
# 切到 scripts 目录
cd "<你的路径>\最新版本\不用积分\scripts"

# 注册（每天 05:00 自动执行）
powershell -ExecutionPolicy Bypass -File .\register_task.ps1 -NonInteractive
```

注册成功后，每天 05:00 Windows 任务计划程序自动运行 `xwlb_report.py` 生成昨天的报告。

---

## 四、三种运行模式

### 4.1 oneshot 模式（默认推荐，零成本）

```json
{ "mode": "oneshot" }
```

- 调用 `代码\xwlb_report.py`，单一脚本完成全流程
- 抓取 → 分类 → 正则提取六要素 → 渲染 → 内置自检 → 落盘
- 零外部依赖、零人工干预、零费用
- 六要素由正则提取，覆盖率约 70%（人物/地点/事件较准，原因/方式可能为"—"）

### 4.2 ai_api 模式（可选升级，极低成本）

```json
{
  "mode": "ai_api",
  "modes": {
    "ai_api": {
      "api_key": "你的DeepSeek API Key",
      "api_base_url": "https://api.deepseek.com/v1",
      "api_model": "deepseek-chat"
    }
  }
}
```

- Phase 1：脚本生成 1-5 部分 + 数据源 JSON
- Phase 2：调用外部 AI API 自动填写六要素（~30 秒）
- Phase 3：脚本合并生成完整报告
- 质量与 TeleAgent 手动生成接近，费用约 0.01 元/天
- **不消耗 TeleAgent 积分**

**获取 DeepSeek API Key**：访问 https://platform.deepseek.com 注册后创建，新用户有免费额度。

**也可用本地 Ollama（完全免费）**：
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

### 4.3 semi_auto 模式（半自动，零成本）

```json
{ "mode": "semi_auto" }
```

- Phase 1：脚本自动生成 1-5 部分 + 数据源 JSON
- Phase 2：**人工**用任意 AI 工具填写六要素 JSON
- Phase 3：运行 `check_and_merge.ps1` 自动检测并合并

---

## 五、脚本说明

| 脚本 | 用途 | 使用方式 |
|------|------|---------|
| `register_task.ps1` | 注册 Windows 任务计划程序 | 管理员身份运行；`-NonInteractive` 无人值守 |
| `unregister_task.ps1` | 卸载定时任务 | 管理员身份运行 |
| `run_now.ps1` | 立即运行一次（与计划任务动作一致） | `-TargetDate 20260915` 补跑指定日期 |
| `check_status.ps1` | 查看任务状态 + 报告是否就位 | `-NoPause` 无人值守 |
| `run_daily_task.ps1` | [历史] 旧外壳脚本，支持多模式分发 | 计划任务不再直接调用 |
| `check_and_merge.ps1` | [历史] 半自动模式合并检测 | semi_auto 模式用 |

---

## 六、修改执行时间

编辑 `config\config.json` 的 `schedule.time`：

```json
"schedule": {
  "time": "06:30"    // 改成你想要的时间
}
```

**修改后必须重新注册**（任务计划程序的触发时间在注册时写入，不随配置文件变化）：

```powershell
powershell -ExecutionPolicy Bypass -File .\register_task.ps1 -NonInteractive
```

---

## 七、常见问题

### Q1: 任务到点没运行？

| 检查项 | 方法 |
|--------|------|
| 任务状态 | `check_status.ps1` 或任务计划程序 GUI |
| 电脑是否开机 | 05:00 时电脑需处于运行且用户已登录 |
| 错过补跑 | 已设 `StartWhenAvailable`，恢复后自动补跑 |

### Q2: 报告没生成或很小？

```powershell
# 前台补跑看输出
powershell -ExecutionPolicy Bypass -File .\run_now.ps1
# 看退出码：0=成功 / 1=致命错误 / 2=有 CRITICAL 问题
```

### Q3: oneshot 模式六要素质量不够？

切换到 `ai_api` 模式（见 4.2 节），质量接近 TeleAgent 手动生成，费用约 0.01 元/天。

### Q4: 如何暂停/恢复？

打开"任务计划程序"→ 找到"新闻联播每日总结" → 右键"禁用"/"启用"。

---

## 八、与用积分方案的共存

两套方案可共存于同一项目：

| 方案 | 触发方式 | 输出位置 | 冲突？ |
|------|---------|---------|--------|
| 不用积分 | Windows 任务计划 05:00 | `归档\YYYY年M月\新闻联播总结_YYYYMMDD.md` | 同一文件 |
| 用积分 | TeleAgent 定时 05:00 | 同上 | 同一文件 |

**建议**：只用其中一套。若两套都启用，后执行的会覆盖先执行的（文件 >10KB 时 oneshot 脚本会跳过，但 TeleAgent AI 会备份后覆盖）。

---

## 变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-10-07 | 初版：从 `自动化任务/` 迁移，路径调整为指向 `../代码/`；含 oneshot/auto_v2/semi_auto/ai_api 四种模式；6 个 PowerShell 脚本 + config.json 自包含 |

> AI生成
