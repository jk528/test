# 百度网盘每日签到（独立模板）

复用浏览器登录态 Cookie，自动完成百度网盘会员每日签到 + 每日答题。**不需要账号密码**，凭证不离开本机。
纯 Node 零依赖（Node 18+）。

## 前置条件

| 条件 | 说明 |
|---|---|
| 浏览器已登录 pan.baidu.com | 脚本只复用你复制的 Cookie（BDUSS 等） |
| Node.js 18+ | 必需（用到内置 `fetch`） |
| Windows | 脚本与计划任务配置均面向 Windows |

## 目录结构

```
百度网盘每日签到/
├── README.md                    # 本文件（统领）
├── config.json                  # 可选配置：随机延迟范围
├── 注册计划任务.ps1              # 一键注册/卸载每日计划任务
├── config/
│   ├── baidupan_config.example.json  # 凭证模板（复制为 baidupan_config.json 填写）
│   └── baidupan_config.json          # 你的真实 Cookie（自建，已被 .gitignore 排除）
├── scripts/
│   ├── baidupan_checkin.js      # 签到主脚本
│   └── run_checkin.cmd          # 入口（自动探测 Node 运行时）
├── docs/
│   └── 百度网盘签到逆向过程.md   # 接口逆向过程（独立文档）
└── logs/                        # 运行日志（注册计划任务后自动生成）
```

## 快速开始（3 步）

```powershell
# 1. 填写凭证：复制模板并粘贴 Cookie
Copy-Item .\config\baidupan_config.example.json .\config\baidupan_config.json
#    编辑 baidupan_config.json，填入 cookie，然后手动测试一次
.\scripts\run_checkin.cmd --no-delay

# 2. 注册计划任务（默认每天 00:10）
.\注册计划任务.ps1

# 3. 手动触发验证 + 看日志
Start-ScheduledTask -TaskName "百度网盘每日签到"
Get-Content .\logs\checkin.log -Tail 20
```

## 配置说明

**config/baidupan_config.json**（凭证，必填，绝不入库）：

| 字段 | 说明 |
|---|---|
| `cookie` | 浏览器登录 pan.baidu.com 后，F12 → 网络 → 任意请求的 Cookie 整段复制（至少含 `BDUSS`/`STOKEN`/`BAIDUID`） |

也可用环境变量 `BAIDUPAN_COOKIE` 覆盖。Cookie 有效期通常数月，改密码/安全设置即失效，失效后重新复制即可。

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
| `--status` | 只查询会员等级与成长值，不执行签到 |

## 常见问题

| 报错 | 原因与处理 |
|---|---|
| `未找到百度网盘签到凭证` | 未建 `config\baidupan_config.json` 或 cookie 为空，按上方步骤填写 |
| `签到失败：errno=-6` 或 `error_code=-6` | Cookie 已失效，重新从浏览器复制 |
| 状态查询失败（Cookie 可能已失效） | 同上，重新复制 Cookie |
| `No Node.js runtime found` | 安装 Node 18+ |
| 计划任务秒退码 1 且无日志 | 文件夹路径含空格，移到无空格路径重新注册 |

签到幂等：今日已签时接口返回 `error_code=421001 repeat signin`，脚本视为成功（退出码 0），重复触发/补跑均安全。

## 原理简介

签到、答题、成长值查询三个接口的调用方式移植自开源项目并对照网页端实测确认，
完整过程见 [docs/百度网盘签到逆向过程.md](docs/百度网盘签到逆向过程.md)。简要链路：

```
config/baidupan_config.json 读 Cookie → GET signin 签到 → getdailyquestion 取答案
→ answerquestion 交卷（答案由接口直接给出）→ membership/user 复查成长值
```

## 声明

仅供个人学习与研究使用。请遵守百度网盘平台的使用条款，勿用于批量账号等滥用场景。
Cookie 等同登录态，请勿分享给他人或提交到公开仓库。
