# 库库AI 每日签到（独立模板）

通过百度 Cookie（BDUSS）直连 `kuku.baidu.com` 活动平台，自动完成库库AI 每日签到
（10 积分/天 + 连签里程碑奖励）。**不需要库库AI 客户端**，一次配置 Cookie 长期使用。
纯 Node 零依赖（Node 18+；没有装 Node 也能用库库AI 客户端自身兜底运行）。

> **🔒 安全提示**：BDUSS 等同账号密码。真实凭证只写在 `config\kuku_config.json`，
> 该文件已被 `.gitignore` 排除，**绝不提交到 Git、绝不分享给他人**。

## 前置条件

| 条件 | 说明 |
|---|---|
| 百度账号 | 已开通库库AI（用浏览器登录过一次 kuku.baidu.com 即可） |
| 手动取一次 Cookie | 见下方「快速开始」第 1 步，浏览器 F12 即可完成，约 1 分钟 |
| Node.js 18+ | 可选。没装的话 `run_checkin.cmd` 会尝试用库库AI 客户端自带的运行时兜底 |
| Windows | 脚本与计划任务配置均面向 Windows |

## 目录结构

```
库库AI每日签到/
├── README.md                        # 本文件（统领）
├── 注册计划任务.ps1                  # 一键注册/卸载每日计划任务（默认 00:10）
├── config/
│   ├── kuku_config.example.json     # 配置示例（空字段 + 获取说明）
│   └── kuku_config.json             # 真实凭证（自行创建，.gitignore 排除）
├── scripts/
│   ├── kuku_checkin.js              # 签到主脚本
│   └── run_checkin.cmd              # 入口（自动探测 Node 运行时）
├── docs/
│   └── 库库AI签到逆向过程.md          # 接口逆向过程（独立文档）
└── logs/                            # 运行日志（注册计划任务后自动生成）
```

## 快速开始（3 步）

```powershell
# 1. 配置凭证（只需一次）：
#    a. 浏览器登录 kuku.baidu.com（或百度文库/网盘等任一百度系站点）
#    b. F12 开发者工具 → Application/应用程序 → Cookies → 复制 BDUSS 值
#       （同一页面还可复制 PTOKEN / STOKEN，可选）
#    c. 复制 config\kuku_config.example.json 为 config\kuku_config.json，填入 BDUSS
Copy-Item .\config\kuku_config.example.json .\config\kuku_config.json
notepad .\config\kuku_config.json

# 2. 手动测试一次
.\scripts\run_checkin.cmd --no-delay

# 3. 注册计划任务（默认每天 00:10）
.\注册计划任务.ps1

# 验证
Start-ScheduledTask -TaskName "库库AI每日签到"
Get-Content .\logs\checkin.log -Tail 20
```

## 配置说明

**config\kuku_config.json**（从 example 复制；除 `bduss` 外全部可留空/删除）：

| 字段 | 必填 | 说明 |
|---|---|---|
| `bduss` | **是** | 百度账号 BDUSS，浏览器 Cookie 获取；有效期通常数月到数年 |
| `stoken` | 否 | genflowpro 的 STOKEN；留空且填了 `ptoken` 时脚本自动换取 |
| `ptoken` | 否 | passport 凭证，用于自动换取 STOKEN |
| `uid` | 否 | 账号 uk 数字串，留空由服务端按 BDUSS 识别 |
| `version` | 否 | 客户端版本号伪装（默认 1.6.28） |
| `user_agent` | 否 | 自定义 User-Agent（默认带 GenFlowPro 标识） |
| `delayMinSec` | 否 | 随机延迟下限（秒，默认 30） |
| `delayMaxSec` | 否 | 随机延迟上限（秒，默认 300） |

> 说明：延迟配置直接并入 `kuku_config.json`，不再单独提供 config.json。
> 环境变量 `KUKU_BDUSS` / `KUKU_STOKEN` / `KUKU_UID` 可覆盖文件值（CI 场景用）。

**计划任务**：`.\注册计划任务.ps1 -Time "09:30"` 改触发时间；`-Remove` 卸载。

**命令行参数**：

| 参数 | 说明 |
|---|---|
| `--no-delay` | 跳过随机延迟（手动测试用） |
| `--status` | 只查询签到状态（连签天数/里程碑），不执行签到 |
| `--lottery` | 签到后尝试抽奖（试验性：jsToken 风控未完全逆向，失败不影响签到） |

## 常见问题

| 报错 | 原因与处理 |
|---|---|
| `未找到库库AI签到凭证（bduss 为空）` | 还没创建 `config\kuku_config.json`，按快速开始第 1 步配置 |
| `登录态已失效（errno -6）` | BDUSS/STOKEN 过期或复制错误，重新从浏览器 Cookie 取一遍更新配置 |
| `kuku_config.json 解析失败` | JSON 格式错误（多了注释/逗号），或带 BOM——用 VS Code 另存为 UTF-8 |
| `No Node.js runtime found` | 安装 Node 18+，或安装库库AI 客户端 |
| 计划任务秒退码 1 且无日志 | 文件夹路径含空格，移到无空格路径重新注册 |

## 原理简介

签到接口来自对库库AI 客户端（GenFlowPro，Electron）app.asar 的逆向分析，完整过程见
[docs/库库AI签到逆向过程.md](docs/库库AI签到逆向过程.md)。简要链路：

```
kuku_config.json 读 BDUSS → (可选) passport 换 STOKEN
→ POST /act/v2/kukuai30/homepage 查状态 → 未签则 POST signin → 复查连签天数
```

为什么凭证要手动提供：客户端把登录态交给 native 层（bnusdk.dll）加密存储，
本地文件无明文可提取；BDUSS 是百度全站通用 Cookie，浏览器取一次即可，稳定性反而更好。

## 声明

仅供个人学习与研究使用。请遵守百度/库库AI 平台的使用条款，勿用于批量账号等滥用场景。
