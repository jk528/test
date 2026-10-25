# 多平台每日签到 · 独立模板合集

10 个平台的每日自动签到模板，**每个文件夹都是一个完全独立、可直接拷走使用的小工具**。
源自一个自用多平台签到系统的生产代码，逐平台拆分 + 重构 + 实测。

## 一、平台总览

| 模板 | 建议触发时间 | 凭证机制 | 特殊前置条件 |
|---|---|---|---|
| [Trae每日签到](Trae%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | 客户端加密登录态（AES 自动解密） | Trae CN 客户端已登录 |
| [TeleAgent每日签到](TeleAgent%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | 客户端 token（AES-GCM 解密） | TeleAgent 客户端已登录 |
| [WorkBuddy每日签到](WorkBuddy%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | 客户端 auth 文件（密钥自动获取） | WorkBuddy 客户端登录过即可 |
| [CodeArts每日签到](CodeArts%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | DPAPI + AES-GCM 解密本地库 | 客户端已登录；**Node 22.13+** |
| [OfficeAce每日签到](OfficeAce%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | 本地 API 调用 | **果办客户端必须正在运行** |
| [库库AI每日签到](%E5%BA%93%E5%BA%93AI%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | 百度 BDUSS（手填一次） | 需从浏览器取 BDUSS 填 config |
| [Qoder每日签到](Qoder%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | **10:40** | 客户端 auth.v1.dat | **活动每日 10:00 才重置，不能凌晨跑** |
| [百度网盘每日签到](%E7%99%BE%E5%BA%A6%E7%BD%91%E7%9B%98%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | BDUSS（手填一次） | 需从浏览器取 BDUSS 填 config |
| [天翼云盘每日签到](%E5%A4%A9%E7%BF%BC%E4%BA%91%E7%9B%98%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | 浏览器 Cookie（失效自动重提取） | 夸克浏览器已登录 cloud.189.cn |
| [万兴脑图每日签到](%E4%B8%87%E5%85%B4%E8%84%91%E5%9B%BE%E6%AF%8F%E6%97%A5%E7%AD%BE%E5%88%B0/README.md) | 00:10 | refresh_token 自续命闭环 | 首次需在夸克浏览器登录 mm.edrawsoft.cn/app |

想用哪个平台，**只需把对应文件夹拷走**，彼此零依赖。

## 二、统一模板结构（每个文件夹都是这几件套）

```
<平台>每日签到/
├── README.md               # 统领：前置条件 / 3 步上手 / 配置 / 排障
├── 环境检查清单.md          # 运行环境 + 基础配置逐项核对表（缺失附解决方案）
├── config.json             # 延迟等可选配置（含密钥的平台改放 config/ 并 gitignore）
├── 注册计划任务.ps1         # 一键注册/卸载 Windows 每日计划任务
├── .gitignore              # 排除日志与真实凭证
├── scripts/
│   ├── run_checkin.cmd     # 入口：自动探测 Node（无 Node 时部分平台可用客户端兜底）
│   └── <platform>_checkin.js  # 签到主脚本（纯 Node 内置模块，零 npm 依赖）
├── docs/
│   └── <平台>签到逆向过程.md  # 该平台的接口逆向记录（独立自包含）
└── logs/                   # 运行日志（注册任务后生成）
```

## 三、通用使用流程（任意模板都一样）

```powershell
# 1. 满足前置条件（登录对应客户端/浏览器，或填好 config）
# 2. 手动测试一次
.\scripts\run_checkin.cmd --no-delay
# 3. 注册每日计划任务
.\注册计划任务.ps1            # 默认时间见上表；可加 -Time "09:30" 自定义
```

所有脚本通用参数：`--no-delay`（跳过随机延迟）、`--status`（只查不签）。
签到全部**幂等**：重复执行/补跑不会出错。

## 四、统一设计原则

| 原则 | 落地 |
|---|---|
| 凭证不出本机 | 只读本机客户端/浏览器的登录态；需要手填的 BDUSS 类凭证放 config 且被 .gitignore 排除 |
| 零硬编码 | 数据目录走 %APPDATA% 探测、安装位置走注册表、版本号现场读取 |
| 零依赖 | 只用 Node 内置模块（fetch/crypto/node:sqlite），无需 npm install |
| 防检测 | 签到前随机延迟 30~300 秒（config.json 可调） |
| 幂等 | 已签到自动跳过，重复触发安全 |
| 失效可自愈 | 凭证过期后重新登录客户端/浏览器即可，无需改配置（万兴为 refresh_token 自动轮换，真正免维护） |

## 五、共性排障

| 现象 | 原因与处理 |
|---|---|
| 计划任务秒退码 1、无日志 | 路径含空格（cmd 引号+重定向解析 bug）→ 移到无空格路径重新注册 |
| `未检测到数据目录` / `登录态已过期` | 对应客户端没登录或登录失效 → 打开客户端重新登录 |
| `No Node.js runtime found` | 装 Node 18+（CodeArts 需 22.13+）；部分模板可用自家客户端兜底 |
| Qoder 领不到 | 触发时间早于 10:00，模板默认 10:40 就是为了避开 |

## 六、分享方式

- 单平台分享：直接压缩对应文件夹发出去
- 对方机器要求：Windows + 对应客户端已登录（个别需手填一次 config）
- 逆向细节见各模板 docs/ 下的独立文档，可单独阅读

> 声明：所有模板仅供个人学习研究，凭证均为使用者本机自己的登录态，请遵守各平台使用条款。
