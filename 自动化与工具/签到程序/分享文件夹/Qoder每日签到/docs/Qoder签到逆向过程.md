# Qoder 签到逆向过程

> 独立文档：记录 Qoder「每天领 100 Credits」活动 API 直连的逆向分析过程，可脱离原项目单独阅读。

## 一、目标

实现 Qoder（AI IDE，国内版 Qoder CN / 国际版 Qoder）每日 Credits 领取的自动化：
不打开客户端窗口，直接调用后端 API 完成领取。

与其他平台的最大区别：**它是活动制而非固定签到接口**——campaignId 每天变，
且**每日 10:00（UTC+8）才生成当天活动**，必须先查列表再领取，任务时间必须围绕 10:00 设计。

## 二、关键结论

| 项 | 值 |
|---|---|
| 活动状态查询 | `GET https://openapi.qoder.com.cn/sash/api/v1/me/campaigns`（国际版为 `openapi.qoder.sh`） |
| 领取接口 | `POST /sash/api/v1/me/campaigns/<campaignId>/claim` |
| token 刷新 | `POST /api/v1/deviceToken/refresh`，请求体 `{"refresh_token": "drt-…"}` |
| 鉴权方式 | 请求头 `Authorization: Bearer <token>` + 8 个 `Cosy-*` 风控头 |
| 凭证位置 | `%APPDATA%\com.qodercn.app.stable\auth.v1.dat`（国际版 `com.qoder.app.stable`），**v10 AES-256-GCM 加密** |
| 主密钥 | 同目录 `Local State` 的 `os_crypt.encrypted_key`，DPAPI(CurrentUser) 解密得 32 字节 AES-256 密钥 |
| 机器 ID | 同目录 `auth.machine-id`（明文 UUID） |
| 设备指纹 | 客户端 `resources\umid\runtime-info.exe <env> --account-stdin` 桥接生成（国内版 env=0，国际版 env=3） |
| 活动刷新点 | **每日 10:00（UTC+8）**，campaign 的 `startAt` = 当天 10:00 时间戳 |
| 成功判定 | 领取后复查 campaigns，`claimStatus` 全部变为 `CLAIMED` |

## 三、逆向步骤

### 1. 突破口：客户端日志直接给出 API 骨架

Qoder 是 Electron 应用，主进程日志（`%APPDATA%\com.qodercn.app.stable\logs\<时间戳>\main.log`）
的 `[Campaign]` 模块详细记录了每次活动请求的方法、路径与**完整请求头集合**：

```
GET https://openapi.qoder.com.cn/sash/api/v1/me/campaigns
Authorization: Bearer …  Cosy-ClientType: 10  Cosy-Version: 0.3.4
Cosy-MachineOS / Cosy-MachineHostname / Cosy-MachineId
Cosy-MachineToken / Cosy-MachineCode / Cosy-MachineType  User-Agent: Qoder
```

日志同时暴露响应结构：`campaigns[]` 含 `campaignId / campaignKey / actionType / claimStatus / benefit`。

### 2. asar 解包（踩坑：非标头格式）

Qoder 的 `app.asar` 头不是标准 8 字节格式（Chromium Pickle 变体）：JSON 长度在偏移 @12、
JSON 本体在 @16、文件数据区基址 = 8 + @4。按标准格式读会错位 8 字节。解包后关键文件是
`out/main/index.js`（主进程全部逻辑）。

### 3. 登录态解密：v10 + DPAPI 主密钥（Chromium 同体系）

`auth.v1.dat` 由 Electron `safeStorage` 加密：

```
Local State → os_crypt.encrypted_key(base64，前 5 字节 "DPAPI")
  → DPAPI CurrentUser 解密 → 32 字节 AES-256 主密钥
auth.v1.dat = "v10"(3B) + nonce(12B) + 密文 + GCM tag(16B)
  → AES-256-GCM 解密 → 明文 JSON
```

明文结构：`{ token: "dt-…"(30 天), refreshToken: "drt-…"(1 年), expiresAt, user: {id, name} }`。

token 刷新接口还原自主进程 `performRefresh`：`POST /api/v1/deviceToken/refresh`。
脚本策略：token 剩余寿命 < 3 天时主动刷新，成功后**加密写回 auth.v1.dat**
（tmp+rename 原子写 + 保留 3 份 .bak 备份，与客户端写法一致，不产生写竞争）。

### 4. 风控头：runtime-info.exe 桥接（无法伪造，必须桥接）

`Cosy-MachineToken/Code/Type` 由客户端自带的 native 程序实时生成：

```
> echo {"account":"<userId>"} | runtime-info.exe 0 --account-stdin
{"machineToken":"…(96字符)","machineType":"…","machineCode":"…","vmInfo":{…}}
```

- 风控身份按**账号**绑定（stdin 传 account JSON），客户端每小时自动刷新一次
- `environment` 参数：国内版=0，国际版=3
- 这是 Qoder 风控强度远高于其他平台的原因：每次签到都要 spawn 该程序实时生成设备指纹，
  **卸载客户端即失去签到能力**

### 5. 领取接口在哪：最终在活动页 JS 里找到

**asar 里搜不到领取接口**（daily-credit / credits/claim / claimCampaign 均 0 命中）。
原因：领取动作写在活动 Web 页里。活动页地址来自日志响应的 `campaignUrl`
（`https://openapi.qoder.com.cn/growth-page/activity-iframe`），其 JS 托管在阿里云 CDN。
在该 JS 中确认领取路径正则：`/^\/sash\/api\/v1\/me\/campaigns\/([^/]+)\/claim$/`，POST 方法。

桌面端领取走同源 XHR + 服务端校验 Cosy-MachineToken——活动页自身的阿里云风控 JS
（sufei_data / AWSC）无需破解，只要 9 个请求头齐全即可直连。

### 6. 活动数据结构与「今日」判定

```json
{
  "campaignId": "01a0bb11-…", "campaignKey": "act-20260920-044",
  "actionType": "CLAIM_BENEFIT",           // 还有 VIEW_DETAILS（宣传位，不可领）
  "startAt": 1789869600,                    // = 当天 10:00 UTC+8（每日刷新点）
  "claimStatus": "CLAIMABLE",               // CLAIMABLE / CLAIMED
  "benefit": { "kind": "CREDITS", "amount": 100, "validity": { "days": 30 } }
}
```

`campaignKey` 内嵌日期，`startAt` = 当天 10:00 时间戳。脚本据此区分三种情况：
- 有 `CLAIMABLE` → 领取
- 全部 `CLAIMED` 且存在 `startAt >= 今天 10:00` 的活动 → 「今日已签到」
- 全是昨天的活动 → 「今日活动尚未刷新」，跳过**不算失败**（等 10:30 的任务来领）

### 7. 幂等性确认

先查 campaigns 再决定是否领取；重复触发、手动补跑均安全。

## 四、落地调用链

```
auth.v1.dat 读加密登录态
      │  Local State → DPAPI 主密钥 → AES-256-GCM 解密
      ▼
token 临期(<3天)？ → POST deviceToken/refresh → 加密写回 auth.v1.dat（含备份）
      │
      ▼
runtime-info.exe 生成 Cosy-MachineToken/Code/Type（失败仅警告）
      │
      ▼
GET campaigns（401/403 → 强制刷新 token 重试一次）
      │
      ▼
过滤 actionType=CLAIM_BENEFIT
      ├── 有 CLAIMABLE → 随机延迟 30~300 秒 → POST claim → 复查
      ├── 全部 CLAIMED 且有今日活动 → 「今日已签到」结束
      └── 全是昨日活动 → 「活动未刷新」跳过（非失败）
```

- **零依赖**：只用 Node 18+ 内置模块（`fetch` / `crypto` / `fs` / DPAPI 经 powershell 子进程）
- **零配置**：版本（国内/国际）自动探测、版本号从安装目录 package.json 现取、凭证自动解密
- **无硬编码路径**：`%APPDATA%` / `%LOCALAPPDATA%` 动态定位

## 五、凭证生命周期与运维

| 项 | 值 | 运维含义 |
|----|-----|---------|
| token（dt-…） | 30 天 | 客户端在线时自动续期；脚本临期（<3天）也会自动刷新 |
| refreshToken（drt-…） | 1 年 | 一年内哪怕客户端长期不开，脚本也能自续 |
| 彻底失效 | 打开 Qoder 重新登录一次 | 生成新 auth.v1.dat，脚本无需任何改动 |
| 换机器/重装系统 | DPAPI 主密钥不可迁移 | 必须重新登录客户端 |
| 卸载 Qoder | 失去 runtime-info.exe | 风控头无法生成，签到失效 |

## 六、合规说明

本逆向仅涉及读取并解密本机自己账号的登录态、桥接客户端自带的设备指纹程序，
调用平台自身的公开接口；未绕过任何服务端校验（风控头照实生成提供）。
仅限个人学习研究，请遵守平台条款。
