---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'c259df3f-b381-42e2-ab0b-61342bfcae6e'
  PropagateID: 'c259df3f-b381-42e2-ab0b-61342bfcae6e'
  ReservedCode1: 'f2164687-cc3d-4a28-b383-9960fa2251a7'
  ReservedCode2: 'f2164687-cc3d-4a28-b383-9960fa2251a7'
---

# WorkBuddy (CodeBuddy) 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-09-17（v1 明文 token）／**2026-10-04（v2 加密 token 重新逆向）**
> 目标：逆向 WorkBuddy 桌面客户端的签到功能，实现后台 API 直连签到
> 结论：**已成功**。v1 明文方案实测连续签到成功；v2 加密方案解密链路已跑通并实测 HTTP 200
> WorkBuddy = 腾讯 CodeBuddy 桌面版（AI 编程助手），产品域名 copilot.tencent.com

> **【v2 重大变更】** 客户端 2026-09-21 升级后（asar 297MB→302MB），
> `workbuddy-desktop.info` 中的 accessToken 从**明文 JWT** 改为 **`$wbEncrypted` 加密信封**
> （AES-256-GCM，AAD `WB-AAD\0` sym-v1 field），旧脚本直接读 token 拿到空值 → 网关 401。
> 已重新逆向新增 native 解密链路，见「八、v2 升级：token 加密与解密链」。

---

## 一、最终结果速览

### 交付文件

| 文件 | 说明 |
|------|------|
| `workbuddy_get_token.js` | **v2 新增**：解密工具（经 WorkBuddy.exe 原生绑定解密 accessToken，输出 JSON） |
| `checkin_all.js` | v2 统一四平台签到脚本（WorkBuddy 部分内置 v2 解密链） |
| `run_checkin_all.cmd` | Windows 执行入口（4 平台统一入口） |
| `本文件` | 逆向研究全记录 |

> 说明：v1 时代的 `workbuddy_checkin.js` / `run_workbuddy_checkin.cmd` 独立脚本
> 自 2026-09-21 起已合并进 `checkin_all.js` / `run_checkin_all.cmd`（四平台统一调度）。

### v2 实测输出

```
[WorkBuddy] 今日已签到。连续 3 天，今日积分 100，每日可领 100
```

解密后的 accessToken 调 `/billing/meter/checkin-activity-status` → HTTP 200，
返回 `active:true, today_checked_in:true, streak_days:3, total_credits:300`。

### 三套签到方案对照（v2 更新）

| 维度 | TraeWork | TeleAgent | WorkBuddy（v2） |
|------|----------|-----------|------------------|
| 产品归属 | 字节跳动 | 中电信人工智能 | 腾讯 |
| token 加密 | AES-128-CBC + SHA-512 派生 + 混淆常量表 | Chromium OSCrypt v10（DPAPI + AES-256-GCM） | **v1 明文 → v2 `$wbEncrypted` 信封（AES-256-GCM + AAD）** |
| 解密难度 | 中（逆向混淆算法） | 中（DPAPI + AES-GCM 两步） | 中（需调 WorkBuddy.exe 原生绑定取密钥） |
| API 网关 | api.trae.cn | agent.teleai.com.cn | copilot.tencent.com |
| 签到方法 | POST claim | GET checkTask?type=daily_login | POST daily-checkin |
| 风控 | req_source=2 + 数字设备 ID | 无签名 | Turing Token（可选，无也通过） |
| 客户端依赖 | 不需要 | 不需要 | **需要 WorkBuddy.exe 存在**（取 native 密钥） |

---

## 二、逆向思路全流程

### 第 1 步：定位安装与数据目录

| 目录 | 内容 |
|------|------|
| `%LOCALAPPDATA%\Programs\WorkBuddy\` | 安装目录，`resources\app.asar`（302MB，Electron 打包） |
| `%USERPROFILE%\.workbuddy\` | 主数据目录（会话、项目、插件、keyblob、数据库等） |
| `%USERPROFILE%\.workbuddy\app\` | Electron userData（`--user-data-dir` 参数指向） |
| `%LOCALAPPDATA%\CodeBuddyExtension\` | **auth session 存储根目录（关键！）** |

> auth 目录不在 `.workbuddy` 下，因为 `sharedDataPath` 指向 `CodeBuddyExtension\Data\Public`。
> 这是通过逆向 asar 中的 `getAuthSavePath()` → `sharedDataPath` → `basePath` → `EXTENSION_DATA_DIR_NAME = "CodeBuddyExtension"` 才找到的。

### 第 2 步：从 asar 中找签到接口

**搜索策略**：跳过通用关键词（checkin/points 噪声太大），直接搜 UI 独有中文字符串「连续签到」定位功能模块，再顺藤摸瓜找 API 路径。

从「连续签到」上下文找到 i18n 键 `account.checkin.*` 系列，再搜 `daily-checkin` 找到接口路径：

```
/billing/meter/daily-checkin             ← 签到/领取（POST，body: {}）
/billing/meter/checkin-status            ← 签到状态（POST）
/billing/meter/checkin-activity-status   ← 活动状态（POST，含连续天数/积分明细）
```

### 第 3 步：定位 API 网关

搜 `copilot.tencent.com` 在 asar 中的出现位置：

```
DEV_ENV_ENDPOINTS = {
    prod: "https://copilot.tencent.com",
    staging: "https://staging.codebuddy.cn"
};
// 运行时: daemonState.getEndpoint() || "https://copilot.tencent.com"
```

### 第 4 步：鉴权头分析

追踪签到调用链 `postCheckin → http.post` → `buildHeaders(session)`：

```
Authorization: `Bearer ${auth.accessToken}`   // 关键
X-User-Id: account.uid
可选: X-Domain, X-Enterprise-Id, X-Tenant-Id, X-Domain
```

**发现**：鉴权只需 `Authorization: Bearer <JWT>` + `X-User-Id`，无签名/无时间戳/无 nonce。

### 第 5 步：Turing Token 风控分析

v2 接口调用 `buildHeadersWithTuringToken` 会额外注入 Turing Token（腾讯防刷），但 `postCheckin` 的实现是「有头带，无头照发」。实测确认：不带 Turing Token 请求同样返回 200。

### 第 6 步（v1）：定位 token 存储

从 `restore()` 方法追踪到：`%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`，
v1 是**明文 JSON**（`auth.accessToken` 直接可用）。此方案在 v2 已失效，详见「八」。

### 第 7 步：接口实测

| 接口 | 方法 | 实测结果 |
|------|------|---------|
| `/billing/meter/checkin-activity-status` | POST `{}` | 200，`active:true, today_checked_in:true, streak_days:3, daily_credit:100` |
| `/billing/meter/checkin-status` | POST `{}` | 200，通用签到状态 |
| `/billing/meter/daily-checkin` | POST `{}` | 200，领取成功 |

---

## 三、遇到的问题与解决方案（v1+v2）

| # | 问题 | 原因 | 解决方案 |
|---|------|------|---------|
| 1 | `rg` 搜索 asar 报 binary file matches | asar 含二进制段 | 加 `-a` 强制文本模式 |
| 2 | `checkin` 命中 1989 处全是 `checking` | 通用词噪声 | 换 UI 独有中文字符串「签到」当 anchor |
| 3 | `.workbuddy` 目录下找不到 auth 文件 | auth 在 `CodeBuddyExtension` 目录 | 逆向 `getAuthSavePath` 链路才找到 |
| 4 | asar 被进程占用无法直接打开 | WorkBuddy 运行时独占 asar | Node `fs.openSync('r')` 共享读模式；或 rg（默认共享读） |
| 5 | 多行函数体 rg 匹配只输出首行 | asar 换行格式 | `rg -b` 字节偏移 + Node `fs.readSync` 切片读取 |
| 6 | `EXTENSION_DATA_DIR_NAME` 不是 "WorkBuddy" | WorkBuddy 底层是 CodeBuddy 扩展体系 | 搜常量定义 `"CodeBuddyExtension"` |
| 7 | `checkin-status` 与 `checkin-activity-status` 数据不一致 | 含义不同（通用 vs 活动） | 以 `checkin-activity-status` 为准 |
| 8 | 担心 Turing Token 缺失被风控 | 腾讯系通常强风控 | 看代码：无头也照发 → 实测 200 通过 |
| **9** | **v2：accessToken 读取为空、接口 401** | **客户端升级，token 改为 `$wbEncrypted` 加密信封** | **重新逆向解密链（见第八节）** |
| **10** | **v2：AES-GCM 解密认证失败** | **AAD 中 `encodeOptionalUint64(undefined)` 输出 1 字节 `0x00`（不是 0 字节）** | 修正 AAD 组装，解密成功 |

---

## 四、生产脚本架构（v2）

```
run_checkin_all.cmd → checkin_all.js（四平台统一）
                              │
    ┌─────────────────────────┤ WorkBuddy 段
    │ 1. wbFindAuthFile()      │   确认登录态存在
    │ 2. wbGetToken()          │   调 WorkBuddy.exe 运行 workbuddy_get_token.js
    │                          │     （ELECTRON_RUN_AS_NODE=1）
    │                          │     native loggerGet() → atRestSecretKey
    │                          │     symKey=sha256(secret) → AES-GCM 解密 → {token,uid}
    │ 3. POST checkin-activity-status
    │    today_checked_in=true → "今日已签到" 退出(0)
    │ 4. POST daily-checkin（领取）
    │ 5. 复查状态 → 输出结果
    └──────────────────────────────────────────
```

---

## 五、接口清单

网关：`https://copilot.tencent.com`

| 用途 | 方法 + 路径 | 请求体 | 备注 |
|------|------------|--------|------|
| 活动签到状态 | POST `/billing/meter/checkin-activity-status` | `{}` | active/today_checked_in/streak_days/daily_credit/total_credits |
| 签到状态 | POST `/billing/meter/checkin-status` | `{}` | 通用签到概览 |
| 签到领取 | POST `/billing/meter/daily-checkin` | `{}` | 领取每日积分（100） |

必需请求头：

```
Authorization: Bearer <accessToken>    （v2 需解密，见第八节）
Content-Type: application/json
X-User-Id: <uid>
```

可选请求头：

```
X-Domain: www.codebuddy.cn            （auth.domain）
X-Device-Token: <turing_token>        （腾讯防刷，缺失也能通过）
```

---

## 六、排障指南

### 登录态过期

```
现象: 错误：登录态已过期，请打开 WorkBuddy 客户端重新登录
```

打开 WorkBuddy 客户端重新登录，`workbuddy-desktop.info` 会刷新。

### auth 文件不存在

```
现象: 错误：未找到 WorkBuddy 登录态文件
```

检查路径：`%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\`。如目录不存在，说明从未登录过 WorkBuddy。

### v2 解密失败：WorkBuddy.exe 不存在

```
现象: 错误：accessToken 解密失败 - WorkBuddy.exe 不存在
```

WorkBuddy 客户端被卸载/移动时发生。`checkin_all.js` 会回退到 `.temp\wb_key.json` 缓存密钥；
若缓存也失效，需重装/重登 WorkBuddy。

### v2 解密失败：密钥不匹配（客户端再升级）

```
现象: 错误：accessToken 解密失败 - Unsupported state or unable to authenticate data
```

客户端升级可能更换 `atRestSecretKey`（`loggerGet()` 返回值变化）。重新抓取一次密钥即可：

```powershell
$env:ELECTRON_RUN_AS_NODE = "1"
& "$env:LOCALAPPDATA\Programs\WorkBuddy\WorkBuddy.exe" "C:\Users\Administrator\Desktop\定时任务脚本\workbuddy_get_token.js"
```

工具脚本会自动刷新 `.temp\wb_key.json` 缓存。

### 客户端升级后接口变更

```powershell
# 1. 先跑一次看具体报错
& "$env:USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe" "C:\Users\Administrator\Desktop\定时任务脚本\checkin_all.js"

# 2. 若接口变了，从新 asar 里搜索
$rg = "C:\Program Files\TeleAgent\resources\ripgrep\win32-x64\rg.exe"
& $rg -a -o -N "daily-checkin.{0,200}" "C:\Users\Administrator\AppData\Local\Programs\WorkBuddy\resources\app.asar" | Select-Object -First 5
```

### auth 文件路径变化

WorkBuddy 大版本升级可能改变 `EXTENSION_DATA_DIR_NAME`。在 asar 里搜：

```
rg -a -o -N "EXTENSION_DATA_DIR_NAME\s*=\s*[^\s;]{0,50}" app.asar
```

---

## 七、关键文件路径速查（v2）

| 文件 | 路径 |
|------|------|
| 签到脚本（统一） | `C:\Users\Administrator\Desktop\定时任务脚本\checkin_all.js` |
| WorkBuddy 解密工具 | `C:\Users\Administrator\Desktop\定时任务脚本\workbuddy_get_token.js` |
| 签到入口 | `C:\Users\Administrator\Desktop\定时任务脚本\run_checkin_all.cmd` |
| auth session | `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info` |
| 客户端代码包 | `%LOCALAPPDATA%\Programs\WorkBuddy\resources\app.asar` |
| 主数据目录 | `%USERPROFILE%\.workbuddy\` |
| 密钥容器 keyblob | `%USERPROFILE%\.workbuddy\keyblob` |
| 密钥缓存（脚本自用） | `%USERPROFILE%\.workbuddy\connectors\<uid>\.master.key`（connector 用，非全局） |

---

## 八、v2 升级：token 加密与解密链（2026-10-04 重新逆向）

### 8.1 现象与判断

客户端 09-21 升级后：
- `workbuddy-desktop.info` 中 `accessToken` / `refreshToken` / `nickname` / `phoneNumber`
  全部变成 `{ "$wbEncrypted": 1, "envelope": "<base64>" }` 结构；
- 旧脚本 `raw.auth.accessToken` 读到 `undefined`（字段是对象不是字符串）；
- 带旧 token 请求网关 → **HTTP 401**（APISIX 拦截）。

### 8.2 信封格式

envelope base64 解码后：

```json
{
  "suite": 1,
  "keyId": "9127dea1b440a7...",   // 16 位小写 hex（实际以文件为准）
  "nonce": "<base64 12B>",
  "authTag": "<base64 16B>",
  "ciphertext": "<base64>"
}
```

这是 `@genie/at-rest-crypto`（GitHub ciphertext 风格）的 **AES-256-GCM + AAD** 方案。

### 8.3 逆向定位加密实现

asar 里定位 `$wbEncrypted` 的判定与处理：

```
isStandardEncryptedFieldWrapper(value)  → 判定加密字段
ProtectedFieldCodec.open()              → 解密入口（field framing）
AtRestCrypto.seal()/open()              → AES-256-GCM 核心
buildAuthenticatedContextAad()          → AAD 组装
```

关键常量：

| 常量 | 值 |
|------|-----|
| `AAD_DOMAIN` | `"WB-AAD\0"`（ascii 7 字节） |
| `STANDARD_FORMAT_ID.field` | `"WBEV1"` |
| scheme | `"sym-v1"` |
| suite | `1` |
| `FRAMING_CODE.field` | `2` |
| key 派生 | `deriveAtRestKeyId(key) = sha256(key).hex.slice(0,16)` |

**AAD 组装（sym-v1 field，顺序敏感）**：

```
AAD_DOMAIN
+ [0x01]
+ u32(7)  + "WBEV1"
+ u32(6)  + "sym-v1"
+ u32(1)
+ u32(16) + keyId
+ [0x02]                          ← FRAMING_CODE.field
+ [0x00]                          ← encodeOptionalUint64(undefined) = 1B 0x00（易漏！）
+ [0x00]                          ← final undefined → 0
```

> 踩坑：`encodeOptionalUint64(undefined)` 返回 **1 字节 `0x00`** 而不是 0 字节，
> 漏掉它会导致 GCM tag 校验失败（`Unsupported state or unable to authenticate data`）。

### 8.4 对称密钥来源（关键突破）

A 密钥（protector）不落盘明文，而是由 **WorkBuddy.exe 内置 native 绑定**提供：

```js
// main 进程 bootstrap
loadMainCredentialProtectionBootstrap(
  getAtRestEncryptionBuildPolicy(),
  () => electron.workbuddyStorage.loggerGet(),   // ← native API
  { configDir: ... }
);
```

native 模块 `electron_browser_workbuddy_storage`（编译在 WorkBuddy.exe 里）
提供 `loggerGet()`，返回 JSON：

```json
{
  "version": 1,
  "atRestSecretKey": "Sik9U5aXhCdwTVEwsEySDOmDoB9r9ntFxVHF1fst9LQI=",
  "atRestDeveloperPublicKey": { "alg": "RSA-OAEP-256", "id": "...", "key": "..." }
}
```

> 突破点：**Electron 的 `ELECTRON_RUN_AS_NODE=1` 模式下，直接以
> `WorkBuddy.exe` 运行普通 Node 脚本，`process._linkedBinding('electron_browser_workbuddy_storage')`
> 仍然可用**！无需启动完整客户端，无需窗口。

### 8.5 解密链路（完整）

```
atRestSecretKey
   │  sha256(utf8)
   ▼
symKey（32 字节）  ─── keyId 校验: deriveAtRestKeyId(symKey) === envelope.keyId
   │  AES-256-GCM（AAD = 8.3 节组装）
   ▼
accessToken 明文 JWT（RS256，~1325 字符）
```

> 注意：`normalizeAtRestKeyPayload` 中 key = `sha256(atRestSecretKey 字符串的 UTF-8 字节)`，
> 不是 base64 解码后再 hash（踩坑点 2）。

### 8.6 解密工具与生产集成

`workbuddy_get_token.js`（Node，无第三方依赖）：

```
WorkBuddy.exe workbuddy_get_token.js   （ELECTRON_RUN_AS_NODE=1）
  1. loggerGet() → atRestSecretKey（失败则读 .temp\wb_key.json 缓存）
  2. sha256 派生 symKey
  3. 读 auth 文件 → 解密 accessToken.envelope
  4. 输出一行 JSON: {"token":"eyJ...","uid":"15ce..."}
```

`checkin_all.js` 中 WorkBuddy 段通过 `execFileSync(WB_EXE, [WB_TOKEN_SCRIPT], {env:{ELECTRON_RUN_AS_NODE:'1'}})` 调用，解析 JSON 后照常签到。

### 8.7 兜底方案

- WorkBuddy.exe 不存在（卸载）→ 读 `.temp\wb_key.json` 缓存的 `atRestSecretKey`；
- 客户端再升级导致密钥轮换 → 重跑工具自动刷新缓存；
- 登录态过期 → 打开 WorkBuddy 重新登录（auth 文件刷新）。

---

*本文档由逆向分析生成，基于 WorkBuddy v2.5.2→最新客户端 app.asar 静态分析 + native 绑定实测 + 接口实测。*

> AI生成