# 库库AI（KukuAI）签到逆向记录

> 逆向日期：2026-10-25（周日）
> 产品：库库AI 桌面客户端（百度 GenFlowPro 1.6.28.0，Electron 架构）
> 状态：**协议层逆向完成**（接口/参数/鉴权/判定全部还原并实测）；凭证层待接入（BDUSS 由 native 加密存储，见 §八）
> 关联：本文档为第八个平台逆向记录，摘要已并入《签到逆向研究总集.md》

---

## 一、背景与结论

用户提出逆向"酷酷客户端"（实为**库库AI**，快捷方式名"库库AI"，主程序 `GenFlowPro.exe`）的签到逻辑。结论：

- **签到体系**：走百度活动平台 `/act/v2/kukuai30/`（当前 V3.0 版，旧版 `/act/v2/kukuai/` 并存），每日签到得 10 积分 + 抽奖机会，连续签到有里程碑奖励（SVIP 等）
- **鉴权**：百度账号 Cookie（`BDUSS` + `STOKEN` + `gfprotpl=genflowpro`），由客户端 native 层（bnusdk.dll）自动附加
- **网关**：`https://kuku.baidu.com`（与百度网盘同源体系，channel=`chunlei`）
- **积分体系**：文/api/genflowpro/freepoint/*文（homenew/rewardClaim/taskComplete/inviteCode/inviteBind）
- **实测**：无 Cookie 请求状态接口返回 文errno:-6 账户已过期文，接口连通、参数格式正确，仅缺凭证

---

## 二、侦察层：目录定位

| 目标 | 位置 | 说明 |
|------|------|------|
| 快捷方式 | 桌面/开始菜单 文库库AI.lnk文 | → 文%APPDATA%\baidu\KukuAI\GenFlowPro.exe文 |
| 安装+数据目录 | 文%APPDATA%\baidu\KukuAI\文 | Electron userData 与安装目录合一（少见形态） |
| 主代码包 | 文KukuAI\resources\app.asar文（40MB） | Vue3 + Electron，明文可逆 |
| 沙箱引擎数据 | 文%APPDATA%\baidu\GenFlowPro\文 | node-v22 沙箱、埋点 SQLite、加密日志 MXLog |
| 用户数据 | 文KukuAI\users\<md5hash>\文 | transmission.db / upload.db / PersonalSetting.xml（加密） |
| 登录态存储 | 文KukuAI\AppSettingApp.dat文（1.4KB） | Base64 加密二进制，native 层管理，**无明文 BDUSS** |
| native SDK | `bnusdk.dll` / `minosagent.dll` / `genflowengine.dll` | 百度统一账号 SDK，管理 Cookie 与加密存储 |
| 本地端口 | GenFlowPro 监听 `127.0.0.1:19475` | native http 通道，非公开 API，asar 内无定义 |
| 日志 | 文GenFlowPro\AppData\MXLog_*文 | 百度自研编码格式，不可直接阅读 |

> 排障提示：注册表搜"酷酷"无结果，产品名是"**库库**AI"（KukuAI），进程名 `GenFlowPro`。

---

## 三、代码定位（asar 逆向路径）

1. 关键词锚点：文签到文(21)/`checkin`(46)/文积分文(106) → UI 模块 `SigninPromoCard`
2. 奖励文案：文checkInReward: "Check-in Rewards"文、文checkInRewardValue: "Get SVIP"文（签到奖 SVIP）
3. API 路径浮现：`/act/v2/kukuai/signinlist`、`/act/v2/kukuai30/signin`、`/api/genflowpro/freepoint/rewardClaim`
4. 网关配置（`_y` 常量）：`main: https://kuku.baidu.com`（另有 pcsData/analytics/officeEditor 等）
5. 活动配置（`yy` 常量）：文signin30Tid: '291651792210'文（V3.0 签到）、文signinTid: '794211789557'文（旧版）、文lotteryTid: '531681788278'文
6. 公共参数：文defaultParams: {app_id: 123971023}文、文channel: "chunlei"文、文clienttype: <Windows>文、`version`

---

## 四、接口清单

### 4.1 签到活动（V3.0 当前版）

网关：`https://kuku.baidu.com`

| 用途 | 方法+路径 | 关键参数 |
|------|-----------|----------|
| 签到状态（日历/连签） | POST `/act/v2/kukuai30/homepage` | `uid` 文<uk>文、`tid=291651792210`、`app_id=123971023` |
| 执行签到 | POST `/act/v2/kukuai30/signin` | 同上 |
| 旧版签到列表 | POST `/act/v2/kukuai/signinlist` | `tid=794211789557` |

通用 query 参数：`app_id=123971023`、`channel=chunlei`、`clienttype=0`（或设备类型）、`version=1.6.28`

### 4.2 积分体系（freepoint）

| 用途 | 方法+路径 |
|------|-----------|
| 积分主页（活动/任务列表） | GET `/api/genflowpro/freepoint/homenew` |
| 领取奖励 | POST `/api/genflowpro/freepoint/rewardClaim` |
| 任务完成上报 | POST `/api/genflowpro/freepoint/taskComplete` |
| 邀请码生成/绑定 | POST `/api/genflowpro/freepoint/inviteCode` / `inviteBind` |

（另有活动任务：`/api/genflowpro/activity/taskcomplete`、`/api/taskscore/tasklist`）

### 4.3 STOKEN 换取（passport）

| 用途 | 方法+路径 | 请求体 |
|------|-----------|--------|
| bduss+ptoken 换 STOKEN | POST `https://passport.baidu.com/v3/login/api/auth` | 文bduss=<bduss>&ptoken=<ptoken>文（form-urlencoded） |

响应取 `stoken_list.genflowpro` 即 STOKEN；`errno=0` 成功。

---

## 五、鉴权与凭证层

### 5.1 Cookie 形态（脚本直连需自行携带）

文文文text
Cookie: BDUSS=<bduss>; STOKEN=<stoken>; gfprotpl=genflowpro
文文文

- `BDUSS`：百度账号主凭证（有效期通常数年）
- `STOKEN`：经 §4.3 接口换取（`stoken_list.genflowpro`）
- `gfprotpl=genflowpro`：产品标识固定值
- 客户端内由 native（bnusdk.dll）自动附加；脚本直连需手动携带

### 5.2 客户端登录链路（还原）

文文文
passport 授权页(webview) → 从 cookie 按 domain 精确度提取
  [BDUSS, BDUSS_BFESS, PTOKEN, PTOKEN_BFESS, PASS_STOKEN, STOKEN]
→ POST passport.baidu.com/v3/login/api/auth (bduss+ptoken) 换 stoken
→ fetchUserReport 取用户 uk(即 uid)/uinfo(signKey)
→ nativeBridge.setLoginState({sign_key, bduss, stoken, pass_stoken, uk, cookies})
→ native 层加密持久化（AppSettingApp.dat / bnusdk 存储）
文文文

### 5.3 凭证存储现状

- `AppSettingApp.dat`、`PersonalSetting.xml` 均为加密密文（无明文 BDUSS）
- 本地所有文件二进制搜索 BDUSS/STOKEN 明文无命中（仅 DLL/asar 内代码字符串）
- **结论：凭证在 native 加密层，明文提取需继续逆向 bnusdk.dll（成本高，见 §八方案）**

---

## 六、响应判定逻辑（从签到模块还原）

### 6.1 通用响应解析（G 函数）

文文文js
data = resp.data;                      // axios 层
errno = data.errno ?? data.code;       // 百度 errno 风格
if (errno !== 0) throw show_msg/message;
result = data.data ?? data.result;
文文文

### 6.2 签到状态字段（ue 函数）

| 字段 | 含义 |
|------|------|
| `signed_today` | `true`=今日已签（state→`signed`） |
| `continuous_days` | 连续签到天数 |
| `next_reward_days` / `next_reward_award` | 里程碑奖励进度与文案（SVIP 等） |
| `countdown` | 活动倒计时（>0 入口可用） |
| 文calendar[]文 | 文[{date:"2026-10-25", status:n}]文 |

日历 status：文0文=已签、文1文=今日未签（可签）、文2文=未签、文3文=错过；每日奖励 `signPoint`（默认 10 积分，服务端配置 `kukuSignConf` 可改）+ `lotteryChances`（1 次抽奖机会）

### 6.3 签到交互流程（ge 函数）

文文文
未登录(guest) → 弹登录 → 登录后刷新状态
今日未签(unsigned) → POST signin → 成功后刷新 homepage
今日已签(signed) → 提示已签
homepage 请求失败 → 隐藏签到入口
文文文

---

## 七、实测验证（2026-10-25）

| 步骤 | 请求 | 结果 |
|------|------|------|
| 1. V3.0 状态接口 | 文POST https://kuku.baidu.com/act/v2/kukuai30/homepage?tid=291651792210&app_id=123971023&uid=&channel=chunlei&clienttype=0&version=1.6.28文 | HTTP 200 文{"errno":-6,"show_msg":"账户已过期，重新登陆","server_time":1792878670}文 |
| 2. 旧版签到列表 | 文POST https://kuku.baidu.com/act/v2/kukuai/signinlist?tid=794211789557&app_id=123971023&channel=chunlei&clienttype=0文 | HTTP 200 文{"errno":-6,...}文 |

> 判定：URL/参数格式正确（服务端正常解析并返回业务错误码），`errno=-6` = 未登录，与"仅缺 Cookie 凭证"的预期完全一致；接口活性正常。

---

## 八、落地方案与待办（凭证获取）

脚本直连签到的最后一块拼图是拿到 `BDUSS`（再换 STOKEN）。三个方案按成本排序：

| 方案 | 做法 | 成本/风险 |
|------|------|-----------|
| A. 手动提供 Cookie（推荐起步） | 用户从客户端流量抓包（Fiddler 等）取一次 BDUSS/STOKEN，配置到脚本；BDUSS 有效期数年 | 低；一次性操作 |
| B. 逆向 bnusdk 存储加密 | 逆向 `bnusdk.dll`/`AppSettingApp.dat` 的加解密，自动读 native 凭证 | 高；需动态调试 |
| C. 百度网盘凭证复用 | 逆向百度网盘客户端账号库（同源 SDK），提取 BDUSS 后经 §4.3 换 genflowpro STOKEN | 中；依赖网盘已登录同一账号 |

> 注意：本机浏览器（Edge）Cookies 无百度登录态，浏览器提取方案不可行。

**集成建议**：凭证就绪后按 `checkin_all.js` 平台模块模式新增 `checkinKuku()`（POST homepage 判 `signed_today` → 未签则 POST signin → 校验 errno=0 → 输出连签天数/奖励文案），错误码处理：`-6` 登录态失效（提示重新抓取 Cookie）。

---

## 九、文件清单

| 文件 | 说明 |
|------|------|
| `checkin_all.js` | 待新增 `checkinKuku()`（凭证就绪后集成） |
| 文文档/签到逆向研究总集.md文 | 摘要与接口清单已并入（2.8 节） |
| **本文件** | 库库AI 签到完整逆向过程 |

> AI生成
