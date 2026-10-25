# 天翼云盘每日签到（独立模板）

复用浏览器登录态 Cookie，自动完成天翼云盘（cloud.189.cn）每日签到领空间。**Cookie 失效时脚本会自动从夸克浏览器重新提取**，日常零维护。
纯 Node 零依赖（Node 22.5+，推荐 Node 24；浏览器提取用到内置 `node:sqlite`）。

## 前置条件

| 条件 | 说明 |
|---|---|
| 夸克浏览器已登录 cloud.189.cn 网页版 | **核心依赖**：Cookie 自动提取与失效续期都靠它；换浏览器需改脚本内路径常量 |
| Node.js 22.5+（推荐 24） | 用到内置 `fetch` 与 `node:sqlite` |
| Windows | 浏览器 Cookie 解密依赖 DPAPI（绑定当前 Windows 用户），脚本与计划任务均面向 Windows |

## 目录结构

```
天翼云盘每日签到/
├── README.md                    # 本文件（统领）
├── config.json                  # 可选配置：随机延迟范围
├── 注册计划任务.ps1              # 一键注册/卸载每日计划任务
├── config/
│   ├── tianyi_config.example.json    # 凭证模板（复制为 tianyi_config.json 填写）
│   └── tianyi_config.json            # 你的真实凭证（自建，已被 .gitignore 排除）
├── scripts/
│   ├── tianyi_checkin.js        # 签到主脚本（含浏览器 Cookie 自动提取）
│   └── run_checkin.cmd          # 入口（自动探测 Node 运行时）
├── docs/
│   └── 天翼云盘签到逆向过程.md   # 接口逆向过程（独立文档，含设备锁 -133 教训）
└── logs/                        # 运行日志（注册计划任务后自动生成）
```

## 快速开始（3 步）

```powershell
# 1. 夸克浏览器登录 https://cloud.189.cn 网页版，然后建凭证文件
Copy-Item .\config\tianyi_config.example.json .\config\tianyi_config.json
#    cookie 字段可留空（脚本会自动提取并回写），手动测试一次
.\scripts\run_checkin.cmd --no-delay

# 2. 注册计划任务（默认每天 00:10）
.\注册计划任务.ps1

# 3. 手动触发验证 + 看日志
Start-ScheduledTask -TaskName "天翼云盘每日签到"
Get-Content .\logs\checkin.log -Tail 20
```

## 配置说明

**config/tianyi_config.json**（凭证，已被 .gitignore 排除，绝不入库）：

| 字段 | 必填 | 说明 |
|---|---|---|
| `cookie` | 推荐 | 浏览器登录 cloud.189.cn 后的 Cookie；**留空也行**——脚本会自动从夸克浏览器提取并回写本文件 |
| `username` / `password` | 可选 | 手机号 + 密码，仅作 Cookie 与自动提取都失败时的兜底。**注意：开启设备锁的账号会触发短信二次验证（result=-133），密码链路无法全自动** |

环境变量可覆盖：`TIANYI_COOKIE` / `TIANYI_USERNAME` / `TIANYI_PASSWORD`。

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
| `--status` | 只验证登录态有效性，不执行签到 |

## 常见问题

| 报错 | 原因与处理 |
|---|---|
| `未找到天翼云盘凭证` | 未建 `config\tianyi_config.json`，按上方步骤创建（cookie 可留空） |
| `浏览器提取的 Cookie 缺少 COOKIE_LOGIN_USER` | 夸克浏览器未登录 cloud.189.cn 网页版，登录后重跑 |
| `浏览器 Cookie 提取失败` | 多为卷影/权限问题，用**管理员权限**的终端手动跑一次；确认是夸克浏览器 |
| `设备ID不存在，需要二次设备校验`（-133） | 账号开了设备锁，密码登录被撞停；保持夸克浏览器登录态走 Cookie 链路即可 |
| 提示图形验证码 | 属风控，网页端手动登录解除后再运行 |
| `No Node.js runtime found` | 安装 Node 22.5+ |
| 计划任务秒退码 1 且无日志 | 文件夹路径含空格，移到无空格路径重新注册 |

签到幂等：今日已签时接口返回 `isSign=true`，脚本视为成功（退出码 0）。
Cookie 有效期经验值数月~一年，改密码即失效；失效后脚本自动重新提取，浏览器仍登录即可。

## 原理简介

密码登录链路（RSA 加密）与 Cookie 签到接口来自开源社区方案与实测，
完整过程（含设备锁 -133 撞墙记录、浏览器 Cookie 提取链路）见
[docs/天翼云盘签到逆向过程.md](docs/天翼云盘签到逆向过程.md)。简要链路：

```
config/tianyi_config.json 读 Cookie → GET mkt/userSign.action 签到
      │ Cookie 失效
      ▼
夸克浏览器 Cookie 库自动提取（VSS 卷影 + DPAPI + AES-GCM 解密）→ 回写配置 → 重试签到
      │ 提取也失败
      ▼
账号密码 RSA 登录兜底（可能触发设备锁二次验证，需人工）
```

## 声明

仅供个人学习与研究使用。请遵守天翼云盘平台的使用条款，勿用于批量账号等滥用场景。
Cookie 等同登录态，配置文件绝不提交公开仓库。
