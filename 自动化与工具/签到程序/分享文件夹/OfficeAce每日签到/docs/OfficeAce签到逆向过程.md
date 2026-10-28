# OfficeAce（果办）签到逆向过程

> 独立文档：记录果办 OfficeAce 每日签到接口的逆向分析过程，可脱离原项目单独阅读。

## 一、目标

实现果办 OfficeAce（华为云出品的桌面客户端）每日签到自动化：
不操作客户端界面，通过其本地 API 完成「每日签到有礼」领取（1000 积分/天）。

## 二、关键结论

| 项 | 值 |
|---|---|
| 签到活动 | `bonus-daily-checkin-2026`「每日签到有礼」，1000 积分/天，每日北京 00:00 刷新 |
| 状态查询 | `GET <本地API>/api/subscription/current` → `bonusSkus[]` |
| 签到领取 | `POST <本地API>/api/subscription/claim-bonus`，须带 `Content-Type: application/json` + 空体 `{}` |
| 鉴权方式 | `Cookie: oc_sid=<value>`（Fastify 签名 Cookie） |
| 凭证位置 | `%USERPROFILE%\.office-claw\session.cookie` = `OC-DPAPI-1\n` + base64(**DPAPI(CurrentUser)** 加密的 JSON `{value, expires}`） |
| 本地 API | 客户端内嵌 HTTPS 服务（自签证书），监听 `127.0.0.1`，端口弹性发现（默认 3004/3002） |
| TLS 信任 | `<安装目录>\.office-claw\certs\root-ca.pem`（自签三级 CA 链），找不到时兜底跳过证书校验 |
| 已签判定 | daily 记录的 `effectiveTime`（实际领取时刻）落在今日北京 00:00 之后即已签 |
| 成功判定 | claim 返回含当日记录 = 本次入账；返回 `[]` = 当天已领（客户端整点定时器常先代领），以复查为准 |
| 关键依赖 | **客户端必须运行中**——本地服务在内存中承载云凭证（AK/SK/securityToken），做华为云 APIG 签名（V11-HMAC-SHA256）转发云端，无法离线直连 |

## 三、逆向步骤

### 1. 命名脱钩：产品名、目录名、进程名三套

搜「果办」一无所获。实际对应关系：产品名 **OfficeAce**、数据目录
**`.office-claw`**、注册表关键词 `OfficeAce`（HKCU Uninstall 命中安装目录）。
安装目录常见位置：`%USERPROFILE%\OfficeAce`、`%LOCALAPPDATA%\Programs\OfficeAce`。

### 2. 架构还原：本地 API 服务是唯一通道

客户端是 Electron 应用，启动时拉起 node 子进程跑 `packages/api/dist/cli.js`
做本地 API 服务：接收本地请求 → 用内存中的云凭证做华为云 APIG 签名 →
转发云端。**云凭证只在内存**，脚本无法离线直连，因此客户端必须运行。

### 3. 端口发现：四层弹性策略

历史上端口误判过三次（27201 = 主进程桥、8080 = 别的应用、3003 = 前端反代、
3004 = API），最终固化为四层策略，逐层探测判活：

| 优先级 | 来源 | 说明 |
|---|---|---|
| ① | `<安装目录>\.office-claw\run\windows\runtime-state.json` | 服务每次启动写入 `ApiUrl`/`ApiPort`，快准零成本 |
| ② | 安装目录 `.env` / `.inner.env` 的 `API_SERVER_PORT` | 配置文件 |
| ③ | 默认端口 3004 / 3002 | https + http 各试一次 |
| ④ | `netstat -ano` 枚举全部回环 LISTENING 端口并发探测 | 换端口/多实例的终极兜底 |

判活标准：`/api/subscription/current` 返回 200（体含 `bonusSkus` 等果办特征）
或 401/403（体含 `statusCode` / `Authentication required`），避免误判其他本地服务。
注意枚举进程/端口不能用 WMI/PowerShell 模块（冷启动 20 秒级），`netstat -ano` 毫秒级。

### 4. TLS 与鉴权

- 本地 API 是 **HTTPS 自签证书**：明文 HTTP 请求会被静默断连。Node 请求传
  `root-ca.pem` 作 `ca`；找不到 CA 文件时兜底 `rejectUnauthorized: false`（仅本机回环）。
- **证书易轮换（2026-10-28 故障案例）**：客户端 1.4.x 起每次启动重新生成证书对
  （实测磁盘 certs 全部停留在 10-13，而运行中服务 10-26 重启后下发的新证书链
  subject 同名、公钥不同），脚本拿旧 CA 验证新证书报
  `certificate signature failure`（X509_V_ERR_CERT_SIGNATURE_FAILURE），
  10-27/10-28 连续两天签到失败。修复：请求遇证书类 TLS 错误且目标为回环地址时，
  自动降级 `rejectUnauthorized: false` 重试一次（探测阶段本就走跳过校验，
  故"能发现 API 但签到失败"是此故障的典型特征）。
- 401 鉴权：要求 `oc_sid` 签名 Cookie。`session.cookie` 经 DPAPI 解密得
  `{value, expires}`，`value` 即签名后的 Cookie 值，放进 `Cookie: oc_sid=<value>` 即 200。
  会话有效期约一个月，过期需客户端重新登录。
- 415：`POST` 必须带 `Content-Type: application/json` 和空体 `{}`（Fastify 强校验）。
- 探测时**不能发空 Cookie 头**（`Cookie: undefined` 触发 `ERR_HTTP_INVALID_HEADER_VALUE`
  被 try/catch 吞掉，表现为「探测全失败」）；无会话时省略该头。

### 5. 「领取不入账」之谜：判定语义修正

最初误判「claim 返回空 = 失败」，实为三个连环误判：

1. **`currentValue` 是已消耗量**而非已领取量，拿它判「已领/可领」恒错；
2. **返回空 = 当天已领**：每天 00:00 后首次 claim 必返回完整记录并入账；
   客户端有整点自动领取定时器（00:00:0X 即代领），白天看到的空响应全是重复调用；
3. **`totalCredits` 恒定恰是成功证据**（若失败当天列表无当日记录且总额下降）。

**判定铁律**：daily 记录的 `effectiveTime` = 实际领取时刻，落在今日北京 00:00
之后即已签。修复后流程：GET 取最新 daily → eff 在今日则直接结束；否则 claim，
返回含记录 = 入账成功，返回空 = 复查 eff——「客户端已代领」也算成功，
复查仍非今日才报失败。

推论：本脚本定位是「**兜底 + 确认**」——客户端开机运行时整点定时器几乎
必然先领，任何时刻跑脚本都能正确入账/确认。

### 6. 幂等性

- 已签时脚本在查询阶段即判定退出，不发领取请求；
- 即使重复 claim，服务端同日后续调用返回空记录，无副作用；
- 「未找到每日签到活动」（活动下线/未刷新）按跳过处理，不算失败、不误报成功。

## 四、落地调用链

```
session.cookie 读 OC-DPAPI-1 块
      │  DPAPI(CurrentUser) 解密 → { value, expires } → Cookie: oc_sid=<value>
      ▼
本地 API 弹性发现（runtime 快照 → .env → 默认端口 → 回环扫描）
      │  + root-ca.pem 信任（缺失或校验失败时回环内跳过证书校验）
      ▼
GET /api/subscription/current ──► bonusSkus 中最新 daily 记录
      │  effectiveTime 在今日北京 00:00 后 → 已签结束
      ▼
随机延迟 30~300 秒（防检测，--no-delay 可跳过）
      │
      ▼
POST /api/subscription/claim-bonus（Content-Type: application/json，body {}）
      │
      ▼
2 秒后复查 subscription/current ──► 以最新 effectiveTime 确认今日入账
```

- **零依赖**：只用 Node 18+ 内置模块（`https` / `fs` / `child_process`）
- **零配置**：凭证、端口、CA、安装目录全部现场自动探测
- **无硬编码路径**：注册表 + 环境变量动态定位

## 五、故障案例速查

| 现象 | 根因 | 处置 |
|---|---|---|
| `certificate signature failure`，且日志显示"能发现 API 但状态接口调用失败" | 客户端重启后证书轮换，磁盘 root-ca.pem 落后于运行中服务实际证书 | 已内置自动降级跳过校验（仅回环），无需人工干预；重启客户端后磁盘证书追上新证书即恢复严格校验 |
| 探测全失败但客户端明明在运行 | 探测时发了空 Cookie 头（`ERR_HTTP_INVALID_HEADER_VALUE` 被吞） | 无会话时省略 Cookie 头（已修复） |
| claim 返回空 | 当天已被客户端整点定时器代领 | 复查 effectiveTime 确认，算成功 |
| 未找到每日签到活动 | 活动下线/未刷新 | 按跳过处理，不算失败 |

## 六、合规说明

本逆向仅涉及读取并解密本机自己账号的登录态，调用客户端本地 API（与客户端
自身行为一致）；云端签名由客户端本地服务完成，未触碰或绕过任何服务端校验。
仅限个人学习研究，请遵守平台条款。

> AI生成
