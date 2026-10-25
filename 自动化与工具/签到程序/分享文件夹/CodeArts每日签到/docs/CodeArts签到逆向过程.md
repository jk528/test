# CodeArts 签到逆向过程

> 独立文档：记录 CodeArts Agent 每日签到接口的逆向分析过程，可脱离原项目单独阅读。

## 一、目标

实现华为云 CodeArts Agent（码道，AI 编码智能体 IDE，VSCode fork）的
「积分福利」每日签到自动化：不操作客户端界面，直接调用后端 API 完成签到。
签到形态为**福利活动制**（ops/campaign）：先拉活动列表再领取，每日签到领 1000 CREDIT。

## 二、关键结论

| 项 | 值 |
|---|---|
| 活动列表 | `GET https://snap-access.cn-north-4.myhuaweicloud.com/v1/ops/delivery?channel=IDE` |
| 签到领取 | `POST /v1/ops/claim`，body `{"campaignId":1,"idempotentKey":"claim_1_<毫秒时间戳>","channel":"IDE"}` |
| 确认到账 | `POST /v1/ops/confirm`，body `{"campaignId":1}` |
| 鉴权方式 | **华为云 IAM STS 临时凭证（AK/SK/SecurityToken）+ SDK-HMAC-SHA256 全头签名** |
| 必需业务头 | `Agent-Type: PromptCenter`、`X-Language: zh-cn`、`X-Security-Token`、`X-Sdk-Content-Sha256: UNSIGNED-PAYLOAD`、`x-snap-traceid: <uuid>` |
| 凭证位置 | `%APPDATA%\codearts-agent\User\globalStorage\state.vscdb`（SQLite），<br>键 `secret://{"extensionId":"huaweicloud.authentication","key":"HuaweiCloudSession"}`（**加密存储**） |
| 主密钥 | `%APPDATA%\codearts-agent\Local State` 的 `os_crypt.encrypted_key`（去 `DPAPI` 前缀后 DPAPI Unprotect 得 32B AES 密钥） |
| 成功判定 | delivery 中每日活动 status ∈ {CLAIMED, CONFIRMED, CONSUMED}；claim 返回 `code:0` 后必须再 confirm |
| 每日活动 | `campaignId=1`，type=`USER_LOGIN`（当天登录触发领取资格），`benefitAmount=1000 CREDIT` |

## 三、逆向步骤

### 1. 接口定位：福利活动三段式

客户端是 VSCode fork，代码明文部署（`resources\app\`，无 asar）。
在 `extensions\vscode-codebot\out\extension.js` 中搜 `checkin`/`welfare` 命中：

- `welfareDeliveryUrl = <policyCenterDomain>/v1/ops/delivery`
- `welfareClaimUrl = .../v1/ops/claim`、`welfareConfirmUrl = .../v1/ops/confirm`
- 国内版 `policyCenterDomain = https://snap-access.cn-north-4.myhuaweicloud.com`

签到是「delivery 拉活动 → claim 领取 → confirm 确认」三段式，
比一般平台的 status/claim 两段式多了 confirm 落账环节。

### 2. 凭证存储：VSCode SecretStorage + Chromium OSCrypt

登录由内置扩展 `huaweicloud.authentication` 负责（IAM OAuth2 + PKCE + DPoP），
拿到 STS 临时凭证后经 VSCode SecretStorage 共享，落盘为：

```
state.vscdb (SQLite ItemTable)
  key   = secret://{"extensionId":"huaweicloud.authentication","key":"HuaweiCloudSession"}
  value = {"type":"Buffer","data":[...]}   ← v10 信封密文
```

密文结构 `v10`(3B) + nonce(12B) + ciphertext + tag(16B)，AES-256-GCM；
主密钥在 `Local State` 的 `os_crypt.encrypted_key`，DPAPI(CurrentUser) 解密。
**全部解密材料都在本机，无需联网、无需用户密码。**

解密后明文 JSON 含：

```json
{
  "account": {"id": "...", "label": "..."},
  "accessKey": "HST...",          // STS 临时 AK（2 小时有效）
  "secretKey": "...",             // 配套 SK
  "securitytoken": "...",         // STS token
  "expires_at": "...",            // 过期时刻
  "refresh_token": "eyJ..."       // 客户端认证扩展每小时续期并写回
}
```

读取 SQLite 用 Node 内置 `node:sqlite`（需 22.13+，readOnly 打开），零 npm 依赖。

### 3. 请求签名：SDK-HMAC-SHA256（AWS v4 风格）

签名算法从客户端 kernel（`otlp-aksk-exporter`，pkg 打包的 Node）原样提取，
与华为云 SDK 一致：

```
CanonicalRequest =
  HTTPMethod \n
  CanonicalURI \n          # path 按 / 分段 urlEncode 后 join，末尾补 /
  CanonicalQueryString \n  # key,value 各自 urlEncode 后 k=v 排序拼接
  CanonicalHeaders \n      # 全部请求头小写排序，k:value\n
  SignedHeaders \n         # 小写头名分号连接
  HexEncode(SHA256(body))  # 有 X-Sdk-Content-Sha256 头则直接用其值

StringToSign = "SDK-HMAC-SHA256" \n <X-Sdk-Date> \n HexEncode(SHA256(CanonicalRequest))
Signature    = HexEncode(HMAC-SHA256(StringToSign, SK))
Authorization: SDK-HMAC-SHA256 Access=<AK>, SignedHeaders=..., Signature=...
```

客户端 kernel exporter 形态声明 `X-Sdk-Content-Sha256: UNSIGNED-PAYLOAD`
（body 不参与校验），脚本采用同一形态。

### 4. 踩坑实录（实测症状 → 根因）

| 坑 | 症状 | 根因与解决 |
|---|---|---|
| 带 `x-auth-token: ""` 空头 | `APIG.0301 decrypt token fail` | APIG 见到该头即走 IAM token 认证路径；**脚本直接省略** |
| urlEncode 不转义表错位 | 含特定字母的 path 被错误转义，`verify ak sk signature fail`，且错误只在含错位字母的请求上出现 | 256 位 noEscape 表必须与 kernel 逐位一致（`! ' ( ) * - . _ ~` 及字母数字不转义）；手抄必错，应从 kernel exe 原样提取 |
| delivery 缺 `?channel=IDE` | 400 `channel:参数无效`（签名已通过） | query 参与签名（urlEncode 后 k=v 排序拼接） |
| 缺 `Agent-Type` 头 | 400 `请求头Agent-Type为空` | 必须带 `Agent-Type: PromptCenter` |
| STS 凭证时效 | `decrypt token fail` | 凭证 2 小时有效，客户端在线时每小时续期写回；脚本检测 `expires_at` 过期即提示打开客户端 |

### 5. 状态机与幂等

活动状态机：`ELIGIBLE`（可领）→ `CLAIMED`（已领）→ `CONFIRMED`（已到账）→ `CONSUMED`（已使用）。

- status ∈ {CLAIMED, CONFIRMED, CONSUMED} → 今日已完成，直接跳过；
- `CLAIMED` 是「已领但 confirm 中断」的中间态，脚本会**补一次 confirm** 使积分落账；
- `claimable=false` 且未完成 → 当天登录资格未触发，跳过不算失败；
- claim 请求带幂等键 `claim_<campaignId>_<毫秒时间戳>`（与 webview 前端生成规则一致）。

因此定时任务重复触发、手动补跑都安全。

### 6. 凭证保活

STS 凭证 2 小时有效，客户端认证扩展每小时自动续期并写回本地存储。
**脚本前提：CodeArts Agent 客户端保持运行**（最小化即可，无需打开项目）。
凭证过期表现：脚本明确提示「凭证已过期且客户端未在线续期」，
打开客户端续期后重试即可，无需修改任何配置。

## 四、落地调用链

```
state.vscdb 读 secret:// HuaweiCloudSession 加密块
      │  Local State 取主密钥（DPAPI）→ AES-256-GCM 解密 → STS 凭证
      ▼
校验 expires_at（过期则提示打开客户端续期）
      │
      ▼
GET /v1/ops/delivery?channel=IDE（SDK-HMAC-SHA256 签名）
      │
      ▼
定位每日签到（campaignId=1 / type=USER_LOGIN）
      │  status ∈ {CLAIMED,CONFIRMED,CONSUMED} → 已签结束（CLAIMED 补 confirm）
      │  claimable=false → 跳过
      ▼
随机延迟 30~300 秒（防检测，--no-delay 可跳过）
      │
      ▼
POST /v1/ops/claim（带幂等键）→ status ∈ 成功集合
      │
      ▼
POST /v1/ops/confirm → 积分到账
```

- **零依赖**：只用 Node 内置模块（`https` / `crypto` / `node:sqlite` / `child_process`）
- **零配置**：凭证路径、密钥、签名材料全部现场自动探测/推导
- **无硬编码凭证**：无任何账号信息写入脚本

## 五、合规说明

本逆向仅涉及读取并解密本机自己账号的登录态，调用平台自身的公开接口；
未绕过任何服务端校验（签名照实计算、凭证照实使用）。仅限个人学习研究，
请遵守平台条款。
