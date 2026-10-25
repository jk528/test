# WorkBuddy 签到逆向过程

> 独立文档：记录 WorkBuddy（腾讯 CodeBuddy 桌面版）每日签到接口的逆向分析过程，
> 可脱离原项目单独阅读。

## 一、目标

实现 WorkBuddy 每日签到的自动化：
不打开客户端窗口，直接调用后端 API 完成签到。

## 二、关键结论

| 项 | 值 |
|---|---|
| 活动签到状态 | `POST https://copilot.tencent.com/billing/meter/checkin-activity-status` |
| 签到领取 | `POST https://copilot.tencent.com/billing/meter/daily-checkin` |
| 鉴权方式 | 请求头 `Authorization: Bearer <accessToken>` + `X-User-Id: <uid>` |
| 可选请求头 | `X-Domain: www.codebuddy.cn`；Turing Token 防刷头（缺失也能通过） |
| 请求体 | 固定 `{}` |
| 凭证位置 | `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`<br>（accessToken 为 `$wbEncrypted` **加密信封**；uid 在 `account.uid`） |
| 加密密钥 | 客户端 WorkBuddy.exe 内置 native 绑定<br>`electron_browser_workbuddy_storage.loggerGet()` 返回的<br>`atRestSecretKey`（44 字符 base64） |
| 成功判定 | 状态接口 `today_checked_in: true`；领取云端竞态返回 code=10001 按已签处理 |
| 签名/加密 | 请求本身**无签名**；难点全在本地凭证的加密存储 |

> 注意：auth 目录不在用户主数据目录 `.workbuddy` 下，而是
> `CodeBuddyExtension\Data\Public\auth`——客户端 `sharedDataPath` 指向
> CodeBuddy 扩展体系目录，这是逆向 `getAuthSavePath()` 链路才确认的。

## 三、逆向步骤

### 1. 接口定位：从 UI 字符串顺藤摸瓜

客户端业务代码打包在 `resources\app.asar`（Electron，约 300MB）。
直接搜 `checkin` 命中近两千处全是 `checking` 噪声；有效姿势是搜 UI 独有
中文字符串「连续签到」，定位到 i18n 键 `account.checkin.*` 系列，再顺藤摸瓜
找到接口路径与 API 网关（`copilot.tencent.com` 为 prod 环境端点）：

```
/billing/meter/checkin-activity-status   活动状态（连续天数/积分明细）
/billing/meter/daily-checkin             签到领取
```

> 提示：搜 asar 需给 ripgrep 加 `-a` 强制文本模式；asar 被运行中的客户端
> 独占时可用共享读模式（`fs.openSync('r')`）绕过。

### 2. 鉴权头：Bearer + uid 即可，风控头可选

追踪签到调用链 `postCheckin → http.post → buildHeaders(session)`：

```
Authorization: Bearer <accessToken>    // 关键
X-User-Id: account.uid
可选: X-Domain / X-Enterprise-Id / X-Tenant-Id
```

代码里另有 Turing Token（腾讯防刷）注入逻辑，但实现是「有头带，无头照发」，
实测不带同样返回 200。

### 3. token 加密升级：明文 → `$wbEncrypted` 信封

早期版本 auth 文件中 accessToken 是明文 JWT。客户端 2026-09 升级后，
`accessToken` 等字段全部变为：

```json
{ "$wbEncrypted": 1, "envelope": "<base64>" }
```

envelope base64 解码后是 `@genie/at-rest-crypto` 风格的 AES-256-GCM + AAD 结构：

```json
{ "suite": 1, "keyId": "<16位hex>", "nonce": "<base64 12B>",
  "authTag": "<base64 16B>", "ciphertext": "<base64>" }
```

### 4. AAD 组装（sym-v1 field framing，顺序敏感）

逆向 `buildAuthenticatedContextAad()` 还原出（关键常量：`AAD_DOMAIN="WB-AAD\0"`、
格式 ID `"WBEV1"`、scheme `"sym-v1"`、`FRAMING_CODE.field=2`）：

```
"WB-AAD\0" + [0x01]
+ u32be(7)  + "WBEV1"
+ u32be(6)  + "sym-v1"
+ u32be(suite)
+ u32be(16) + keyId
+ [0x02]      ← FRAMING_CODE.field
+ [0x00]      ← encodeOptionalUint64(undefined) = 1 字节 0x00（易漏！）
+ [0x00]      ← final undefined → 0
```

踩坑：`encodeOptionalUint64(undefined)` 输出 **1 字节 `0x00`** 而不是 0 字节，
漏掉会导致 GCM tag 校验失败（`Unsupported state or unable to authenticate data`）。

### 5. 对称密钥来源：native 绑定，不落盘明文

加密密钥（protector）不落盘明文，由 WorkBuddy.exe 内置 native 模块
`electron_browser_workbuddy_storage` 的 `loggerGet()` 提供，返回 JSON 含
`atRestSecretKey`（44 字符 base64）。

突破点：**以 `ELECTRON_RUN_AS_NODE=1` 模式直接用 WorkBuddy.exe 运行普通
Node 脚本，`process._linkedBinding('electron_browser_workbuddy_storage')`
仍然可用**——无需启动完整客户端、无需窗口、不触发单实例锁，实测 1 秒内返回。

密钥派生：`symKey = sha256(atRestSecretKey 字符串的 UTF-8 字节)`（32 字节），
注意是**对字符串本身 hash**，不是 base64 解码后再 hash（踩坑点 2）。
`keyId = sha256(symKey).hex.slice(0,16)`，可与信封中的 `keyId` 字段互相校验。

### 6. 幂等与竞态

签到前先查状态：`today_checked_in=true` 直接跳过。
存在云端竞态：查询时未签、领取时已签（如客户端 UI 先点过），此时领取接口
返回 code=10001，按已签处理即可。领取后复查状态确认。

### 7. 凭证保活与密钥轮换

- accessToken 过期（接口 401）：打开 WorkBuddy 客户端重新登录，auth 文件刷新；
- 客户端再升级可能轮换 `atRestSecretKey`：解密 authTag 校验失败时自动清缓存、
  重新经 native 绑定取新密钥重试一次；仍失败则需重新登录客户端；
- WorkBuddy.exe 不存在（卸载）：自动回退到本地缓存的密钥（`.temp\wb_key.json`）。

## 四、落地调用链

```
%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info
      │  读 $wbEncrypted 信封（accessToken.envelope）与 account.uid
      ▼
WorkBuddy.exe（ELECTRON_RUN_AS_NODE=1）→ native loggerGet() → atRestSecretKey
      │  sha256(secret) 派生 symKey（32B）
      ▼
AES-256-GCM + AAD(WB-AAD\0, sym-v1 field) 解密信封 → accessToken (JWT)
      │
      ▼
拼请求头（Bearer + X-User-Id + X-Domain）
      │
      ▼
POST checkin-activity-status ──► today_checked_in? 已签则结束
      │ 否
      ▼
随机延迟 30~300 秒（防检测，--no-delay 可跳过）
      │
      ▼
POST daily-checkin（领取；code=10001 竞态按已签）
      │
      ▼
再 POST checkin-activity-status 复查
```

- **零依赖**：只用 Node 18+ 内置模块（`fetch` / `crypto` / `fs`）
- **零配置**：凭证、uid、安装路径全部现场自动探测
- **无硬编码路径**：auth 目录由 `%LOCALAPPDATA%` 动态定位，WorkBuddy.exe
  经注册表 InstallLocation + 常见路径候选探测
- **无 Node 也能跑**：入口脚本可用 WorkBuddy.exe 以 `ELECTRON_RUN_AS_NODE=1`
  兜底运行（此模式下 native binding 在本进程内直接可用，连 spawn 都省了）

## 五、合规说明

本逆向仅涉及读取并解密本机自己账号的登录态，调用平台自身的公开接口；
未绕过任何服务端校验。仅限个人学习研究，请遵守平台条款。
