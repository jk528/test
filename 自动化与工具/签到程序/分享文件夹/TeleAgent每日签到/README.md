# TeleAgent 每日签到（独立模板）

读取 TeleAgent 客户端本地登录态，自动完成每日签到。**不需要账号密码**，凭证不离开本机。
纯 Node 零依赖（Node 18+；没有装 Node 也能用 TeleAgent 客户端自带运行时或客户端自身兜底运行）。

## 前置条件

| 条件 | 说明 |
|---|---|
| TeleAgent 客户端 | 已安装且**已登录**（脚本只复用本地登录凭证） |
| Node.js 18+ | 可选。没装的话 `run_checkin.cmd` 会依次尝试 TeleAgent 自带 Node 运行时、TeleAgent 客户端自身兜底 |
| Windows | 脚本与计划任务配置均面向 Windows（解密依赖 DPAPI，绑定当前 Windows 用户） |

## 目录结构

```
TeleAgent每日签到/
├── README.md                   # 本文件（统领）
├── config.json                 # 可选配置：随机延迟范围
├── 注册计划任务.ps1             # 一键注册/卸载每日计划任务
├── scripts/
│   ├── teleagent_checkin.js    # 签到主脚本
│   └── run_checkin.cmd         # 入口（自动探测 Node 运行时）
├── docs/
│   └── TeleAgent签到逆向过程.md # 接口逆向过程（独立文档）
└── logs/                       # 运行日志（注册计划任务后自动生成）
```

## 快速开始（3 步）

```powershell
# 1. 确认 TeleAgent 客户端已登录，然后手动测试一次
.\scripts\run_checkin.cmd --no-delay

# 2. 注册计划任务（默认每天 00:10）
.\注册计划任务.ps1

# 3. 手动触发验证 + 看日志
Start-ScheduledTask -TaskName "TeleAgent每日签到"
Get-Content .\logs\checkin.log -Tail 20
```

## 配置说明

**config.json**（都可删除，删除后用默认值）：

| 字段 | 默认 | 说明 |
|---|---|---|
| `delayMinSec` | 30 | 随机延迟下限（秒） |
| `delayMaxSec` | 300 | 随机延迟上限（秒） |

**计划任务**：`.\注册计划任务.ps1 -Time "09:30"` 改触发时间；`-Remove` 卸载。

**命令行参数**：

| 参数 | 说明 |
|---|---|
| `--no-delay` | 跳过随机延迟（手动测试用） |
| `--status` | 只查询签到状态与积分余额，不执行签到 |

## 常见问题

| 报错 | 原因与处理 |
|---|---|
| `未找到 TeleAgent 登录态文件` | 客户端未安装或未登录，打开客户端登录即可 |
| `登录态已过期` | 打开 TeleAgent 客户端重新登录（脚本下次运行自动读取新凭证） |
| `登录态解密失败` | DPAPI 绑定 Windows 用户：换系统用户登录后需在客户端重新登录 |
| `No Node.js runtime found` | 安装 Node 18+，或确认 TeleAgent 客户端存在 |
| 计划任务秒退码 1 且无日志 | 文件夹路径含空格，移到无空格路径重新注册 |

凭证失效不用改任何配置：重新登录客户端后脚本自动生效。

## 原理简介

签到接口与请求头来自对 TeleAgent 客户端的逆向分析，完整过程见
[docs/TeleAgent签到逆向过程.md](docs/TeleAgent签到逆向过程.md)。简要链路：

```
Local State 取 DPAPI 加密主密钥 → 解出 AES 主密钥 → AES-256-GCM 解密 token.json
→ GET v2/checkDayTask 查状态 → GET checkTask?type=daily_login 领取 → 复查状态与余额
```

## 声明

仅供个人学习与研究使用。请遵守 TeleAgent 平台的使用条款，勿用于批量账号等滥用场景。
