---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'a7813dcf-fe28-4072-a181-5365ac37fdb6'
  PropagateID: 'a7813dcf-fe28-4072-a181-5365ac37fdb6'
  ReservedCode1: 'cef781c0-5eaa-4afe-a43e-a377a1f0be1e'
  ReservedCode2: 'cef781c0-5eaa-4afe-a43e-a377a1f0be1e'
---

# Qoder 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-09-20
> 目标：让 Qoder（Qoder CN 桌面版）「每天领 100 Credits」活动领取脱离客户端窗口，改为后台 API 直连
> 结论：**已成功**。独立任务「Qoder积分签到」已部署（每天 10:30±30分钟），统一签到 checkin_all.js 已升级为 5 平台；API 直连实测通过（campaigns 查询 HTTP 200，脚本退出码 0）
> 本文档记录完整的逆向思路、踩坑与解决方案，供日后出问题时排查参考

---

## 一、最终结果速览

| 项目 | 值 |
|------|-----|
| 独立定时任务 | `Qoder积分签到`（每天 **10:30**，触发器随机延迟 PT30M）—— Qoder 签到唯一入口 |
| 统一签到任务 | `统一积分签到`（每天 01:00，4 平台；与 Qoder 无关，2026-09-21 起） |
| 执行入口 | `桌面\定时任务脚本\run_qoder_checkin.cmd` |
| 核心脚本 | `桌面\定时任务脚本\qoder_checkin.js`（Node.js，模块化导出，独立任务唯一入口） |
| Node 运行时 | `%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe`（复用 TeleAgent 自带） |
| 日志文件 | `桌面\定时任务脚本\qoder_checkin.log`（UTF-8 追加写入） |
| 活动规则 | 「每天领 100 Credits」：**每日 10:00（UTC+8）刷新**，100 Credits/天，领取后 30 天有效 |
| 实测输出 | `今日已签到。act-20260920-044 奖励 100 CREDITS`（退出码 0） |

**为什么任务时间设在 10:30**：活动每天 10:00 才生成当天的新活动（campaignKey 带当天日期），凌晨签到会扑空。这与另外 4 个平台（凌晨即可签）根本不同，所以 Qoder 单独立任务，不能简单并进 01:00 的统一签到。

---

## 二、逆向思路全流程

整体路线：**客户端日志先行 → asar 结构解析 → 主进程代码定位 → 凭证解密 → 风控头生成 → 活动页 JS 分析（领取接口最终在这里找到）→ API 实测**。全程静态分析 + 只读验证，不抓包、不篡改。

### 第 1 步：定位文件系统布局

| 目录/文件 | 内容 |
|------|------|
| `%LOCALAPPDATA%\Programs\Qoder CN\resources\app.asar` | 139MB 主程序包（Electron） |
| `%LOCALAPPDATA%\Programs\Qoder CN\resources\umid\runtime-info.exe` | **设备指纹桥接程序**（风控头来源，关键） |
| `%APPDATA%\com.qodercn.app.stable\` | 国内版用户数据目录 |
| `...\auth.v1.dat` | **加密登录态**（v10 格式，420 字节） |
| `...\auth.machine-id` | 机器 ID（明文 UUID） |
| `...\Local State` | Chromium 主密钥（`os_crypt.encrypted_key`，DPAPI） |
| `...\main.sqlite` | 应用数据库（**不含凭证**，只有会话/聊天记录等） |
| `...\logs\<时间戳>\main.log` | 主进程日志（信息量极大，逆向突破口） |
| `%APPDATA%\com.qoder.app.stable\` | 国际版数据目录（本机未登录，脚本作兜底支持） |

> 国际版与国内版双线并存：国内版 openapi.qoder.com.cn / runtime-info env=0；国际版 openapi.qoder.sh / env=3。

### 第 2 步：从日志直接拿到 API 骨架（比 asar 更快）

`main.log` 里 `[Campaign]` 模块日志详细记录了每次活动请求，直接暴露了：

```
[Campaign] 活动状态请求发出 {"method":"GET","origin":"https://openapi.qoder.com.cn",
  "path":"/sash/api/v1/me/campaigns","clientType":10,
  "requestHeaders":{"Authorization":"[redacted]","Cosy-ClientType":"10",
  "Cosy-Version":"0.3.4","Cosy-MachineOS":"<present>","Cosy-MachineHostname":"<present>",
  "Cosy-MachineId":"<present>","Cosy-MachineToken":"[redacted]",
  "Cosy-MachineCode":"<present>","Cosy-MachineType":"<present>","User-Agent":"Qoder"}}
```

由此确认：
- 活动状态接口：`GET https://openapi.qoder.com.cn/sash/api/v1/me/campaigns`
- 完整请求头集合：Authorization Bearer + 8 个 `Cosy-*` 风控头
- 日志还给出响应结构：`uid / showCampaign / claimable / campaignUrl / campaigns[]`（campaignId、campaignKey、actionType、claimStatus、benefit）

**日志还还原了用户手动领取的完整过程**：14:19:10 claimable=true → 14:19:50 claimable=false（用户在活动弹窗里点了领取）→ 14:19:55 关闭弹窗。这说明领取发生在 campaignUrl 指向的 Web 活动页里，领取后状态立即变为 CLAIMED。

### 第 3 步：asar 解包（踩坑：Qoder 的 asar 头格式与标准不同）

标准 asar 头是 `[UInt32 jsonLen][json]`（偏移 4/8），但 Qoder 的 app.asar 实测十六进制：

```
04 00 00 00 | B0 02 12 00 | AC 02 12 00 | A8 02 12 00 | 7B 22 66 69 6C 65 73 ...
=4          = 1180336     = 1180332     = 1180328     = {"files"...
```

实际格式（Chromium Pickle）：

| 偏移 | 含义 |
|------|------|
| @0 | UInt32 = 4（固定） |
| @4 | UInt32 = pickle 大小（= 8 + jsonLen 对齐后） |
| @8 | UInt32 = jsonLen + 4 |
| @12 | **UInt32 = JSON 实际长度** |
| @16 | JSON 字符串开始 |
| 8 + @4 | 文件数据区基址 |

按 @4 读 jsonLen、@8 读 JSON 会错位 8 字节（开头出现乱码），按 @12/@16 读即正确。自写 `asar_tool.js`（无依赖，list/extract/grep 三命令）解析文件表，关键文件：
- `out/main/index.js`（8.1MB，主进程全部逻辑）
- `out/renderer/assets/index-DDa3WwIe.js`（19MB，渲染层）

### 第 4 步：主进程代码里的 Campaign 服务

在 main_index.js 中定位 `campaignMainService`：

- 常量 `zJt = "/sash/api/v1/me/campaigns"`，缓存 5 分钟（`$Jt = 300*1e3`），启动后自动打开活动弹窗（Surface）
- `getStatus()` → GET campaigns，401/403 时 `invalidateAccessToken`
- 响应解析 `r1t()`：`campaignUrl` 必须是 HTTPS 且 host 属于 `qoder.sh / qoder.com / qoder.com.cn`（含子域）才被信任
- 请求头构造：`createRequestHeaders()` → `nativeCampaignRequestService.createAuthorizedHeaders(...)`

`xJt()` 最终头构造（完整还原）：

```js
{
  Authorization: `Bearer ${token}`,
  "Cosy-ClientType": "10",              // 桌面端常量 clientType
  "Cosy-Version": clientVersion,          // "0.3.4"
  "Cosy-MachineOS": "x86_64_windows",     // `${arch}_${platform}`
  "Cosy-MachineHostname": 主机名,
  "Cosy-MachineId": auth.machine-id,      // machineIdentityMainService → 数据目录 auth.machine-id
  "Cosy-MachineToken": 风控token,         // ↓ 第 6 步
  "Cosy-MachineCode": 风控码,
  "Cosy-MachineType": 风控类型,
  "User-Agent": "Qoder"
}
```

另发现注入机制：活动 Web 页面发 XHR 时，主进程通过 `session.webRequest.onBeforeSendHeaders`（`authorize()`，仅对 campaignOrigin/apiBaseUrl 白名单域）自动补齐上述头——**活动页自己不带任何凭证**。

### 第 5 步：登录态解密（与 TeleAgent 同体系，直接复用思路）

`auth.v1.dat` 读写类 `Vte`（main_index.js @1017333 附近）：

```js
load()  { return JSON.parse(safeStorage.decryptString(readFileSync("auth.v1.dat"))) }
save(t) { writeFileSync("auth.v1.dat", safeStorage.encryptString(JSON.stringify(t))) }
```

明文结构（schemaVersion=1）：

```json
{
  "schemaVersion": 1,
  "token": "dt-…",                  // 27字符，30 天有效
  "refreshToken": "drt-…",           // 28字符，1 年有效
  "expiresAt": "2026-10-20T14:18:56Z",
  "refreshTokenExpiresAt": "2027-09-15T14:18:56Z",
  "user": { "id": "01a0b9ed-…", "name": "…", "phone": "…" }
}
```

解密链路（复用 TeleAgent 的方法，实测一次通过）：
1. `Local State` → `os_crypt.encrypted_key`（base64，前 5 字节 "DPAPI"）
2. DPAPI CurrentUser 解密 → 32 字节 AES-256 主密钥
3. `auth.v1.dat` = `v10` 前缀(3B) + nonce(12B) + 密文 + GCM tag(16B)
4. AES-256-GCM 解密 → 明文 JSON

> 差异备忘：TeleAgent 把主密钥放在自身数据目录的 `Local State`，Qoder 相同；两者 v10 格式字节布局一致，`taDecryptMasterKey/taDecryptToken` 代码可平移。

**刷新接口**（`performRefresh` @1063041）：

```
POST https://openapi.qoder.com.cn/api/v1/deviceToken/refresh
Content-Type: application/json
{"refresh_token": "drt-…"}
→ { "device_token"|"token", "refresh_token", "expire_time"|"expires_at", "refresh_token_expire_time"|… }
```

脚本策略：token 剩余寿命 < 3 天时主动刷新；刷新成功后**写回 auth.v1.dat**（v10 加密 + tmp/rename 原子写 + 3 份 .bak 备份），与客户端共享最新凭证、不产生竞争。401/403 时强制刷新重试一次。

### 第 6 步：风控头生成（runtime-info.exe 桥接）

`nativeRiskIdentityMainService`（`XJt` 类）+ `$We`（@934936）：

```js
const exe = join(runtimeDirectory, "runtime-info.exe");   // resources\umid\ 下
// Windows: spawn(exe, [String(environment), "--account-stdin"], {stdio:["pipe","pipe","pipe"]})
//          stdin 写入 {"account": userId}\n
//          stdout 第一行 JSON 即机器身份
```

实测调用（国内版 env=0）：

```
> echo {"account":"01a0b9ed-…"} | runtime-info.exe 0 --account-stdin
{"machineToken":"P1gAWji_…（96字符）","machineType":"617475549101b90a71",
 "machineCode":"2169ca4b0079ce5a34","vmInfo":{"isVm":false,…},"accountOutcome":"success"}
```

- 超时 25 秒，输出限 1MB，首行换行符截断——脚本照抄
- `environment` 参数：国内版=0，国际版=3（`dZe(e,t)`：`t==="global"?3:0`）
- 风控身份按**账号**绑定（stdin 传 account），每账号每小时自动刷新一次（`WJt=3600*1e3`）

### 第 7 步：领取接口在哪（最终在活动页 JS 里找到）

**asar 里没有领取接口**（搜 daily-credit / credits/claim / claimCampaign 均为 0 命中）。原因：领取动作写在活动 Web 页里。

活动页地址（来自日志响应）：`https://openapi.qoder.com.cn/growth-page/activity-iframe`，其 JS 在阿里云 CDN：`https://g.alicdn.com/qbase/qoder/0.0.705/growth-page/activity-iframe/activity-iframe.js`（240KB）。

在该 JS 里找到 qe 函数的分流逻辑：

```js
e === "qoderwake"    // 手机 App：postMessage 转发给宿主代发
  ? (listCampaigns → {type:"listCampaigns"}；领取路径正则 match → {type:"claimCampaign", campaignId})
  : Fe(t, n)          // 其他宿主（含 Qoder Desktop）：直接 fetch，头由 Electron 注入
```

**领取接口就此确认**：

```
POST https://openapi.qoder.com.cn/sash/api/v1/me/campaigns/<campaignId>/claim
```

（`/^\/sash\/api\/v1\/me\/campaigns\/([^/]+)\/claim$/`，POST 方法）

活动数据结构（实测响应）：

```json
{
  "campaignId": "01a0bb11-…", "campaignKey": "act-20260920-044",
  "actionType": "CLAIM_BENEFIT",           // 还有 VIEW_DETAILS（订阅宣传，不可领）
  "startAt": 1789869600,                    // = 当天 10:00 UTC+8（每日刷新点）
  "endAt": 1789955940,
  "claimStatus": "CLAIMABLE",               // CLAIMABLE / CLAIMED / 其他(不可领)
  "benefit": { "kind": "CREDITS", "amount": 100,
               "validity": { "mode": "RELATIVE_DAYS", "days": 30 } }
}
```

`campaignKey` 内嵌日期（act-20260920-044），配合 `startAt` 可判断"这是今天的活动还是昨天的残留"——脚本据此区分「今日已领」与「活动未刷新」。

### 第 8 步：API 实测

| 项 | 结果 |
|----|------|
| DPAPI 主密钥解密 | OK（32 字节） |
| auth.v1.dat 解密 | OK（token/refreshToken/user 全部读出） |
| runtime-info.exe 风控头 | OK（machineToken/Code/Type） |
| GET campaigns | **HTTP 200**，完整活动列表（当日活动 CLAIMED，因用户 14:19 已手动领取） |
| Claim 逻辑 | 正确跳过非 CLAIMABLE 活动（当天已领） |
| 脚本退出码 | 0 |

---

## 三、生产脚本设计（qoder_checkin.js）

```
qoder_checkin.js
├── QD_VARIANTS           国内版/国际版探测（有 auth.v1.dat 的优先；API 域名/env 参数/版本号）
├── dpapiMasterKey()       Local State → DPAPI → 32B 主密钥（powershell.exe 子进程）
├── decryptV10/encryptV10  v10+nonce+ct+tag 的 AES-256-GCM 解密/加密（加密用于刷新后写回）
├── writeAuthAtomic()      tmp+rename 原子写回 + 3 份 .bak 备份（与客户端写法一致）
├── riskIdentity()         runtime-info.exe <env> --account-stdin（stdin 传账号）
├── refreshToken()         POST /api/v1/deviceToken/refresh → 写回 auth.v1.dat
├── checkinQoder()
│   ├── 解密登录态 → 打印账号与 token 到期时间
│   ├── token 临期(<3天) → 自动刷新
│   ├── 风控头获取（失败仅警告，不中断）
│   ├── GET campaigns（401/403 → 强制刷新重试一次）
│   ├── 过滤 actionType=CLAIM_BENEFIT
│   │   ├── CLAIMABLE → POST claim → 复查
│   │   ├── 全 CLAIMED 且有今日活动(startAt>=今天10:00) → 「今日已签到」
│   │   └── 全是昨日活动 → 「今日活动尚未刷新（每日 10:00 刷新），跳过」
│   └── 复查 claimStatus 全变 CLAIMED → 签到成功
└── module.exports + require.main 守卫（被 checkin_all.js require 复用）
```

关键防御性设计：
- **不与客户端抢写**：正常情况只读登录态；仅刷新时写回，且用客户端同款 tmp+rename 模式
- **国际版兜底**：QD_VARIANTS 数组遍历，国内版优先
- **失败细分会报**：登录态失效/领取失败/复查未通过分别提示，避免笼统 error
- **--no-delay 测试模式**：跳过随机延迟立即执行

---

## 四、定时任务架构（单一专责）

| 任务 | 时间 | Qoder 行为 |
|------|------|-----------|
| `Qoder积分签到`（05） | 每天 10:30±30min | **唯一入口**：活动 10:00 刷新后完成当日领取 |

> **架构调整记录**（2026-09-21）：2026-09-20 曾把 Qoder 以"探测分支"并入统一签到（02 号凌晨 01:00），但当天活动尚未生成，该分支每天必然输出"活动未刷新，跳过"后空跑，纯冗余。现已移除：统一签到回归 4 平台，Qoder 完全由本任务专责，职责单一。脚本判定基于 startAt 与当天 10:00 UTC+8 的时间戳比较，不依赖死时间；若未来活动刷新时间改变，只需调整本任务触发时间。

防检测两层随机化与其他平台一致：触发器 PT30M + 脚本内 30~300 秒。

---

## 五、踩坑与经验

| # | 坑 | 解法 |
|---|-----|------|
| 1 | Qoder asar 头不是标准 8 字节格式，JSON.parse 失败输出 2.3MB 报错 | 读十六进制实测：jsonLen 在 @12、JSON 在 @16、数据区 = 8+@4 |
| 2 | asar 里搜不到领取接口 | 领取逻辑在活动 Web 页（CDN JS），顺着日志里的 campaignUrl 下载页面 JS 才找到 claim 路径正则 |
| 3 | `/turns/claim`（290+ 处）是**远程任务认领**，不是积分领取 | 积分领取必须认准 `/me/campaigns/<id>/claim` 且 POST |
| 4 | credits-summary / seat-activity 只是"账户指标"（总积分/连续活跃天数），不是签到状态接口 | 签到状态以 campaigns 的 claimStatus 为准 |
| 5 | 活动页有阿里云风控 JS（g.alicdn.com/secdev/sufei_data + AWSC/et_f.js） | 桌面端领取走的是同源 XHR + 服务端校验 Cosy-MachineToken，无需破解页面风控；只要风控头齐全即可直连 |
| 6 | run_qoder_checkin.cmd 中文注释在 GBK 代码页下乱码，导致任务把注释当命令执行 | **cmd 批处理一律用英文注释**（现有 4 个 cmd 同款风格的原因） |
| 7 | 从自动化会话 Start-ScheduledTask 触发的运行，进程被会话回收 ^C 杀掉（0xC000013A），日志出现 `^C` | 环境已知现象（与 03/04 号 Git 同步任务偶发同源）；**定时自然触发不受影响**（01:09 统一签到、06:15 Git 同步均长期 0）；验证时用一次性触发器等自然触发，或前台直跑 cmd |
| 8 | Node 24 在 Windows 上 process.exit() 偶发 uv 句柄断言噪音 | 用 `process.exitCode` 自然退出代替显式 exit |
| 9 | 日志读取乱码 | qoder_checkin.log 是 UTF-8 字节流，PowerShell 需 `Get-Content -Encoding UTF8`；且 Node stdout 重定向下块缓冲，运行中日志为空属正常，进程结束一次性落盘 |

---

## 六、凭证生命周期与运维要点

| 项 | 值 | 运维含义 |
|----|-----|---------|
| token（dt-…） | 30 天 | 客户端在线时自动续期；脚本临期（<3天）也会自动刷新 |
| refreshToken（drt-…） | 1 年 | 一年内哪怕客户端长期不开，脚本也能自续 |
| 过期兜底 | 打开 Qoder CN 重新登录一次 | 生成新 auth.v1.dat，脚本无需任何改动 |

- 登录态位置：`%APPDATA%\com.qodercn.app.stable\auth.v1.dat`
- 脚本写回时自动留 `.bak-*` 3 份备份，误写可回滚
- **换机器/重装系统后**：DPAPI 主密钥不可迁移，必须重新登录客户端（脚本会明确提示）
- 卸载 Qoder CN 会同时失去 runtime-info.exe（风控头生成），签到随之失效——脚本给出独立提示

---

## 七、与另外 4 个平台的横向对比

| 维度 | TraeWork/TraeCN | TeleAgent | WorkBuddy | **Qoder** |
|------|-----------------|-----------|-----------|-----------|
| 登录态加密 | AES-128-CBC + SHA-512 | v10 + DPAPI 主密钥 | 明文 JSON | **v10 + DPAPI 主密钥（同 TeleAgent）** |
| 请求头 | Cloud-IDE-JWT + 设备头 | X-Token + 时间戳/nonce | Bearer + X-User-Id | **Bearer + 9 个 Cosy-\* 风控头** |
| 风控强度 | 低 | 中 | 低 | **高（设备指纹桥接 + 账号绑定）** |
| 签到窗口 | 全天 | 全天 | 全天 | **每日 10:00 后** |
| token 自续 | 否（客户端负责） | 否（客户端负责） | 否 | **是（脚本可主动刷新并写回）** |
| 签到形态 | checkin_credits/claim | checkTask | daily-checkin | **campaigns/<id>/claim（活动制）** |

Qoder 的三点独特性：
1. **活动制而非固定签到接口**——campaignId 每天变，必须先查列表再领取
2. **风控头依赖客户端自带的 native 桥接程序**——不像其他平台纯 HTTP 头可伪造，Qoder 每次都要 spawn runtime-info.exe 实时生成设备指纹
3. **时区敏感**——每日 10:00（UTC+8）刷新，任务时间设计必须围绕这个点

---

## 八、本次产物清单

| 文件 | 位置 | 说明 |
|------|------|------|
| `qoder_checkin.js` | `桌面\定时任务脚本\` | Qoder 模块（模块化导出设计，由 05 号独立任务唯一使用） |
| `run_qoder_checkin.cmd` | `桌面\定时任务脚本\` | 入口批处理（英文注释 + `chcp 65001`） |
| `qoder_checkin.log` | `桌面\定时任务脚本\` | 运行日志（UTF-8） |
| `checkin_all.js`（更新） | `桌面\定时任务脚本\` | 统一签到（4 平台；2026-09-21 移除 Qoder 探测分支） |
| 计划任务 `Qoder积分签到` | 任务计划程序 | 每天 10:30±30min |
| `05_Qoder积分签到（每天10点30分±30分钟）\` | `桌面\定时任务总览\` | 副本 + README 留档 |
| `02_统一积分签到（…）\`（更新） | `桌面\定时任务总览\` | 4 平台副本 + README（Qoder 副本已移除） |
| `五平台积分签到逆向研究总集.md` | `桌面\定时任务脚本\` | 总集升级（原四平台总集） |
| 逆向中间产物 | `彩读分析\.temp\qoder\` | asar_tool.js / ctx.js / 提取的 main_index.js 等（临时，可清） |

> AI生成