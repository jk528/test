# 万兴脑图每日签到（独立模板）

利用 refresh_token 自续命机制，自动完成万兴脑图（MindMaster / EdrawMind）每日签到领 AI 点数。
**不需要账号密码**，凭证不离开本机。纯 Node 零依赖。

## 前置条件

| 条件 | 说明 |
|---|---|
| **首次使用必做** | 在**夸克浏览器**打开 <https://mm.edrawsoft.cn/app>，**退出并重新登录一次**——只有该登录流程（refreshMode=1）才会把 `refresh_token` 写入 Cookie，脚本才能提取。之后脚本每天自动轮换续命，无需再操作 |
| 夸克浏览器 | 已安装（凭证兜底提取的来源；脚本不依赖万兴客户端） |
| Node.js 18+ | 纯刷新路径 18+ 即可；浏览器兜底提取用到了 `node:sqlite`，建议 **22.5+** |
| 管理员权限 | 仅**兜底提取**时需要（用 VSS 卷影绕过浏览器对 Cookie 数据库的独占锁）；已有有效凭证后的日常运行**不需要** |
| Windows | 脚本与计划任务配置均面向 Windows |

> **自续命原理**：`refresh_token` 30 天有效、每次刷新轮换。脚本每次运行先用它换新
> token 并**立即保存**轮换后的新值再签到——只要 30 天内跑过一次即永久有效，
> 每天定时跑则无风险。

## 目录结构

```
万兴脑图每日签到/
├── README.md                    # 本文件（统领）
├── config.json                  # 可选配置：随机延迟范围
├── 注册计划任务.ps1              # 一键注册/卸载每日计划任务
├── scripts/
│   ├── edraw_checkin.js         # 签到主脚本
│   └── run_checkin.cmd          # 入口（自动探测 Node 运行时）
├── config/
│   ├── edraw_config.example.json # 凭证示例（可留空，首次自动回填）
│   └── edraw_config.json        # 真实凭证（运行后自动生成，已在 .gitignore 排除）
├── docs/
│   └── 万兴脑图签到逆向记录.md    # 接口逆向过程（独立文档）
└── logs/                        # 运行日志（注册计划任务后自动生成）
```

## 快速开始（4 步）

```powershell
# 0. 首次使用：夸克浏览器打开 https://mm.edrawsoft.cn/app 退出并重新登录一次

# 1. 以管理员身份打开 PowerShell，手动测试一次（首次需走浏览器提取）
.\scripts\run_checkin.cmd --no-delay

# 2. 注册计划任务（默认每天 00:10）
.\注册计划任务.ps1

# 3. 手动触发验证 + 看日志
Start-ScheduledTask -TaskName "万兴脑图每日签到"
Get-Content .\logs\checkin.log -Tail 20
```

## 配置说明

**config.json**（都可删除，删除后用默认值）：

| 字段 | 默认 | 说明 |
|---|---|---|
| `delayMinSec` | 30 | 随机延迟下限（秒） |
| `delayMaxSec` | 300 | 随机延迟上限（秒） |

**config/edraw_config.json**：凭证文件 `{ "user_id": "...", "refresh_token": "..." }`。
**首次无需手工填写**——留空或不创建均可，脚本会自动从夸克浏览器提取并回填；
之后每次运行自动轮换更新。**该文件含长期凭证，绝不分享/入库**（已加入 .gitignore）。

**计划任务**：`.\注册计划任务.ps1 -Time "09:30"` 改触发时间；`-Remove` 卸载。

**命令行参数**：

| 参数 | 说明 |
|---|---|
| `--no-delay` | 跳过随机延迟（手动测试用） |
| `--status` | 只查询本周签到状态与积分，不执行签到 |

## 常见问题

| 报错 | 原因与处理 |
|---|---|
| `EDCurrent 缺 user_id/refresh_token 字段` | 登录入口不对。必须在夸克浏览器打开 <https://mm.edrawsoft.cn/app> **退出并重新登录**（应用内登录流程才写入 refresh_token） |
| `凭证获取失败 - 未找到刚创建的卷影` 等 VSS 报错 | 兜底提取需**管理员权限**运行；日常有有效 config 时不需要 |
| `token 刷新失败` | refresh_token 已失效（超过 30 天未运行）。重新登录网页版后，以管理员身份再跑一次让脚本重提取 |
| `No Node.js runtime found` | 安装 Node 18+（建议 22.5+） |
| 计划任务秒退码 1 且无日志 | 文件夹路径含空格，移到无空格路径重新注册 |
| `signature is invalid` | 凭证混用了协作服务令牌（见 docs 逆向记录「两个签名域」）；重新从 EDCurrent Cookie 提取即可 |

## 原理简介

签到与刷新接口来自对万兴脑图 APK（DEX strings）与网页版主包的逆向分析，完整过程见
[docs/万兴脑图签到逆向记录.md](docs/%E4%B8%87%E5%85%B4%E8%84%91%E5%9B%BE%E7%AD%BE%E5%88%B0%E9%80%86%E5%90%91%E8%AE%B0%E5%BD%95.md)。简要链路：

```
config/edraw_config.json 读 refresh_token
  → POST goapi.../refresh/token 换新 token + 轮换 refresh_token（先存后用）
  → GET clockin/list 查本周状态（已签则幂等跳过）
  → POST clockin 签到 → GET point 复查积分
```

## 声明

仅供个人学习与研究使用。请遵守万兴平台的使用条款，勿用于批量账号等滥用场景。
