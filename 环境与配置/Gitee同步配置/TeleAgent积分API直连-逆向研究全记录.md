---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '3ae6c702-1295-497e-b01f-19b054c57a75'
  PropagateID: '3ae6c702-1295-497e-b01f-19b054c57a75'
  ReservedCode1: '38f83a13-265c-405c-9d51-3f475624ef45'
  ReservedCode2: '38f83a13-265c-405c-9d51-3f475624ef45'
---

# TeleAgent 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-09-16
> 目标：让 TeleAgent 每日积分签到脱离 UI 模拟点击，改为后台 API 直连（像 TraeWork 签到那样），无需客户端窗口运行
> 结论：**已成功**。生产脚本已部署，定时任务已切换，实测通过（退出码 0）
> 本文档记录完整的逆向思路、踩坑与解决方案，供日后出问题时排查参考

---

## 一、最终结果速览

### 当前生效配置

| 项目 | 值 |
|------|-----|
| 定时任务名 | `TeleAgent积分签到`（每天 01:00，已从 UI 版切换为 API 版） |
| 执行入口 | `桌面\定时任务脚本\run_teleagent_checkin.cmd` |
| 核心脚本 | `桌面\定时任务脚本\teleagent_checkin.js`（Node.js） |
| Node 运行时 | `%USERPROFILE%\.local\share\TeleAgent\runtimes\node\node.exe`（复用客户端自带，无需安装） |
| 日志文件 | `桌面\定时任务脚本\checkin_teleagent.log`（UTF-8 追加写入） |
| 补跑策略 | `StartWhenAvailable`（01:00 关机则开机后补跑） |
| 实测输出 | `今日已签到。本期已领 1 天，累计 100 积分，当前余额 5775.04` |

### 两版签到方案现状

| 方案 | 状态 | 说明 |
|------|------|------|
| UI 模拟点击版（claim_points.py） | 保留备用 | 依赖客户端窗口运行，技能文件仍在 skills 目录 |
| **API 直连版（teleagent_checkin.js）** | **当前生效** | 无需窗口，约 2 秒完成，仅依赖登录态未过期 |

---

## 二、逆向思路全流程

整个研究遵循「**从界面字符串 → 渲染层代码 → API 路径 → 鉴权头 → token 来源 → 解密链路**」的递进式路线，全程静态分析 + 只读验证，不抓包、不篡改。

### 第 1 步：定位文件系统布局

| 目录 | 内容 |
|------|------|
| `C:\Program Files\TeleAgent\` | 安装目录，核心是 `resources\app.asar`（470MB，Electron 打包） |
| `C:\Users\Administrator\.local\share\TeleAgent\` | 用户数据目录（登录态、Local State、设备元数据） |
| `...\TeleAgent\users\v1_public_2100056496220749824\` | 当前用户目录，`app-auth\token.json` 存加密登录态 |
| `...\TeleAgent\app-auth\device-meta.json` | 设备 ID（`deviceId: fa163e31ddf1`） |
| `...\TeleAgent\Local State` | Chromium 主密钥（`os_crypt.encrypted_key`） |
| `...\TeleAgent\current-owner.json` | 指向当前登录用户的目录名（脚本动态定位用） |

### 第 2 步：从 asar 中找接口（走了三次弯路才找对姿势）

**弯路 1**：直接对 `app.asar` 搜 `checkin/points/credits` 关键词 → ripgrep 报"binary file matches"。
**解决**：加 `-a`（`--text`）强制按文本搜索。

**弯路 2**：关键词噪声爆炸——`points` 命中 25388 处（echarts/d3 图表库污染），`checkin` 命中 902 处大多是 `checking/checkpoint`。
**解决**：**换锚点**——不搜通用词，搜 UI 独有字符串「积分福利社」「立即领取」「今日已领」，先定位功能模块，再顺藤摸瓜。

**弯路 3**：想完整解析 asar 时，PowerShell 5.1 的 `ConvertFrom-Json` 解析 8.4MB 头部直接失败（默认 2MB 上限且对大 JSON 脆弱）。
**解决**：改用客户端自带的 Node.js 写脚本解析。asar 头部结构实测为：

```
偏移 0x00: u32 = 4（外层 pickle 大小）
偏移 0x04: u32 = 头部区域总大小（如 8441292）
偏移 0x08: u32 = pickle payload 大小
偏移 0x0C: u32 = JSON 长度
偏移 0x10: JSON 头开始（文件树，含每个文件的 offset/size）
数据区起始 = 8 + 头部区域总大小
```

> 注意：网上常见的 asar 格式描述（JSON 从偏移 8 或 12 开始）与本机实测不符，以十六进制 dump 为准。

### 第 3 步：定位关键代码文件

解析 asar 得到 32312 个文件，排除 node_modules 后锁定两个 bundle：

| 文件 | 角色 |
|------|------|
| `dist/assets/index-Dol27aED.js`（3.8MB） | 渲染层 React 业务代码（**积分逻辑在这里**） |
| `dist-electron/main-runtime-*.js`（4MB） | 主进程代码（token 解密在这里） |

### 第 4 步：渲染层定位领取逻辑

搜索 `claimNow` 定位到福利社卡片组件（压缩后叫 `axe`），核心领取代码：

```js
const v = async b => {
  await On(ot.ACTIVE_CHECK_DAILY_TASK + "?type=daily_login");  // 领取
  const x = await On(ot.NEW_ACTIVE_DAYTASK);                    // 刷新状态
};
```

再搜 `ACTIVE_CHECK_DAILY_TASK` 找到 API 枚举表 `ot`：

```js
ot = {
  BASE_URL: KR() ? Hl : "",   // Hl = "https://agent.teleai.com.cn/superCowork/sapi"
  ACTIVE_USERCENTER:       `${Qt}/user/portal/companyStore/userCenter`,
  ACTIVE_DAYTASK:          `${Qt}/user/portal/companyStore/checkDayTask`,
  ACTIVE_CHECK_DAILY_TASK: `${Qt}/user/portal/companyStore/checkTask`,
  NEW_ACTIVE_DAYTASK:      `${Qt}/user/portal/companyStore/v2/checkDayTask`,
  ...
}
// Qt = KR() ? "" : "/teleagent-space"  → 桌面版 Qt 为空串，即用完整 URL
```

**关键判断**：`KR()` 检测 `window.electronAPI` 存在 → 桌面版为 true → `BASE_URL = https://agent.teleai.com.cn/superCowork/sapi`，`/teleagent-space` 前缀仅是 Web 版路径。**桌面版直接对公网域名发请求，无本地代理转发**，这意味着我们可以在任意进程里直连。

### 第 5 步：请求函数与鉴权头

追踪 `On → vM`（统一请求封装）→ `kv()`（鉴权头构造）：

```js
async function kv() {
  return {
    "X-Timestamp": String(Math.floor(Date.now()/1000)),   // 秒级时间戳
    "X-Nonce": ql(),                                       // UUID v4
    "X-App-Version": appVersion,
    "X-OS-Type": osType,
    "X-SuperAgent-Device-Id": deviceId,                    // device-meta.json 里的 deviceId
    "X-Token": token,                                      // 登录 token（关键）
    "X-Channel-Id": channelId,
    "X-Runtime-Env": runtimeEnv
  };
}
```

**重要发现**：`_De()` 函数里有签名相关逻辑，但只针对特定部署环境（`teleagent` 常量的 env 判断），**普通公网环境无需任何请求签名**——头齐全即可通过。这与 Trae 的风控（缺参报 9004、错设备 ID 报 9074）相比宽松得多。

### 第 6 步：token 从哪来（主进程侧）

渲染层 `Jt.getState().token`，初始值来自 `window.electronAPI.appAuth.getToken()` → 主进程。搜主进程 `getToken`：

```js
return n.version !== 1 || typeof n.encryptedToken != "string"
  ? "" : ro.decryptString(Buffer.from(n.encryptedToken, "base64"));
```

`ro.decryptString` 是 Electron **safeStorage** 封装。Electron safeStorage 在 Windows 上 = **Chromium OSCrypt**：

```
token.json 的 encryptedToken (base64)
  = "v10" + nonce(12字节) + ciphertext + GCM tag(16字节)
  用 AES-256-GCM 加密，密钥为 32 字节主密钥

主密钥来自: Local State → os_crypt.encrypted_key
  = "DPAPI" + (DPAPI 加密的 32 字节密钥)
  → 同一 Windows 用户下可用 DPAPI CurrentUser 范围直接解开
```

### 第 7 步：解密验证与接口实测

按上述链路解密 token（439 字符，JWT 三段式），带上鉴权头请求：

| 接口 | 方法 | 实测结果 |
|------|------|---------|
| `/user/portal/companyStore/v2/checkDayTask` | GET | 200，返回完整签到状态（是否已领/累计天数/积分） |
| `/user/portal/companyStore/checkTask?type=daily_login` | GET | 200，领取（幂等，已领时再调用不会重复发放） |
| `/user/portal/companyStore/userCenter` | GET | 200，返回积分余额、套餐、活动信息 |

验证安全性措施：
1. 先调**只读**状态接口确认鉴权可行，不碰领取
2. 调领取接口时当天已领，服务端幂等返回成功但不重复发放
3. 复查余额确认积分未异常增加（排除重复领取风险）

---

## 三、遇到的问题与解决方案汇总

| # | 问题现象 | 根因 | 解决方案 |
|---|---------|------|---------|
| 1 | rg 搜索 asar 报 "binary file matches" | asar 含大量二进制段，被自动识别为二进制 | 加 `-a` / `--text` 强制文本模式 |
| 2 | 搜 `points/checkin` 上万条无关命中 | echarts/d3 等图表库污染关键词 | 换 UI 独有中文字符串当锚点（积分福利社/立即领取） |
| 3 | PowerShell `ConvertFrom-Json` 解析 asar 头失败 | PS 5.1 对 8.4MB JSON 有大小/语法限制 | 改用 Node 脚本解析 |
| 4 | asar JSON 起始偏移反复试错（8→12→16） | 网传格式描述与本机实测不符 | 先 hexdump 前 64 字节确认 `[4,总大小,payload,JSON长度,JSON...]` 再写解析器 |
| 5 | PowerShell 正则含引号时报 ParserError | PS 转义规则与 rg 正则冲突 | 简化正则避免 `['\"\`]` 组合，或改用 Node 执行搜索 |
| 6 | 主进程搜 `welfare/companyStore` 零命中 | 积分业务在**渲染层**，主进程只管 token/系统 | 分别提取两个 bundle，渲染层搜业务、主进程搜鉴权 |
| 7 | DPAPI 直接 Unprotect token 密文失败（"数据无效"） | token 不是 DPAPI 格式，是 Chromium OSCrypt v10（AES-GCM） | 两步走：先 DPAPI 解 `Local State` 的主密钥，再用 AES-256-GCM 解 token |
| 8 | 密文头部字节 `76 31 30` 看不懂 | = ASCII "v10"，Chromium OSCrypt 版本前缀 | 识别为 v10 → nonce=后续12字节、tag=末尾16字节 |
| 9 | 改 JS 文件后 Node 报 `fs is not defined` | PowerShell 5 的 `Set-Content` 默认 ANSI(GBK) 写入，把 UTF-8 中文注释写成乱码并吞掉了换行 | 用 Write 工具（UTF-8）重写文件；**PS 改代码文件必须显式 `-Encoding UTF8`** |
| 10 | 定时任务日志中文乱码（`浠婃宸茬鍒?`） | Node 输出 UTF-8 字节，`>>` 原样写入；查看器按 GBK 解释 | 字节本身正确，**用 `Get-Content -Encoding UTF8` 读取**；记事本/VSCode 打开正常 |
| 11 | `Set-ScheduledTask` 后 `.Arguments` 显示为空 | PowerShell 对含多层引号的参数显示截断 | 用 `$t.Actions[0].Arguments` 完整输出验证 + 手动触发看结果码 |
| 12 | 担心测试时重复领积分 | 领取接口幂等性未知 | 顺序验证：只读状态接口 → 已领状态下调领取 → 复查余额无变化 |

---

## 四、生产脚本架构（teleagent_checkin.js）

```
定时任务(01:00) → run_teleagent_checkin.cmd → teleagent_checkin.js
                                                │
        ┌───────────────────────────────────────┤
        │ 1. 定位登录态                          │
        │   current-owner.json → users\<id>\app-auth\token.json
        │                                       │
        │ 2. 运行时解密（密钥不落盘）             │
        │   Local State(DPAPI解密) → 32字节主密钥
        │   → AES-256-GCM 解 encryptedToken → JWT
        │                                       │
        │ 3. 查状态 GET v2/checkDayTask          │
        │   claimed_today=true → 输出"今日已签到"并退出(0)
        │   claimed_today=false → 继续           │
        │                                       │
        │ 4. 领取 GET checkTask?type=daily_login │
        │                                       │
        │ 5. 复查状态+余额                        │
        │   confirmed → 输出结果(退出码0)         │
        │   未确认 → 输出警告(退出码1)            │
        └───────────────────────────────────────┘
```

设计要点：

1. **动态定位**：通过 `current-owner.json` 找当前用户目录，多账号/重装后不用改脚本
2. **密钥不落盘**：主密钥在内存中解密使用，不写任何临时文件（研究阶段的 masterkey.hex 已删除）
3. **三态输出**：`今日已签到` / `签到成功` / 错误信息，日志带时间戳便于追溯
4. **退出码语义**：0=正常（含已签），1=异常（解密失败/接口失败/领取未确认）
5. **依赖零安装**：Node 用客户端自带运行时，crypto/fs/os 全是内置模块

---

## 五、日常排障指南（出问题先看这里）

### 场景 1：日志报「登录态解密失败」

```
现象: 错误：登录态解密失败 - ...（可能需要重新打开客户端登录）
```

| 可能原因 | 处理 |
|---------|------|
| 登录态过期（最常见） | 打开 TeleAgent 客户端重新登录一次，token.json 会刷新 |
| Windows 用户变了 | DPAPI 密钥绑定用户账户，换用户登录系统后需重新登录客户端 |
| Local State 被清理 | 客户端重建后首次启动会重新生成，重新登录即可 |
| token.json 格式变化（客户端大版本升级） | 按「六、重新逆向」章节检查 |

### 场景 2：日志报「登录态已过期」

```
现象: 错误：登录态已过期，请打开 TeleAgent 客户端重新登录
```

token 能解密但服务端拒绝（401）。处理：打开客户端重新登录。

### 场景 3：客户端升级后签到失败

客户端改版可能变更：接口路径、鉴权头、加密格式。排查顺序：

```powershell
# 1. 先跑一次看具体报错
& "$env:USERPROFILE\.local\share\TeleAgent\runtimes\node\node.exe" "C:\Users\Administrator\Desktop\定时任务脚本\teleagent_checkin.js"

# 2. 若怀疑接口变了，从新 asar 里重新找接口（见第六节）
```

### 场景 4：日志中文乱码

不是 bug。日志字节是 UTF-8，PowerShell 5 的 `Get-Content` 默认按 GBK 读。正确读取：

```powershell
Get-Content "C:\Users\Administrator\Desktop\定时任务脚本\checkin_teleagent.log" -Tail 20 -Encoding UTF8
```

记事本 / VSCode 打开显示正常。

### 场景 5：任务到点没执行

```powershell
# 查任务状态
Get-ScheduledTask -TaskName "TeleAgent积分签到" | Select TaskName, State
Get-ScheduledTaskInfo -TaskName "TeleAgent积分签到" | Select LastRunTime, LastTaskResult, NextRunTime

# 手动触发
Start-ScheduledTask -TaskName "TeleAgent积分签到"

# 确认任务文件落盘（沙箱环境注册可能假成功）
Test-Path "C:\Windows\System32\Tasks\TeleAgent积分签到"   # 必须为 True
```

`LastTaskResult` 含义：0=成功，1=脚本内错误（看日志），267011=任务从未运行过。

### 场景 6：想临时切回 UI 模拟点击版

```powershell
$py = "C:\Users\Administrator\.local\share\TeleAgent\runtimes\python\python.exe"
$skill = "C:\Users\Administrator\.config\TeleAgent\users\v1_public_2100056496220749824\skills\teleagent-points-claimer\scripts\claim_points.py"
$out = "C:\Users\Administrator\Desktop\定时任务脚本\.temp\teleagent-points"
$arg = "/s /c `"`"$py`" `"$skill`" --output-dir `"$out`" >> `"$out\claim.log`" 2>&1`""
Set-ScheduledTask -TaskName "TeleAgent积分签到" -Action (New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arg)
```

UI 版要求客户端窗口运行且未最小化。

---

## 六、重新逆向速查（客户端改版时用）

1. **解 asar**：Node 脚本读头部（偏移 16 起 JSON，数据区 = 8+头部总大小），文件清单见 `dist/assets/index-*.js`（渲染层业务）与 `dist-electron/main-runtime-*.js`（主进程）
2. **找接口**：在渲染层 bundle 搜 UI 字符串（如 `积分福利社`、`claimNow`）→ 定位组件 → 找 `ot.ACTIVE_*` 枚举
3. **找鉴权**：搜 `X-Token` → `kv()` 函数 → 鉴权头清单
4. **找加密**：主进程搜 `encryptedToken` / `decryptString` → safeStorage → Windows 上即 DPAPI+OSCrypt
5. **验证**：先调只读接口（v2/checkDayTask），确认 200 再动领取
6. 搜索命令模板（注意 `-a` 强制文本）：

```powershell
$rg = "C:\Program Files\TeleAgent\resources\ripgrep\win32-x64\rg.exe"
& $rg -a -o -N "积分福利社.{0,200}" "C:\Program Files\TeleAgent\resources\app.asar" | Select-Object -First 5
```

> 自带 ripgrep 有 win32-x64 与 win32-arm64 两版，x64 机器用 `win32-x64`。

---

## 七、附录

### A. 关键文件路径速查

| 文件 | 路径 |
|------|------|
| API 签到脚本 | `C:\Users\Administrator\Desktop\定时任务脚本\teleagent_checkin.js` |
| 签到入口 | `C:\Users\Administrator\Desktop\定时任务脚本\run_teleagent_checkin.cmd` |
| 签到日志 | `C:\Users\Administrator\Desktop\定时任务脚本\checkin_teleagent.log` |
| 登录态 | `%USERPROFILE%\.local\share\TeleAgent\users\v1_public_2100056496220749824\app-auth\token.json` |
| 加密主密钥 | `%USERPROFILE%\.local\share\TeleAgent\Local State`（os_crypt.encrypted_key） |
| 设备 ID | `%USERPROFILE%\.local\share\TeleAgent\app-auth\device-meta.json` |
| 客户端代码包 | `C:\Program Files\TeleAgent\resources\app.asar` |

### B. 接口清单

网关：`https://agent.teleai.com.cn/superCowork/sapi`

| 用途 | 方法 + 路径 | 备注 |
|------|------------|------|
| 签到状态 | GET `/user/portal/companyStore/v2/checkDayTask` | 返回 daily_task.claimed_today / total_claim_days / total_claimed_points |
| 领取积分 | GET `/user/portal/companyStore/checkTask?type=daily_login` | 幂等；每日 100 积分 |
| 积分余额 | GET `/user/portal/companyStore/userCenter` | 返回 current_points_balance、套餐、活动 |

必需请求头：`X-Token`（解密后的 JWT）、`X-Timestamp`（秒级时间戳）、`X-Nonce`（UUID）、`X-SuperAgent-Device-Id`（device-meta.json 的 deviceId）、`X-OS-Type: Windows`。`X-App-Version` 填客户端版本号（当前 2.5.2，缺失也能过）。

### C. 签到状态响应字段对照

```json
{
  "code": 200,
  "data": {
    "brand_title": "积分福利社",
    "daily_task": {
      "daily_claimable_points": 100,      // 每日可领
      "total_claim_days": 1,              // 本期已领天数
      "total_claimed_points": 100,        // 累计积分
      "claimed_today": true,              // 今日是否已领
      "button_text": "今日已领"
    }
  }
}
```

### D. 与 TraeWork 签到方案对照

| 维度 | TraeWork | TeleAgent（本次） |
|------|----------|------------------|
| token 加密 | AES-128-CBC + SHA-512 派生 + 内置常量表（逆向混淆） | Chromium OSCrypt v10（DPAPI 主密钥 + AES-256-GCM） |
| 解密依赖 | 纯 JS 可解 | 需 DPAPI（同 Windows 用户） |
| 风控参数 | req_source=2 + 数字设备ID，缺参 9004/风控 9074 | 头齐全即过，暂无签名 |
| 领取方法 | POST claim | GET checkTask?type=daily_login |
| 验证方式 | code===0 + 刷新状态 | 按钮状态 + 余额复查 |

### E. 定时任务管理命令

```powershell
Get-ScheduledTask -TaskName "TeleAgent积分签到"                    # 查状态
Get-ScheduledTaskInfo -TaskName "TeleAgent积分签到"                # 查运行记录
Start-ScheduledTask -TaskName "TeleAgent积分签到"                  # 手动触发
Disable-ScheduledTask -TaskName "TeleAgent积分签到"                # 停用
Unregister-ScheduledTask -TaskName "TeleAgent积分签到" -Confirm:$false  # 删除
```


> AI生成