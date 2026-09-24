---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4cf7082e-dee0-4302-86a5-0d54760edff8'
  PropagateID: '4cf7082e-dee0-4302-86a5-0d54760edff8'
  ReservedCode1: 'd04bec69-c519-4229-a4cd-70ff2d519cfc'
  ReservedCode2: 'd04bec69-c519-4229-a4cd-70ff2d519cfc'
---

# WorkBuddy (CodeBuddy) 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-09-17
> 目标：逆向 WorkBuddy 桌面客户端的签到功能，实现后台 API 直连签到
> 结论：**已成功**。脚本已产出并实测通过（签到成功，连续 2 天，100 积分）
> WorkBuddy = 腾讯 CodeBuddy 桌面版（AI 编程助手），产品域名 copilot.tencent.com

---

## 一、最终结果速览

### 交付文件

| 文件 | 说明 |
|------|------|
| `workbuddy_checkin.js` | 核心签到脚本（Node.js，纯 API 直连） |
| `run_workbuddy_checkin.cmd` | Windows 执行入口 |
| `本文件` | 逆向研究全记录 |

### 实测输出

```
2026/9/17 04:28:38 签到成功！连续 2 天，今日积分 100，每日可领 100
退出码: 0
```

### 三套签到方案对照

| 维度 | TraeWork | TeleAgent | WorkBuddy（本次） |
|------|----------|-----------|------------------|
| 产品归属 | 字节跳动 | 中电信人工智能 | 腾讯 |
| token 加密 | AES-128-CBC + SHA-512 派生 + 混淆常量表 | Chromium OSCrypt v10（DPAPI + AES-256-GCM） | **明文 JSON，无需解密** |
| 解密难度 | 中（逆向混淆算法） | 中（DPAPI + AES-GCM 两步） | **零（直接读文件）** |
| API 网关 | api.trae.cn | agent.teleai.com.cn | copilot.tencent.com |
| 签到方法 | POST claim | GET checkTask?type=daily_login | POST daily-checkin |
| 风控 | req_source=2 + 数字设备 ID | 无签名 | Turing Token（可选，无也通过） |
| 客户端依赖 | 不需要 | 不需要 | 不需要 |

---

## 二、逆向思路全流程

### 第 1 步：定位安装与数据目录

| 目录 | 内容 |
|------|------|
| `%LOCALAPPDATA%\Programs\WorkBuddy\` | 安装目录，`resources\app.asar`（297MB，Electron 打包） |
| `%USERPROFILE%\.workbuddy\` | 主数据目录（会话、项目、插件、数据库等） |
| `%USERPROFILE%\.workbuddy\app\` | Electron userData（`--user-data-dir` 参数指向） |
| `%LOCALAPPDATA%\CodeBuddyExtension\` | **auth session 存储根目录**（关键！） |

> 发现 auth 目录的过程走了弯路——`.workbuddy` 下没有 auth 文件，因为 `sharedDataPath` 指向的是 `CodeBuddyExtension\Data\Public`，不在 `.workbuddy` 下。这是通过逆向 asar 中的 `getAuthSavePath()` → `sharedDataPath` → `basePath` → `EXTENSION_DATA_DIR_NAME = "CodeBuddyExtension"` 才找到的。

### 第 2 步：从 asar 中找签到接口

**搜索策略**：跳过通用关键词（checkin/points 噪声太大），直接搜 UI 独有中文字符串「连续签到」定位功能模块，再顺藤摸瓜找 API 路径。

从「连续签到」上下文找到 i18n 键 `account.checkin.*` 系列，再搜 `daily-checkin` 找到接口路径：

```
/billing/meter/daily-checkin            ← 签到/领取（POST，body: {}）
/billing/meter/checkin-status            ← 签到状态（POST）
/billing/meter/checkin-activity-status   ← 活动状态（POST，含连续天数/积分明细）
```

### 第 3 步：定位 API 网关

搜 `copilot.tencent.com` 在 asar 中的出现位置，找到：

```js
DEV_ENV_ENDPOINTS = {
    prod: "https://copilot.tencent.com",
    staging: "https://staging.codebuddy.cn"
};
// 运行时: daemonState.getEndpoint() || "https://copilot.tencent.com"
```

`billingPrefix` 在基类中返回空串 `""`，所以完整路径直接拼在网关域名后面。

### 第 4 步：鉴权头分析

追踪签到调用链 `postCheckin → http.post` → `buildHeaders(session)`：

```js
buildHeaders(session) {
    const { auth, account } = session;
    return {
        Accept: "application/json",
        Authorization: `Bearer ${auth.accessToken}`,   // 关键
        "Content-Type": "application/json",
        "X-User-Id": account.uid ?? "",
        // 可选: X-Enterprise-Id, X-Tenant-Id, X-Domain
    };
}
```

**发现**：鉴权只需 `Authorization: Bearer <JWT>` + `X-User-Id`，无签名/无时间戳/无 nonce。

### 第 5 步：Turing Token 风控分析

v2 签到接口调用 `buildHeadersWithTuringToken`，额外注入 Turing Token（腾讯防刷系统）：

```js
async buildHeadersWithTuringToken(session) {
    const headers = this.buildHeaders(session);
    const result = await this.getTuringDeviceTokenResult();
    if (result.token) headers[TURING_SHIELD_ID_HEADER] = result.token;
    return headers;
}
```

但 `postCheckin` 的实现是：

```js
async postCheckin(path) {
    const headers = await this.getCheckinRequestHeaders();
    if (headers) return this.http.post(path, {}, { headers });  // 有头: 带
    return this.http.post(path, {});                            // 无头: 照发
}
```

**关键发现**：Turing Token 是**可选风控增强**，没有也照样发请求。实测确认：不带 Turing Token 的请求成功返回 200。

### 第 6 步：定位 token 存储（最曲折的一步）

从 `restore()` 方法追踪：

```
restore() → getAuthSavePath() → path.join(sharedDataPath, "auth", `${id}.info`)
                                    ↓
                         sharedDataPath = basePath + "Data/Public"
                         basePath = AppData/Local + EXTENSION_DATA_DIR_NAME
                         EXTENSION_DATA_DIR_NAME = "CodeBuddyExtension"
```

最终路径：`C:\Users\Administrator\AppData\Local\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`

打开文件后发现是**明文 JSON**，结构：

```json
{
  "account": { "uid": "15ce5697-...", "nickname": "...", "uin": "..." },
  "auth": {
    "accessToken": "eyJhbGciOiJSUzI...",   // JWT，1325 字符
    "refreshToken": "...",
    "domain": "www.codebuddy.cn",
    "expiresAt": ...,
    ...
  }
}
```

**不需要任何解密！** 与 TeleAgent 的 DPAPI + AES-256-GCM 和 Trae 的 SHA-512 + AES-CBC 相比，这是最简单的方案。

### 第 7 步：接口实测

| 接口 | 方法 | 实测结果 |
|------|------|---------|
| `/billing/meter/checkin-activity-status` | POST `{}` | 200，返回 `active:true, today_checked_in:false, streak_days:1, daily_credit:100` |
| `/billing/meter/checkin-status` | POST `{}` | 200，返回签到状态概览 |
| `/billing/meter/daily-checkin` | POST `{}` | 200，签到成功，连续 2 天，100 积分 |

---

## 三、遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|---------|
| 1 | `rg` 搜索 asar 报 "binary file matches" | asar 含二进制段 | 加 `-a` 强制文本模式（同 TeleAgent 经验） |
| 2 | `checkin` 命中 1989 处全是 `checking` | 通用词噪声 | 换 UI 独有中文字符串「连续签到」当锚点 |
| 3 | `.workbuddy` 目录下找不到 auth 文件 | auth 不存在 `.workbuddy` 下，在 `CodeBuddyExtension` 目录 | 逆向 `getAuthSavePath → sharedDataPath → basePath → EXTENSION_DATA_DIR_NAME` 链路才找到 |
| 4 | asar 被进程占用无法直接 `File.Open` | WorkBuddy 运行时独占 asar | 用 Node `fs.openSync('r')` 以共享读模式打开；或用 rg（默认共享读） |
| 5 | 多行函数体 rg 匹配只输出首行 | asar 内换行格式问题 | 改用字节偏移（`rg -b`）+ Node `fs.readSync` 切片读取 |
| 6 | `EXTENSION_DATA_DIR_NAME` 不是 "WorkBuddy" | WorkBuddy 底层是 CodeBuddy 扩展体系 | 搜常量定义 `EXTENSION_DATA_DIR_NAME = "CodeBuddyExtension"` |
| 7 | `checkin-status` 和 `checkin-activity-status` 返回数据不一致 | 两个接口含义不同：前者是通用签到状态，后者是活动专属状态（含连续天数） | 以 `checkin-activity-status` 为准（数据更完整） |
| 8 | 担心 Turing Token 缺失导致风控拦截 | 腾讯系产品通常有强风控 | 看 `postCheckin` 代码：无头也照发 → 实测确认 200 通过 |

---

## 四、生产脚本架构

```
run_workbuddy_checkin.cmd → workbuddy_checkin.js
                              │
    ┌─────────────────────────┤
    │ 1. 定位 auth 文件        │
    │   CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info
    │                         │
    │ 2. 读取明文 JSON         │
    │   accessToken / uid / domain（无需解密）
    │                         │
    │ 3. 查状态 POST checkin-activity-status
    │   today_checked_in=true → 输出"今日已签到"并退出(0)
    │   today_checked_in=false → 继续
    │                         │
    │ 4. 领取 POST daily-checkin
    │                         │
    │ 5. 复查状态              │
    │   confirmed → 输出结果(0) │
    │   未确认 → 输出警告(1)    │
    └─────────────────────────┘
```

---

## 五、接口清单

网关：`https://copilot.tencent.com`

| 用途 | 方法 + 路径 | 请求体 | 备注 |
|------|------------|--------|------|
| 活动签到状态 | POST `/billing/meter/checkin-activity-status` | `{}` | 返回 active/today_checked_in/streak_days/daily_credit/checkin_dates |
| 签到状态 | POST `/billing/meter/checkin-status` | `{}` | 返回通用签到概览 |
| 签到领取 | POST `/billing/meter/daily-checkin` | `{}` | 领取每日积分（100） |

必需请求头：

```
Authorization: Bearer <accessToken>    （JWT，明文 JSON 读取）
Content-Type: application/json
X-User-Id: <uid>                      （account.uid）
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

### 客户端升级后接口变更

```powershell
# 1. 先跑一次看具体报错
& "$env:USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe" "C:\Users\Administrator\Desktop\定时任务脚本\workbuddy_checkin.js"

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

## 七、关键文件路径速查

| 文件 | 路径 |
|------|------|
| 签到脚本 | `C:\Users\Administrator\Desktop\定时任务脚本\workbuddy_checkin.js` |
| 签到入口 | `C:\Users\Administrator\Desktop\定时任务脚本\run_workbuddy_checkin.cmd` |
| auth session | `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info` |
| 客户端代码包 | `%LOCALAPPDATA%\Programs\WorkBuddy\resources\app.asar` |
| 主数据目录 | `%USERPROFILE%\.workbuddy\` |
| 设备 ID | `%USERPROFILE%\.workbuddy\device-id` |

---

*本文档由逆向分析生成，基于 WorkBuddy v2.5.2 客户端 app.asar 静态分析 + 接口实测。*

> AI生成