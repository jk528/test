---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '05a17dca-52cf-4cca-b8fa-84c0922ba80f'
  PropagateID: '05a17dca-52cf-4cca-b8fa-84c0922ba80f'
  ReservedCode1: '4353d5dd-c968-49db-b6f5-57df6d6b5b5d'
  ReservedCode2: '4353d5dd-c968-49db-b6f5-57df6d6b5b5d'
---

# Electron 应用 API 逆向通用指南

> 沉淀日期：2026-09-20（基于 TraeWork / Trae CN / TeleAgent / WorkBuddy / Qoder 五个平台的实战逆向经验）
> 目标读者：需要把某个 Electron 桌面客户端的自动化操作（签到、领积分、任务领取等）改造为**后台 API 直连**的自己
> 核心主张：不抓包、不模拟点击、不篡改客户端；全程**静态分析 + 只读验证 + 本机凭证复用**
> 配套文档：各平台独立研究全记录 + `五平台积分签到逆向研究总集.md`

---

## 一、总体思路

API 直连的本质：**用客户端自己的登录态 + 客户端自己的请求逻辑，在客户端进程外复现一次合法请求**。

```
┌─ 侦察层 ──────────────────────────────┐
│ 安装目录 / 数据目录 / 运行日志          │
└──────────┬───────────────────────────┘
           ↓
┌─ 代码层 ──────────────────────────────┐
│ asar 解包（或明文 JS）→ 定位业务模块    │
└──────────┬───────────────────────────┘
           ↓
┌─ 协议层 ─────────────────────────────┐
│ API 路径 → 鉴权头 → 风控参数           │
└──────────┬───────────────────────────┘
           ↓
┌─ 凭证层 ─────────────────────────────┐
│ token 存储位置 → 加密方案 → 解密链路    │
└──────────┬───────────────────────────┘
           ↓
┌─ 落地层 ─────────────────────────────┐
│ 脚本化 → 实测验证 → 计划任务 → 防检测   │
└─────────────────────────────────────┘
```

每一步都有独立的验证手段，走不通就退回上一层换锚点。

---

## 二、侦察层：先摸清三个目录

| 目标 | 位置规律 | 查看要点 |
|------|---------|---------|
| 安装目录 | `%LOCALAPPDATA%\Programs\<产品名>\`（NSIS 用户级）或 `C:\Program Files\` | `resources\app.asar`（打包型）或 `resources\app\`（明文型）；`resources\*.exe`（native 桥接程序，可能是风控来源） |
| 数据目录 | `%APPDATA%\<产品域名式id>\`（如 `com.xxx.app.stable`）、`%USERPROFILE%\.<产品>\`、`%LOCALAPPDATA%\<产品>\` | 凭证文件（auth/token/storage 字样）、`Local State`（Chromium 主密钥）、`.sqlite`/`.json` 配置 |
| 运行日志 | 数据目录 `logs\`、安装目录 `logs\` | **最高性价比入口**：接口路径、请求头（常被 [redacted] 但结构可见）、响应字段、业务流程时序全都可能直接写在里面 |

> **日志先行原则（Qoder 经验）**：先翻 30 分钟日志再动 asar，可能直接省掉一半逆向工作。Qoder 的 campaigns 接口、9 个请求头、活动数据结构、用户领取时序全部来自 main.log，asar 只用来补解密细节。

数据目录多个变体并存时（如 Qoder 国际版/国内版），用**文件修改时间**判断哪个是活跃主力，写脚本时用数组遍历探测。

---

## 三、代码层：asar 的三种打开方式

### 3.1 按需选择

| 方式 | 适用 | 工具 |
|------|------|------|
| 直接二进制搜索 | 只找字符串（接口路径、中文文案） | `rg -a` / PowerShell `Select-String`；asar 内部文件内容是明文拼接的 |
| 自写解析器 | 需要精确提取单个文件 | 40 行 Node 脚本（推荐，见 3.3） |
| 完整解包 | 需要反复浏览多个文件 | `npx @electron/asar extract`（走 npm 镜像） |

### 3.2 asar 头格式详解（重要：有变体！）

标准 asar 头是 Chromium Pickle 结构，但**不同 Electron 版本字段位置有差异**，别死记，用十六进制实测定：

```
偏移:  0x00        0x04         0x08          0x0C         0x10
     ┌─────────┬──────────┬─────────────┬─────────────┬──────────────┐
     │ =4 固定 │ pickle总长│ jsonLen+4   │ JSON实际长度 │ JSON 文本... │
     └─────────┴──────────┴─────────────┴─────────────┴──────────────┘
文件数据区基址 = 8 + 偏移@4处的值
```

**实测过的两个案例**：
- TeleAgent：JSON 从偏移 16 开始（与 Qoder 相同），网传"偏移 8 开始"不成立
- Qoder：`@12` 才是 JSON 长度（`@4`=1180336、`@8`=1180332、`@12`=1180328），按常见的 `@4 读长度、@8 读 JSON` 会错位 8 字节

**通用口诀**：前 64 字节 hexdump，找 `7B 22 66 69 6C 65 73`（`{"files`）的偏移就是 JSON 起点；JSON 前最后一个 LE32 就是它的长度。

### 3.3 自写解析器骨架（无依赖，可复用）

```js
function readHeader(asarPath) {
  const fd = fs.openSync(asarPath, 'r');
  const head = Buffer.alloc(16); fs.readSync(fd, head, 0, 16, 0);
  const pickleSize = head.readUInt32LE(4);
  const jsonLen = head.readUInt32LE(12);
  const jsonBuf = Buffer.alloc(jsonLen); fs.readSync(fd, jsonBuf, 0, jsonLen, 16);
  fs.closeSync(fd);
  return { header: JSON.parse(jsonBuf.toString()), baseOffset: 8 + pickleSize };
}
// 递归 header.files 列目录；每个文件 {offset, size, unpacked}
// unpacked:true 的文件在 app.asar.unpacked 同名目录，不在包内
```

打包后的业务代码通常在 `out/main/index.js`（主进程）与 `out/renderer/assets/*.js`（渲染层），单行超长，配套一个"关键词前后 N 字符"上下文提取小工具（ctx.js 模式）比打开整个文件高效得多。

---

## 四、协议层：API 与鉴权头的定位

### 4.1 搜索锚点优先级

1. **UI 独有中文文案**（"连续签到""立即领取""领取成功，积分已到账"）——混淆压缩打不散字符串
2. **客户端日志**——接口、头、响应全都有
3. **i18n 键名 / API 路径片段 / 响应字段名**
4. **Web 页面 JS**（功能写在 H5/活动页里的场景）——从日志或配置拿页面 URL，直接下载 CDN bundle 分析

### 4.2 接口不在客户端包里怎么办（Qoder 案例）

活动制功能常把逻辑放在**服务端下发的 Web 页**（Electron 里 webview/iframe 加载），客户端只负责注入凭证。此时：
- 从日志找页面 URL（campaignUrl 之类）
- 下载页面 JS，搜请求路径正则/函数
- 注意宿主分流逻辑：Qoder 活动页里 `clientType==="qoderwake"`（手机 App）走 postMessage 代发，桌面端**直接 fetch + Electron onBeforeSendHeaders 注入头**——所以脚本只要自己带全请求头即可直连，无需模拟页面

### 4.3 风控参数的两类形态

| 形态 | 特征 | 应对 |
|------|------|------|
| 静态参数 | 固定值/简单拼接（`req_source=2`、数字设备 ID） | 逆向时抄下来，写死即可 |
| **动态指纹** | 客户端 spawn 专用 exe/库实时生成（Qoder 的 `runtime-info.exe`） | 别试图伪造；**直接调用客户端自带的桥接程序**，保持参数原样（环境参数、stdin 账号） |

判定动态指纹的方法：请求头名带品牌前缀（Cosy-/X- 等）且值每次变化、日志里 `[redacted]`；在 asar 里搜 `spawn` + 头名能定位到生成代码。

---

## 五、凭证层：token 定位与解密

### 5.1 存储位置速判

| 特征文件 | 说明 |
|---------|------|
| `Local State` 有 `os_crypt.encrypted_key` | Chromium 主密钥体系，凭证大概率是 v10 格式 |
| `*.dat`/`token.json` 以 `76 31 30`（"v10"）开头 | AES-256-GCM 加密，走 5.2 链路 |
| `storage.json` 有加密键（如 `iCubeAuthInfo://...`） | 产品自研加密，逆向解密函数 |
| JSON 文件直接含 `accessToken`/`token` 字段 | 明文，直接读（WorkBuddy） |

### 5.2 v10 + DPAPI 解密链路（TeleAgent / Qoder 通用模板）

```
1. Local State → os_crypt.encrypted_key（base64）→ 去掉前 5 字节 "DPAPI"
2. DPAPI Unprotect（CurrentUser）→ 32 字节 AES 主密钥
   （PowerShell：System.Security.Cryptography.ProtectedData::Unprotect）
3. 密文 = "v10"(3B) + nonce(12B) + ciphertext + tag(16B)
4. AES-256-GCM 解密 → 明文（JWT 或 JSON）
```

> 换机器/重装系统后 DPAPI 主密钥不可迁移——脚本报"登录态失效"时，第一处方是**打开客户端重新登录一次**。

### 5.3 token 生命周期与刷新

- 客户端在线时会自己续期，**脚本默认只读不写**，避免竞争
- 例外：若逆向到了 refresh 接口（Qoder：`POST /api/v1/deviceToken/refresh`），可在 token 临期时主动刷新，并**按客户端同款格式写回**（加密格式一致 + tmp/rename 原子写 + 备份），让客户端与脚本共享最新凭证
- 写回前必须实测"解密→加密→再解密"回环一致

---

## 六、落地层：脚本化与定时任务

### 6.1 脚本设计清单

- [ ] 平台探测用数组遍历（多版本/多数据目录兜底）
- [ ] 凭证解密失败给出**具体处方**（重新登录客户端）而非笼统 error
- [ ] 领取后**复查状态**再报成功（幂等确认）
- [ ] "已签/未到刷新时间"与"失败"分开：前两类退出码 0
- [ ] Node 运行时借用某个已装客户端自带的（零安装），路径写进文档
- [ ] 用 `process.exitCode` 自然退出（Node 24 + Windows 显式 exit 偶发 uv 断言）
- [ ] `require.main === module` 守卫 + `module.exports`：支持独立跑 + 被统一脚本 require 复用

### 6.2 定时任务与防检测

| 层 | 措施 |
|----|------|
| 触发器 | `RandomDelay=PT30M` 打乱固定启动时间 |
| 脚本 | 每次请求前 `sleep(30~300s)` 随机等待 |
| 系统 | `StartWhenAvailable=True`（关机错过则开机补跑） |
| 命名 | 任务名与功能一致（便于总览管理） |

**cmd 入口批处理一律英文注释**——GBK 代码页下中文注释会变乱码命令。

### 6.3 已知环境问题：0xC000013A（3221225786）

从自动化会话里 `Start-ScheduledTask` 手动触发的运行，可能被会话回收波及收到 ^C（Git 同步、Qoder 签到均出现过）。**按时间表自然触发的运行不受影响**（长期定时结果均为 0 可证）。排查口诀：看日志——有"随机等待/签到开始"输出说明被杀前已在工作，属偶发；日志全空才是任务没启动。

---

## 七、五平台速查索引

| 平台 | 加密 | 接口形态 | 风控 | 独立全记录文档 |
|------|------|---------|------|--------------|
| TraeWork | AES-128-CBC+SHA-512 | 固定 status/claim | req_source+数字设备ID | `TraeWork积分API直连-逆向研究全记录.md` |
| Trae CN | 同上 | 同上（共用 API） | 同上 | `TraeCN积分API直连-逆向研究全记录.md` |
| TeleAgent | v10+DPAPI | 固定 GET 三连 | 无签名 | `TeleAgent积分API直连-逆向研究全记录.md` |
| WorkBuddy | 明文 JSON | 固定 POST | Turing Token（可选） | `WorkBuddy积分API直连-逆向研究全记录.md` |
| Qoder | v10+DPAPI | **活动制**（GET 列表→POST claim） | **runtime-info.exe 动态指纹** | `Qoder积分API直连-逆向研究全记录.md` |

横切内容（对照表、token 路径、踩坑全集）见 `五平台积分签到逆向研究总集.md`。

---

## 八、检查清单（新平台逆向一页流）

1. [ ] 找到安装目录/数据目录/日志目录，翻 30 分钟日志
2. [ ] 判定代码形态（明文 or asar），asar 则 hexdump 头部定 JSON 偏移
3. [ ] 用 UI 中文/日志/路径三类锚点定位业务代码
4. [ ] 还原：接口路径、方法、请求体、全部鉴权头
5. [ ] 判定风控形态（静态 or 动态指纹）；动态则找桥接程序调用方式
6. [ ] 定位 token 文件，判定加密类型，打通解密链路
7. [ ] curl/Node 单次实测状态接口（HTTP 200 + 业务字段正确）
8. [ ] 实测领取接口（未领取状态），确认幂等与已领行为
9. [ ] 逆向 token 刷新机制（有则脚本加自续）
10. [ ] 脚本化（按 6.1 清单）→ 计划任务（按 6.2）→ 前台 + 一次性触发器双重验证
11. [ ] 副本与文档归档到 `定时任务总览`（README + 任务清单.json 同步）

> AI生成