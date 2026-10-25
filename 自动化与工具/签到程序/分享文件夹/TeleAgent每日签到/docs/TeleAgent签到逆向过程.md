# TeleAgent 签到逆向过程

> 独立文档：记录 TeleAgent 每日签到接口的逆向分析过程，可脱离原项目单独阅读。

## 一、目标

实现 TeleAgent（中电信人工智能 AI 助手）每日签到的自动化：
不打开客户端窗口，直接调用后端 API 完成签到。

## 二、关键结论

| 项 | 值 |
|---|---|
| 状态查询 | `GET https://agent.teleai.com.cn/superCowork/sapi/user/portal/companyStore/v2/checkDayTask` |
| 签到领取 | `GET https://agent.teleai.com.cn/superCowork/sapi/user/portal/companyStore/checkTask?type=daily_login` |
| 积分余额 | `GET https://agent.teleai.com.cn/superCowork/sapi/user/portal/companyStore/userCenter` |
| 鉴权方式 | 请求头 `X-Token: <JWT>` |
| 必需请求头 | `X-Timestamp`、`X-Nonce`、`X-App-Version`、`X-OS-Type`、`X-SuperAgent-Device-Id`、`X-Token`（`X-Channel-Id`/`X-Runtime-Env` 留空） |
| 凭证位置 | `%USERPROFILE%\.local\share\TeleAgent\users\<ownerDir>\app-auth\token.json`<br>的 `encryptedToken` 字段（**加密存储**；`<ownerDir>` 由同目录<br>`current-owner.json` 的 `ownerDir` 字段指向） |
| 设备 ID | `%USERPROFILE%\.local\share\TeleAgent\app-auth\device-meta.json` 的 `deviceId` |
| 加密主密钥 | `%USERPROFILE%\.local\share\TeleAgent\Local State` 的<br>`os_crypt.encrypted_key`（DPAPI 加密，绑定当前 Windows 用户） |
| 成功判定 | 状态接口返回 `daily_task.claimed_today: true`；领取接口幂等 |
| 签名/加密 | 请求本身**无签名**（公网环境）；难点全在本地凭证的加密存储 |

## 三、逆向步骤

### 1. 客户端形态与文件布局

TeleAgent 是 Electron 应用，业务代码打包在 `resources\app.asar` 中。
用户数据（登录态、密钥、设备信息）在 `%USERPROFILE%\.local\share\TeleAgent\` 下。
桌面版直接对公网域名 `agent.teleai.com.cn` 发请求，无本地代理转发，
因此可在任意进程中直连 API。

### 2. 接口定位：从 UI 字符串顺藤摸瓜

asar 是半二进制打包格式，直接搜 `checkin/points` 会被图表库等噪声淹没
（`points` 命中上万处）。有效姿势：搜 UI 独有中文字符串
「积分福利社」「立即领取」先定位渲染层功能组件，再从组件代码追到 API 枚举表：

```
/user/portal/companyStore/v2/checkDayTask        签到状态
/user/portal/companyStore/checkTask?type=daily_login   领取
/user/portal/companyStore/userCenter             积分余额
```

> 提示：搜 asar 需给 ripgrep 加 `-a` 强制文本模式，否则报 "binary file matches"。

### 3. 鉴权头：头齐全即过，无请求签名

逆向统一请求封装得到鉴权头构造（时间戳为秒级、Nonce 为 UUID v4）：

```
X-Timestamp / X-Nonce / X-App-Version / X-OS-Type: Windows
X-SuperAgent-Device-Id: <device-meta.json 的 deviceId>
X-Token: <登录 token>
```

代码里存在签名相关逻辑，但只针对特定部署环境；普通公网环境
**无需任何请求签名**，头齐全即可通过。

### 4. token 解密：Chromium OSCrypt v10（DPAPI + AES-256-GCM 两步）

主进程侧 `getToken` 调 Electron **safeStorage** 解密，而 safeStorage 在
Windows 上即 Chromium OSCrypt：

```
token.json 的 encryptedToken (base64)
  = "v10" + nonce(12B) + ciphertext + GCM tag(16B)
  算法 AES-256-GCM，密钥为 32B 主密钥

主密钥来自 Local State → os_crypt.encrypted_key
  = "DPAPI" + (DPAPI 加密的 32B 密钥)
  → 同一 Windows 用户下 DPAPI CurrentUser 范围直接解开
```

踩坑：直接对 token 密文做 DPAPI Unprotect 会报「数据无效」——token 不是
DPAPI 格式。必须两步走：先 DPAPI 解 `Local State` 的主密钥，再用
AES-256-GCM 解 token。解密得到 JWT（三段式），全程只在内存中完成，不落盘。

### 5. 幂等性确认

领取接口幂等：已领取时重复调用返回成功但不重复发放（实测余额无变化）。
脚本仍先查状态、`claimed_today=true` 直接跳过，定时任务重复触发安全。

### 6. 凭证保活

token 过期后状态接口返回 401。处理方式：**打开 TeleAgent 客户端重新登录**，
`token.json` 即被刷新，脚本下次运行自动读取新值，无需修改任何配置。
注意 DPAPI 密钥绑定 Windows 用户：换系统用户登录后需在客户端重新登录一次。

## 四、落地调用链

```
current-owner.json 定位当前用户目录 → users\<ownerDir>\app-auth\token.json
      │
      ▼
Local State 的 os_crypt.encrypted_key → DPAPI(CurrentUser) 解出 32B 主密钥
      │  AES-256-GCM("v10" 信封) 解密 encryptedToken → JWT
      ▼
拼请求头（X-Token + 时间戳/Nonce + 设备 ID + 版本号）
      │
      ▼
GET v2/checkDayTask ──► claimed_today? 已签则结束
      │ 否
      ▼
随机延迟 30~300 秒（防检测，--no-delay 可跳过）
      │
      ▼
GET checkTask?type=daily_login（领取）
      │
      ▼
复查 v2/checkDayTask + userCenter（确认已领、输出余额）
```

- **零依赖**：只用 Node 18+ 内置模块（`fetch` / `crypto` / `fs`），
  DPAPI 通过一次性 PowerShell 命令完成，无 npm 包
- **零配置**：凭证、设备 ID、版本号全部现场自动探测
- **无硬编码路径**：数据目录由 `%USERPROFILE%` 动态定位，版本号经注册表
  InstallLocation 探测；`current-owner.json` 动态指向当前用户，多账号/重装自适应
- **无 Node 也能跑**：TeleAgent 客户端自带 Node 运行时
  （`%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe`），
  入口脚本会优先复用；再不行用客户端 EXE 以 `ELECTRON_RUN_AS_NODE=1` 兜底

## 五、合规说明

本逆向仅涉及读取并解密本机自己账号的登录态，调用平台自身的公开接口；
未绕过任何服务端校验（设备指纹等照实提供）。仅限个人学习研究，
请遵守平台条款。
