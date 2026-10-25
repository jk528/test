# OfficeAce（果办）每日签到（独立模板）

读取果办客户端本地登录态，通过客户端本地 API 自动完成每日签到领积分。
**不需要账号密码**，凭证不离开本机。纯 Node 零依赖（Node 18+）。

> ⚠️ **重要前置：签到时果办客户端必须处于运行状态！**
> 签到走客户端本地 API（`127.0.0.1`，客户端内嵌服务承载云端凭证签名，
> 无法离线直连）。客户端没启动则签到必然失败——计划任务时间请设在
> 电脑已开机、客户端已启动之后（客户端自身也有整点自动领取，本脚本是
> 兜底 + 确认）。

## 前置条件

| 条件 | 说明 |
|---|---|
| OfficeAce 客户端 | 已安装、**已登录**，且**签到时保持运行**（本地 API 由客户端进程提供） |
| Node.js 18+ | 可选。没装的话 `run_checkin.cmd` 会尝试用 OfficeAce 客户端自带的运行时兜底 |
| Windows | 脚本与计划任务配置均面向 Windows |

## 目录结构

```
OfficeAce每日签到/
├── README.md              # 本文件（统领）
├── config.json            # 可选配置：随机延迟范围
├── 注册计划任务.ps1        # 一键注册/卸载每日计划任务
├── scripts/
│   ├── officeace_checkin.js # 签到主脚本
│   └── run_checkin.cmd     # 入口（自动探测 Node 运行时）
├── docs/
│   └── OfficeAce签到逆向过程.md # 接口逆向过程（独立文档）
└── logs/                  # 运行日志（注册计划任务后自动生成）
```

## 快速开始（3 步）

```powershell
# 1. 启动并登录果办客户端，然后手动测试一次
.\scripts\run_checkin.cmd --no-delay

# 2. 注册计划任务（默认每天 00:10；建议改到客户端已运行的时段，如 -Time "10:00"）
.\注册计划任务.ps1

# 3. 手动触发验证 + 看日志
Start-ScheduledTask -TaskName "OfficeAce每日签到"
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
| `--status` | 只查询签到状态，不执行领取 |

## 常见问题

| 报错 | 原因与处理 |
|---|---|
| `未找到果办登录态文件` | 客户端未安装或未登录，安装并登录即可 |
| `未发现 OfficeAce 本地 API` | **客户端未运行**，启动果办客户端后重试（最常见原因） |
| `本地会话已失效` | 打开 OfficeAce 客户端重新登录（会话 Cookie 有效期约一个月） |
| `No Node.js runtime found` | 安装 Node 18+，或确认 OfficeAce 客户端存在 |
| 计划任务秒退码 1 且无日志 | 文件夹路径含空格，移到无空格路径重新注册 |

会话失效不用改任何配置：重新登录客户端后脚本自动生效。

## 原理简介

签到链路来自对果办客户端的逆向分析，完整过程见
[docs/OfficeAce签到逆向过程.md](docs/OfficeAce签到逆向过程.md)。简要链路：

```
session.cookie 读 DPAPI 加密登录态 → 解密得 oc_sid Cookie
→ 四层策略发现本地 API（runtime 快照 → .env 端口 → 默认端口 → 回环扫描）
→ GET /api/subscription/current 查状态 → POST claim-bonus 领取 → 复查入账
```

## 声明

仅供个人学习与研究使用。请遵守果办（OfficeAce）平台的使用条款，勿用于批量账号等滥用场景。
