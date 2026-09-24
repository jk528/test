---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4789deb7-0f68-4a8e-915c-0a9066e6dad1'
  PropagateID: '4789deb7-0f68-4a8e-915c-0a9066e6dad1'
  ReservedCode1: '65fdf0e1-1f71-4a0d-a24d-9c989b1141f2'
  ReservedCode2: '65fdf0e1-1f71-4a0d-a24d-9c989b1141f2'
---

# TraeWork 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-09-18（回溯建档）
> 目标：逆向 TraeWork（TRAE SOLO CN 桌面端）的签到功能，实现后台 API 直连签到
> 结论：**已成功**。签到脚本已集成到 `checkin_all.js` 统一脚本中，定时任务已绑定
> TraeWork = 字节跳动 TRAE SOLO CN 桌面端（AI 编程助手），产品域名 api.trae.cn

---

## 一、最终结果速览

### 当前生效配置

| 项目 | 值 |
|------|-----|
| 脚本 | `checkin_all.js`（统一签到脚本，含 4 个平台） |
| 入口 | `run_checkin_all.cmd` |
| 定时任务 | `TraeWork积分签到`（每天 00:10） |
| 日志 | `桌面\定时任务脚本\checkin.log` |
| 实测输出 | `今日已签到。积分：200` |

### TraeWork 与其他签到的关系

TraeWork 是本机最早逆向的签到方案，其加密方案与 Trae CN 完全一致（同一产品方字节跳动、同一 API 域名、同一套 AES-128-CBC 解密逻辑），仅数据目录不同。后来 Trae CN 的逆向直接复用了本方案的解密代码。

---

## 二、产品信息

| 维度 | 值 |
|------|-----|
| 产品名 | TraeWork（桌面端显示名：TRAE SOLO CN） |
| 产品方 | 字节跳动 |
| 进程名 | `TRAE SOLO CN.exe` |
| 安装目录 | `%LOCALAPPDATA%\Programs\TRAE SOLO CN\` |
| 数据目录 | `%APPDATA%\TRAE SOLO CN\` |
| 客户端版本 | 1.107.1 |
| 代码包 | `resources\app\`（未打包为 asar，明文 JS） |

---

## 三、逆向思路全流程

### 第 1 步：定位安装与数据目录

```powershell
# 从进程命令行参数找到 --user-data-dir
Get-CimInstance Win32_Process -Filter "Name='TRAE SOLO CN.exe'" | Select CommandLine
# → --user-data-dir 指向 %APPDATA%\TRAE SOLO CN
```

### 第 2 步：在客户端代码中搜索签到接口

TraeWork 代码未打包为 asar，直接在 `resources\app\out\` 目录里，搜索更快：

```powershell
$rg -a -o -N "/[a-zA-Z0-9/_\-]*checkin[a-zA-Z0-9/_\-]*" "...\out" | Where-Object { $_ -notmatch "checking" }
# 结果:
#   /trae/api/v2/ug/checkin_credits/claim
#   /trae/api/v2/ug/checkin_credits/status
```

### 第 3 步：确认 API 域名

从 `product.json` 和代码中确认 API 域名为 `https://api.trae.cn`。

### 第 4 步：分析鉴权机制

从渲染层代码追踪到 `fetchCheckinCreditsStatus` → `claimCheckinCredits` 方法，调用 `this.eb(path, method, apiName)` 统一请求封装。

鉴权头：

```js
{
  'Authorization': `Cloud-IDE-JWT ${auth.token}`,
  'Content-Type': 'application/json',
  'x-device-id': deviceId,      // 纯数字设备 ID
  'x-device-type': 'Windows',
  'x-os-version': os.release(),
  'x-app-version': appVersion,
  'X-User-Region': auth.userRegion?.region  // 可选
}
```

请求体固定为 `{"req_source": 2}`。

### 第 5 步：定位 token 存储

token 存储在 `%APPDATA%\TRAE SOLO CN\User\globalStorage\storage.json`，键名 `iCubeAuthInfo://icube.cloudide`，值为 Base64 加密字符串。

设备 ID 存储在 `%APPDATA%\TRAE SOLO CN\ModularData\ckg_server\local_env.json` 的 `device_id` 字段（纯数字格式）。

### 第 6 步：分析加密方案

```
密文结构（Base64 解码后的字节数组）:
  [0..5]   = 6 字节头部（Em=6）
  [6..37]  = 32 字节 key（Rv=32）
  [38..]   = AES-128-CBC 密文

解密链路:
  1. 提取 key = ciphertext[6:38]
  2. SHA-512(key) → 64 字节
  3. XOR(ure, dre) → 64 字节（两个 62 字节内置常量数组异或，补零到 64）
  4. 拼接 [SHA-512(key)(64) + XOR(64)] → 128 字节
  5. SHA-512(128字节) → 64 字节
  6. AES 密钥 = hash[0:16]，IV = hash[16:32]
  7. AES-128-CBC 解密 ciphertext[38:]
  8. 去掉前 64 字节（rh=64）→ 明文 JSON
```

内置常量数组 `ure` 和 `dre` 各 62 字节，硬编码在客户端 JS 中：

```javascript
const ure = Uint8Array.from([82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37]);
const dre = Uint8Array.from([31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125]);
```

### 第 7 步：接口实测

| 接口 | 方法 | 实测结果 |
|------|------|---------|
| `/trae/api/v2/ug/checkin_credits/status` | POST `{"req_source":2}` | 200，返回 `checked_in / credits / enable / extra_credits` |
| `/trae/api/v2/ug/checkin_credits/claim` | POST `{"req_source":2}` | 200，`code===0` 表示领取成功 |

---

## 四、遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|---------|
| 1 | 设备 ID 用 UUID 格式报 9074 | 服务端要求纯数字格式 | 从 `local_env.json` 读 `device_id`（纯数字如 `1963102595468793`） |
| 2 | 缺少 `req_source` 参数报 9004 | 服务端要求标识请求来源 | 请求体固定 `{"req_source": 2}`（2 表示桌面端） |
| 3 | 解密后 JSON 前面有 64 字节垃圾数据 | 解密结果包含头部填充 | `dec.slice(64)` 去掉前 64 字节（rh=64） |
| 4 | 运行时需要 Node.js 但不想安装 | 用户偏好零安装 | 复用 TRAE SOLO CN 自带的 Electron（`ELECTRON_RUN_AS_NODE=1`），后改为借用 TeleAgent 的 Node |

---

## 五、接口清单

网关：`https://api.trae.cn`

| 用途 | 方法 + 路径 | 请求体 | 鉴权头 |
|------|------------|--------|--------|
| 签到状态 | POST `/trae/api/v2/ug/checkin_credits/status` | `{"req_source":2}` | `Authorization: Cloud-IDE-JWT <token>` + `x-device-id` + `x-device-type` + `x-os-version` + `x-app-version` |
| 领取积分 | POST `/trae/api/v2/ug/checkin_credits/claim` | `{"req_source":2}` | 同上 |

签到状态响应字段：

```json
{
  "checked_in": true,
  "code": 0,
  "credits": 200,
  "did_checked_in": true,
  "enable": true,
  "extra_credits": 50,
  "message": "success"
}
```

---

## 六、关键文件路径速查

| 文件 | 路径 |
|------|------|
| 统一签到脚本 | `C:\Users\Administrator\Desktop\定时任务脚本\checkin_all.js` |
| 统一签到入口 | `C:\Users\Administrator\Desktop\定时任务脚本\run_checkin_all.cmd` |
| 加密登录态 | `%APPDATA%\TRAE SOLO CN\User\globalStorage\storage.json` → `iCubeAuthInfo://icube.cloudide` |
| 设备 ID | `%APPDATA%\TRAE SOLO CN\ModularData\ckg_server\local_env.json` → `device_id` |
| 客户端版本 | `%LOCALAPPDATA%\Programs\TRAE SOLO CN\resources\app\package.json` → `version` |
| 客户端代码 | `%LOCALAPPDATA%\Programs\TRAE SOLO CN\resources\app\out\` (未打包) |

---

## 七、排障指南

### 登录态过期

打开 TRAE SOLO CN 客户端重新登录，`storage.json` 会刷新。

### 风控拒绝（code 9004 / 9074）

- 9004：检查请求体是否包含 `{"req_source": 2}`
- 9074：检查 `x-device-id` 是否为纯数字格式（从 `local_env.json` 读取）

### 客户端升级后接口变更

```powershell
$rg = "C:\Program Files\TeleAgent\resources\ripgrep\win32-x64\rg.exe"
& $rg -a -o -N "/[a-z0-9/_\-]*checkin[a-z0-9/_\-]*" "C:\Users\Administrator\AppData\Local\Programs\TRAE SOLO CN\resources\app\out" | Where-Object { $_ -notmatch "checking" }
```

---

*本文档由回溯建档生成，基于 TraeWork v1.107.1 客户端代码静态分析 + 接口实测。*

> AI生成