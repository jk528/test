---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'b1c2d3e4-2414-4369-a066-28d3498dd3ac'
  PropagateID: 'b1c2d3e4-2414-4369-a066-28d3498dd3ac'
  ReservedCode1: '8b59ab4a-ffe3-44a1-9cd6-2095297de88e'
  ReservedCode2: '8b59ab4a-ffe3-44a1-9cd6-2095297de88e'
---

# CodeArts 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-10-13
> 目标：华为云 CodeArts Agent（桌面端，VSCode fork，版本 26.9.900）的「积分福利」每日签到
> 结果：✅ 全链路打通并实测验证（delivery 200 / 今日状态 CONFIRMED 正确判定）
> 配套：`codearts_checkin.js` + `codearts_get_credentials.py` + `codearts_libs/` + `run_codearts_checkin.cmd`
> 方法论：延续 `Electron应用API逆向通用指南.md`（日志先行 → 锚点定位 → 协议还原 → 凭证解密 → 只读实测）

---

## 一、目标概况

| 维度 | 内容 |
|------|------|
| 产品 | 华为云 CodeArts Agent（码道，AI 编码智能体 IDE） |
| 客户端 | VSCode fork（vscodeVersion 1.109.5），版本 26.9.900 |
| 安装目录 | `C:\Program Files\CodeArts Agent\` |
| 代码形态 | **明文**（`resources\app\`，无 asar；扩展为压缩单文件 JS） |
| 数据目录 | `%APPDATA%\codearts-agent\`（VSCode 风格）+ `%USERPROFILE%\.codeartsdoer\`（kernel 数据） |
| API 网关 | `https://snap-access.cn-north-4.myhuaweicloud.com`（policyCenterDomain/snapEngineDomain） |
| 签到形态 | **福利活动制**（ops/campaign）：先查列表再领取，同 Qoder 模式 |
| 每日积分 | 每日签到领 1000 CREDIT（另有邀请/注册/学生认证活动） |
| 鉴权体系 | **华为云 IAM STS 临时凭证（AK/SK/SecurityToken）+ SDK-HMAC-SHA256 签名**——与五平台完全不同 |

## 二、侦察与定位

1. **日志先行**：`%APPDATA%\codearts-agent\logs\<session>\` 发现 `huaweicloud.authentication` 扩展（华为账号登录，本地 HTTP server + 每小时续期）；`HuaweiCloud Authentication.log` 显示 `renew session success` 每小时一次。
2. **锚点**：`rg "签到"` 无命中 → 搜 `checkin`/`welfare` → 命中 `extensions\vscode-codebot\out\extension.js`（10.4MB 压缩单文件）：
   - `welfareDeliveryUrl = ${policyCenterDomain}/v1/ops/delivery`
   - `welfareClaimUrl = .../v1/ops/claim`、`welfareConfirmUrl = .../v1/ops/confirm`、`welfareInviteUrl = .../v1/ops/invite/generate`
   - 业务处理对象 `C4i`：`getWelfareDelivery` / `claimWelfare` / `confirmWelfare` / `generateInviteCode`
3. **域名**：扩展自带 `product.json`（`isCommercialVersion: true, isNewFramework: true`）→ `policyCenterDomain = https://snap-access.cn-north-4.myhuaweicloud.com`（国际版走 `ap-southeast-1`）。
4. **认证架构**：`huaweicloud.authentication` 扩展（`dist\plugin.js` 3.8MB）负责华为账号登录（IAM OAuth2 + **PKCE + DPoP JWE**），凭证经 VSCode SecretStorage 共享给 `vscode-codebot` 扩展。
5. **kernel**：`AgentKernel_Vscode_...exe`（pkg 打包的 Node，`otlp-aksk-exporter` 用同一套凭证签名成功——成为关键的**对照实现来源**）。

## 三、鉴权体系还原（本平台最大特色）

### 3.1 凭证链路

```
华为账号登录（IAM OAuth2 + PKCE + DPoP）
  └─ POST https://sts.cn-north-4.myhuaweicloud.com/v1/oauth2/tokens
       → { credentials: { access_key_id, secret_access_key, security_token, expiration }, refresh_token, ... }
  └─ 认证扩展每小时自动续期（refresh_token 轮换，renew session success）
  └─ 写回 VSCode SecretStorage（键 SYSTEM_HC_USER_INFO → 落盘 secret://）
```

### 3.2 凭证存储与解密（已打通）

- **存储位置**：`%APPDATA%\codearts-agent\User\globalStorage\state.vscdb`（SQLite `ItemTable`）
- **键名**：`secret://{"extensionId":"huaweicloud.authentication","key":"HuaweiCloudSession"}`
- **值格式**：`{"type":"Buffer","data":[...]}`
- **密文结构**：`v10`(3B) + nonce(12B) + ciphertext + tag(16B)——**Chromium OSCrypt，与 TeleAgent/Qoder 同体系**
- **主密钥**：`%APPDATA%\codearts-agent\Local State` → `os_crypt.encrypted_key`（Base64 → 去 `DPAPI` 前缀 → DPAPI Unprotect）→ 32B AES-256-GCM 密钥
- **明文 JSON**：
  ```json
  {
    "account": {"id": "...", "label": "GT-weixin_72705708"},
    "accessKey": "HST...",            // IAM STS 临时 AK（2小时有效）
    "secretKey": "...",               // 配套 SK（40 字符）
    "securitytoken": "hQpjbi1ub3J0aC00...",  // STS token（base64url，内嵌 region+AK）
    "expires_at": "2026-10-13T11:06:36.95Z",
    "domainId": "f8c8...",
    "loginContext": {"pkcePair": {...}, "dpopKeyPair": {...}},
    "refresh_token": "eyJ..."
  }
  ```
- 解密脚本：`codearts_get_credentials.py`（sqlite3 标准库 + ctypes DPAPI + cryptography AESGCM，依赖随 `codearts_libs/`）

### 3.3 请求签名（SDK-HMAC-SHA256）

业务请求头（`Pz()` 生成 + SDK 注入）：

```
x-snap-traceid: <uuid>          # 每次随机
Content-Type: application/json
Agent-Type: PromptCenter
X-Language: zh-cn
X-Security-Token: <securitytoken>
X-Sdk-Content-Sha256: UNSIGNED-PAYLOAD   # ★ kernel exporter 形态：声明 body 不参与校验
X-Sdk-Date: <YYYYMMDDTHHMMSSZ>           # signer 生成
host: snap-access.cn-north-4.myhuaweicloud.com
Authorization: SDK-HMAC-SHA256 Access=<AK>, SignedHeaders=..., Signature=...
```

⚠️ **不要带 `x-auth-token` 头（哪怕是空值）**——APIG 网关看到该头即走 IAM token 认证路径，报 `APIG.0301 decrypt token fail`。客户端 `Pz()` 中该值为空串（HC 版 `Pr()` 返回 `""`），实际传输层被忽略；脚本直接省略。

Canonical Request（与华为云 SDK 一致，从客户端 kernel 原样提取验证）：

```
HTTPMethod \n
CanonicalURI \n          # path 按 / 分段 urlEncode 后 join，末尾补 /
CanonicalQueryString \n  # key,value 各自 urlEncode 后 k=v 拼接再排序；无 query 为空串
CanonicalHeaders \n      # 全部请求头小写排序，k:value\n（值不折叠空白，仅去除首尾）
SignedHeaders \n         # 小写头名分号连接
HexEncode(Sha256(body))  # 有 X-Sdk-Content-Sha256 头则直接用其值（UNSIGNED-PAYLOAD）
```

StringToSign = `SDK-HMAC-SHA256 \n <X-Sdk-Date> \n HexEncode(Sha256(CanonicalRequest))`，Signature = HexEncode(HMAC-SHA256(StringToSign, SK))。

**noEscape 表陷阱（本次最大坑，见第五节）**：urlEncode 的不转义表必须与 kernel 完全一致——`! ' ( ) * - . _ ~` 及字母数字不转义，其余转义。手抄该 256 位数组极易错位且症状隐蔽（错误只出现在含特定字母的路径上）。

## 四、签到业务接口（全部实测验证）

### 4.1 活动列表

```
GET https://snap-access.cn-north-4.myhuaweicloud.com/v1/ops/delivery?channel=IDE
→ 200 {"code":0,"message":"ok","data":{"channel":"IDE","serverTime":...,"items":[...]}}
```

items 结构（实测 2026-10-13）：

| campaignId | title | type | benefit | triggerEvent/Mode | claimable | status |
|-----------|-------|------|---------|-------------------|-----------|--------|
| 1 | **每日签到领1000积分** | USER_LOGIN | 1000 CREDIT | user.login / MANUAL_CLAIM | false（已领） | **CONFIRMED** |
| 2 | 学生认证领4000积分 | STUDENT_CERTIFIED | 4000 CREDIT | student.certified / MANUAL_CLAIM | false | null |
| 3 | 推荐码上有礼 | INVITE_USER | 1000/人 CREDIT | invite.success / MANUAL_CLAIM | false | null |
| 4 | 新用户注册送4000 | NEW_USER_REGISTER | 4000 CREDIT | user.register / AUTO_GRANT | false | CLAIMED |

**状态机**（按钮文案反推）：`ELIGIBLE`（可领）→ `CLAIMED`（已领取）→ `CONFIRMED`（已到账）→ `CONSUMED`（已使用）。**已到账判定 = status ∈ {CLAIMED, CONFIRMED, CONSUMED}**。

**签到资格**：`triggerEvent=user.login`——当天客户端登录后获得领取资格（claimable=true），弹「积分福利放送」气泡，点击领取。

### 4.2 领取（claim）

```
POST /v1/ops/claim
body: {"campaignId": 1, "idempotentKey": "claim_1_<13位毫秒时间戳>", "channel": "IDE"}
→ {"code":0, "data": {"campaignId":1, "status":"CLAIMED"|"CONFIRMED"|...}}
```

`idempotentKey` 生成（webview 前端 `SnapChat-*.js` 反推）：`` `claim_${campaignId}_${Date.now()}` ``

### 4.3 确认（confirm）

```
POST /v1/ops/confirm
body: {"campaignId": 1}
→ code 0 即到账
```

### 4.4 其他相关接口

| 接口 | 说明 |
|------|------|
| GET `/v1/benefit-gateway-config` | 福利网关开关（AUc 流程） |
| GET `/v1/ops/pages/<campaignId>` | 活动详情页（webview 加载） |
| POST `/v1/ops/invite/generate` | 邀请码生成 |
| GET `sts.cn-north-4.../v5/caller-identity` | STS 身份自检（含 canonical_request 回显排障利器） |

## 五、踩坑全集（按时间线）

| # | 坑 | 症状 | 根因与解决 |
|---|-----|------|-----------|
| 1 | 带 `x-auth-token: ""` 空值头 | `APIG.0301 decrypt token fail` | APIG 见 `x-auth-token` 即走 IAM token 认证；空值解密失败。**脚本省略该头** |
| 2 | 不带 x-auth-token 后仍 401 | `verify ak sk signature fail` | 签名串与客户端不一致，见 3/4 |
| 3 | body hash 取值 | 部分形态 401 | 客户端 kernel exporter 用 `X-Sdk-Content-Sha256: UNSIGNED-PAYLOAD`（服务端跳过 body 校验）；HcClient 常规路径 GET 时 `data={}` → sha256("{}")。**脚本采用 UNSIGNED-PAYLOAD 形态** |
| 4 | **noEscape 表手抄错位**（最大坑） | 含特定字母的 path 被错误转义（如 `v→%76`、`n→%6E`），`verify ak sk signature fail`，且**错误只在含错位字母的请求上出现**，极具迷惑性 | 256 位数组手抄必错。**解法：用 rg 从 kernel exe 原样提取 `noEscape=[...]`（sanity 校验字母数字全为 1），程序化写入脚本**；成功版实现与失败版差异排查时「固定 X-Sdk-Date 双实现 diff」是最快定位法 |
| 5 | STS 凭证时效 | `decrypt token fail`（token 过期/吊销） | 凭证 2 小时有效，客户端在线时每小时续期写回。**脚本前提：CodeArts Agent 保持运行**；脚本检测 `expires_at` 过期即提示打开客户端 |
| 6 | `PROMPTCENTER.00000001 channel:参数无效` | 400（签名已通过！） | delivery 必须带 `?channel=IDE`；query 参与签名（urlEncode 后 k=v 排序拼接） |
| 7 | `TM.00001001 请求头Agent-Type为空` | 400 | 必须带 `Agent-Type: PromptCenter`（Pz 头） |
| 8 | asar 假设 | 找不到代码 | 本应用是 VSCode fork 明文部署，业务在 `extensions\vscode-codebot\out\extension.js` 与内置扩展，不在 app.asar |
| 9 | rg 二进制误判 | kernel exe 搜不到 | `-a` 强制文本模式（老坑复用） |

## 六、脚本设计（codearts_checkin.js）

```
run_codearts_checkin.cmd → codearts_checkin.js
  ├─ spawnSync python codearts_get_credentials.py   # 解密 HuaweiCloudSession（DPAPI+AES-GCM）
  ├─ 校验 expires_at（过期 → 提示打开客户端续期，退出码 1）
  ├─ GET /v1/ops/delivery?channel=IDE               # 签名（kernel 同款 + UNSIGNED-PAYLOAD）
  ├─ 判定：campaignId=1（USER_LOGIN）
  │    ├─ status ∈ {CLAIMED,CONFIRMED,CONSUMED} → 已完成，退出 0
  │    ├─ claimable=false 且 status=null → 不满足条件（如未登录触发），跳过，退出 0
  │    └─ claimable=true → 继续
  ├─ POST /v1/ops/claim {campaignId, idempotentKey:"claim_<id>_<ts>", channel:"IDE"}
  ├─ 校验 claim 响应 status ∈ 成功集合
  └─ POST /v1/ops/confirm {campaignId} → 到账，退出 0
```

- **零安装**：Node 借用 TeleAgent runtime；Python 亦借用 TeleAgent runtime（sqlite3/ctypes 标准库 + cryptography 随 `codearts_libs/`）
- 凭证只读不写回（客户端自己负责续期）
- 日志 UTF-8（cmd 入口 `chcp 65001`）
- `process.exitCode` 自然退出

## 七、验证记录（2026-10-13）

1. `GET /v5/caller-identity`（STS 自检）——服务端回显 canonical_request 逐字符比对一致（排除算法差异）
2. `GET /snap-manager/v1/privacy`（kernel 同款请求）——**200** `{"show_switch":true,"collect_data":true}`
3. `GET /v1/ops/delivery?channel=IDE` ——**200**，4 项活动
4. 今日签到状态判定——`CONFIRMED`（用户当天登录已领取 1000 CREDIT）✓
5. cmd 入口 `run_codearts_checkin.cmd` ——日志 UTF-8 正常，退出码 0 ✓
6. claim/confirm 分支——今日已领无法实测重复领取，代码路径与 webview 前端逻辑逐字对齐（idempotentKey 生成规则一致），**明日首次定时运行即真实验证**

## 八、与五平台的对比要点

| 维度 | 五平台（Trae/TeleAgent/WorkBuddy/Qoder） | CodeArts Agent |
|------|------|----------------|
| 凭证 | 单一 JWT/Bearer/自研加密 | **IAM STS 三元组**（AK+SK+SecurityToken）+ refresh_token/loginContext |
| 签名 | 无签名或简单头 | **SDK-HMAC-SHA256 全头签名**（canonical request） |
| 凭证存储 | 独立文件（storage.json/auth.v1.dat/token.json） | **VSCode SecretStorage → state.vscdb secret:// 键 → OSCrypt v10** |
| 续期 | 多为不续期/自带刷新 | 客户端认证扩展每小时 PKCE+DPoP 续期并写回 |
| 签到接口 | 固定 status/claim 或 campaigns 列表 | **ops/delivery → claim → confirm 三段式**（多了 confirm） |
| 幂等键 | 无 | `claim_<campaignId>_<ts>` |
| 时区敏感性 | Qoder 10:00 刷新 | 按天刷新（user.login 触发），凌晨即可领 |

## 九、运行前提与风险

1. **CodeArts Agent 客户端需保持运行**（凭证续期依赖其认证扩展；客户端全关时 secret 内凭证 2 小时后过期，脚本会明确报错提示）。客户端最小化即可，无需打开项目。
2. 凭证仅本机解密、仅用于本人账号签到（与五平台自动化同等边界）。
3. `codearts_libs/` 含 cryptography 运行库（~5MB），与脚本同目录。
4. 积分活动由华为云运营（当前 2026-09-08 起长期有效），campaignId/type 若变更脚本会以"未找到每日签到活动"明确提示而非误报成功。

---

*本文档基于 2026-10-13 对 CodeArts Agent 26.9.900 的逆向研究。方法论沉淀见 `Electron应用API逆向通用指南.md`，跨平台对照见 `五平台积分签到逆向研究总集.md`（已升级六平台）。*

> AI生成
