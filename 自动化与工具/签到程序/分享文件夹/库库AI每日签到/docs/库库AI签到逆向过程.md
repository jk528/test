# 库库AI 签到逆向过程

> 独立文档：记录库库AI（KukuAI，百度 GenFlowPro 桌面客户端）每日签到接口的逆向分析过程，
> 可脱离原项目单独阅读。

## 一、目标

实现库库AI 桌面客户端「每日签到」的自动化：不打开客户端窗口，直接调用后端活动平台 API
完成签到（10 积分/天 + 抽奖机会，连续签到有 SVIP 等里程碑奖励）。

## 二、关键结论

| 项 | 值 |
|---|---|
| 签到状态查询 | `POST https://kuku.baidu.com/act/v2/kukuai30/homepage` |
| 执行签到 | `POST https://kuku.baidu.com/act/v2/kukuai30/signin` |
| 抽奖（试验性） | `GET /act/v2/component/lottery/homeinfo`、`GET /act/v2/lottery/lotterycommit` |
| STOKEN 换取 | `POST https://passport.baidu.com/v3/login/api/auth`（bduss+ptoken → `stoken_list.genflowpro`） |
| 鉴权方式 | Cookie：`BDUSS=<bduss>; STOKEN=<stoken>; gfprotpl=genflowpro` |
| 通用 query 参数 | `app_id=123971023`、`channel=chunlei`、`clienttype=0`、`version=<客户端版本>`、`uid=<uk 可空>` |
| 活动 tid | 签到 V3.0：`291651792210`；抽奖：`531681788278`（旧版签到 `794211789557` 并存） |
| 成功判定 | 响应 `errno`（或 `code`）= 0；`errno=-6` = 登录态失效 |
| 凭证来源 | **手动提供**：客户端登录态由 native 层（bnusdk.dll）加密存储，本地无明文；改为浏览器 Cookie 取 BDUSS |

## 三、逆向步骤

### 1. 侦察：客户端形态

- 库库AI 主程序 `GenFlowPro.exe`（Electron，Vue3），安装与数据目录合一：`%APPDATA%\baidu\KukuAI\`
- 主代码包 `resources\app.asar`（约 40MB），明文可逆
- 登录态存储 `AppSettingApp.dat` 为加密二进制，由百度统一账号 native SDK（bnusdk.dll）管理，
  **全盘二进制搜索无明文 BDUSS**——这是本方案改为手动配置 Cookie 的根本原因

### 2. 代码定位：asar 里的签到模块

1. 关键词锚点：`签到` / `checkin` / `积分` → UI 模块 `SigninPromoCard`（签到奖 SVIP 文案）
2. API 路径浮现：`/act/v2/kukuai30/signin`、`/act/v2/kukuai/signinlist`、
   `/api/genflowpro/freepoint/rewardClaim` 等
3. 网关配置：`main: https://kuku.baidu.com`（与百度网盘同源体系，channel=`chunlei`）
4. 活动配置：`signin30Tid: '291651792210'`（V3.0 当前版）、`lotteryTid: '531681788278'`
5. 公共参数：`defaultParams: { app_id: 123971023 }`，由 native http 层统一附加

### 3. 鉴权还原：Cookie 三件套

客户端登录链路（还原）：

```
passport 授权页(webview) → 按 domain 提取 Cookie [BDUSS, PTOKEN, STOKEN, …]
→ POST passport.baidu.com/v3/login/api/auth（bduss+ptoken 换 stoken_list.genflowpro）
→ 取用户 uk（即 uid）→ native 层加密持久化
```

脚本直连只需在请求头携带：

```
Cookie: BDUSS=<bduss>; STOKEN=<stoken>; gfprotpl=genflowpro
```

- `BDUSS`：百度账号主凭证，全站通用，有效期通常数月到数年
- `STOKEN`：可由 bduss+ptoken 经 passport 接口自动换取（脚本已实现，缺省自动兜底）
- `gfprotpl=genflowpro`：产品标识固定值

### 4. 响应判定逻辑（从客户端还原）

```js
errno = resp.errno ?? resp.code;   // 百度 errno 风格
if (errno !== 0) throw show_msg / message;
data  = resp.data ?? resp.result;
```

签到状态字段（homepage）：

| 字段 | 含义 |
|------|------|
| `signed_today` | `true` = 今日已签（幂等拦截依据） |
| `continuous_days` | 连续签到天数 |
| `next_reward_days` / `next_reward_award` | 里程碑进度与奖励文案（SVIP 等） |
| `calendar[]` | `[{date, status}]`：0=已签、1=今日未签、2=未签、3=错过 |

### 5. 实测验证

无 Cookie 请求 `POST /act/v2/kukuai30/homepage?tid=291651792210&app_id=123971023&…`
返回 HTTP 200 `{"errno":-6,"show_msg":"账户已过期，重新登陆"}`——证明 URL/参数格式正确
（服务端正常解析并返回业务错误码），接口活性正常，唯一缺口就是 Cookie 凭证。
填入真实 BDUSS 后全链路实测通过（签到/复查/连签天数均正确）。

### 6. 凭证获取方案（为何选浏览器 Cookie）

| 方案 | 结论 |
|------|------|
| A. 浏览器取 Cookie（**采用**） | BDUSS 是百度全站通用 Cookie，浏览器登录任一百度系站点即可 F12 复制；一次配置长期使用，成本最低 |
| B. 逆向 bnusdk.dll 加密存储 | 需动态调试 native 层，成本高，且版本升级易失效 |
| C. 复用百度网盘客户端凭证 | 依赖网盘已登录同一账号，仍需逆向其账号库 |

BDUSS 敏感性等同账号密码：模板将其隔离在 `config\kuku_config.json` 并用 .gitignore 排除。

## 四、落地调用链

```
config\kuku_config.json 读 BDUSS（+ 可选 STOKEN/PTOKEN）
      │  STOKEN 缺失且有 PTOKEN → passport 接口自动换取
      ▼
POST /act/v2/kukuai30/homepage ──► signed_today? 已签则结束（幂等）
      │ 否（errno=-6 则提示凭证失效，退出码 1）
      ▼
随机延迟 30~300 秒（防检测，--no-delay 可跳过，范围可在配置里改）
      │
      ▼
POST /act/v2/kukuai30/signin ──► errno=0
      │
      ▼
再 POST homepage 复查：输出最新连签天数与里程碑进度
```

- **零依赖**：只用 Node 18+ 内置模块（`fetch` / `fs`）
- **无硬编码凭证**：全部来自配置文件/环境变量
- **零客户端依赖**：不需要安装库库AI 客户端（仅无 Node 时用客户端 EXE 兜底运行时）

## 五、合规说明

本逆向仅涉及使用自己账号的 Cookie 调用平台自身的公开活动接口，未绕过任何服务端校验。
BDUSS 等同账号密码，请妥善保管、勿外泄。仅限个人学习研究，请遵守平台条款。
