---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '688fb190-3174-4a7f-b610-8d08e99393fb'
  PropagateID: '688fb190-3174-4a7f-b610-8d08e99393fb'
  ReservedCode1: '9150fa5b-01c2-4188-87ee-78b9365c9e0b'
  ReservedCode2: '9150fa5b-01c2-4188-87ee-78b9365c9e0b'
---

# Trae CN 积分签到 API 直连 —— 逆向研究全记录

> 研究日期：2026-09-18
> 目标：逆向 Trae CN 桌面客户端的签到功能，实现后台 API 直连签到
> 结论：**已成功**。脚本已产出并实测通过，定时任务已绑定
> 注意：Trae CN 与 TraeWork（TRAE SOLO CN）是**两个不同的产品**，但签到 API 完全一致

---

## 一、最终结果速览

### 交付文件

| 文件 | 说明 |
|------|------|
| `traecn_checkin.js` | 核心签到脚本（Node.js，API 直连） |
| `run_traecn_checkin.cmd` | Windows 执行入口 |
| `本文件` | 逆向研究全记录 |

### 实测输出

```
2026/9/18 20:30:50 今日已签到。积分：200（含额外 50）
退出码: 0
```

### 定时任务

| 项目 | 值 |
|------|-----|
| 任务名 | TraeCN积分签到 |
| 执行时间 | 每天 01:20 |
| 日志 | `桌面\定时任务脚本\checkin_traecn.log` |
| 补跑 | 01:20 关机则开机后自动补跑 |

---

## 二、Trae CN 与 TraeWork 的关系

### 两个独立产品

| 维度 | TraeWork（TRAE SOLO CN） | Trae CN |
|------|------------------------|---------|
| 进程名 | `TRAE SOLO CN.exe` | `Trae CN.exe` |
| 安装目录 | `%LOCALAPPDATA%\Programs\TRAE SOLO CN\` | `%LOCALAPPDATA%\Programs\Trae CN\` |
| 数据目录 | `%APPDATA%\TRAE SOLO CN\` | `%APPDATA%\Trae CN\` |
| 桌面快捷方式 | `TRAE Work CN.lnk` | `Trae CN.lnk` |
| 客户端版本 | 1.x（TraeWork 版本号） | 1.107.1 |
| 已有签到脚本 | `checkin.js`（每日签到任务 00:10） | `traecn_checkin.js`（本次产出） |

### 签到 API 完全一致

| 维度 | TraeWork | Trae CN | 差异 |
|------|----------|---------|------|
| API 域名 | `api.trae.cn` | `api.trae.cn` | **无** |
| 接口路径 | `/trae/api/v2/ug/checkin_credits/status` | 同左 | **无** |
| 领取路径 | `/trae/api/v2/ug/checkin_credits/claim` | 同左 | **无** |
| token 加密 | AES-128-CBC + SHA-512 + 内置常量表 | 同左 | **无** |
| 鉴权头 | `Cloud-IDE-JWT` + `x-device-id` 等 | 同左 | **无** |
| req_source | 2 | 2 | **无** |
| 数据目录 | `%APPDATA%\TRAE SOLO CN\` | `%APPDATA%\Trae CN\` | **不同** |
| 设备 ID 来源 | `TRAE SOLO CN\ModularData\ckg_server\local_env.json` | `Trae CN\ModularData\ckg_server\local_env.json` | **路径不同** |
| 版本号来源 | `TRAE SOLO CN\resources\app\package.json` | `Trae CN\resources\app\package.json` | **路径不同** |

**结论**：Trae CN 签到脚本 = TraeWork 签到脚本 + 改数据目录路径。解密逻辑、API 调用、鉴权头全部复用。

---

## 三、逆向思路全流程

### 第 1 步：确认产品差异

```powershell
# 发现两个不同进程
Get-Process -Name "*trae*","*Trae*"
# Trae CN.exe        → C:\Users\Administrator\AppData\Local\Programs\Trae CN\
# TRAE SOLO CN.exe   → C:\Users\Administrator\AppData\Local\Programs\TRAE SOLO CN\
```

桌面上有两个快捷方式：`Trae CN.lnk` 和 `TRAE Work CN.lnk`，确认是**两个独立产品**。

### 第 2 步：定位数据目录

```powershell
# 安装目录（注意：没有 app.asar，代码在 resources\app 目录里未打包）
C:\Users\Administrator\AppData\Local\Programs\Trae CN\

# 数据目录
C:\Users\Administrator\AppData\Roaming\Trae CN\
  ├── User\globalStorage\storage.json     ← 加密登录态
  ├── ModularData\ckg_server\local_env.json  ← 设备 ID
  └── Local State                           ← Chromium 主密钥（未使用）
```

> Trae CN 没有 `app.asar`，代码以明文形式放在 `resources\app\` 目录里。这比 TeleAgent/WorkBuddy 的 asar 打包更容易搜索。

### 第 3 步：搜索签到接口

```powershell
$rg = "C:\Program Files\TeleAgent\resources\ripgrep\win32-x64\rg.exe"
$app = "C:\Users\Administrator\AppData\Local\Programs\Trae CN\resources\app\out"

# 直接搜 checkin 路径（未打包代码搜索更快）
& $rg -a -o -N "/[a-zA-Z0-9/_\-]*checkin[a-zA-Z0-9/_\-]*" $app | Where-Object { $_ -notmatch "checking" }
# 结果:
#   /trae/api/v2/ug/checkin_credits/claim
#   /trae/api/v2/ug/checkin_credits/status
```

**关键发现**：路径与 TraeWork 完全一致，说明共用同一套后端 API。

### 第 4 步：确认 API 域名

```powershell
# product.json 中的域名配置
& $rg -a -o -N "https://[a-z0-9.\-]+" "$app\..\product.json" | Group-Object | Sort-Object Count -Descending
# 结果:
#   api.trae.com.cn      (7次) ← product.json 里配的域名
#   trae-api-cn.mchost.guru (5次) ← 内部/staging 域名
```

但实测发现 `api.trae.com.cn` 返回 404。用三个候选域名测试：

```javascript
// 测试结果:
https://api.trae.com.cn      → HTTP 404 (此域名不提供签到API)
https://api.trae.cn           → HTTP 200 ✓ (签到API实际在这个域名)
https://trae-api-cn.mchost.guru → HTTP 404
```

**关键发现**：虽然 `product.json` 配了 `api.trae.com.cn`，但签到 API 实际在 `api.trae.cn`——与 TraeWork 完全相同。这说明两个产品共用同一套后端服务。

### 第 5 步：验证 token 格式一致性

```powershell
# storage.json 中的加密 token
$j = Get-Content "$env:APPDATA\Trae CN\User\globalStorage\storage.json" -Raw | ConvertFrom-Json
$j.'iCubeAuthInfo://icube.cloudide'  # 存在，长度 2484

# local_env.json 中的设备 ID
Get-Content "$env:APPDATA\Trae CN\ModularData\ckg_server\local_env.json"
# {"device_id":"1963102595468793",...}  ← 纯数字格式，与 TraeWork 一致
```

token 加密格式（`iCubeAuthInfo://icube.cloudide`）和设备 ID 格式（纯数字）完全一致，可直接复用 TraeWork 的解密逻辑。

### 第 6 步：接口实测

```javascript
// 只读状态验证
POST https://api.trae.cn/trae/api/v2/ug/checkin_credits/status
→ HTTP 200 {"checked_in":true,"code":0,"credits":200,"did_checked_in":true,"enable":true,"extra_credits":50,"message":"success"}
```

---

## 四、遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|---------|
| 1 | `api.trae.com.cn` 返回 404 | product.json 配的域名不是签到 API 的实际域名 | 多域名测试，发现 `api.trae.cn` 才是正确域名（与 TraeWork 一致） |
| 2 | 桌面上有 Trae CN 和 TRAE Work CN 两个快捷方式 | 两个独立产品，共用同一套后端 API | 分别创建签到脚本和定时任务 |
| 3 | Trae CN 没有 app.asar | 代码未打包，直接在 `resources\app\` 目录 | 搜索更快，不需要解析 asar 头部 |
| 4 | `local_env.json` 中 `host` 字段为空 | `host_map` 的 `default` 也是空串 | 不影响签到，`api.trae.cn` 是硬编码的 |

---

## 五、生产脚本架构

```
run_traecn_checkin.cmd → traecn_checkin.js
                              │
    ┌─────────────────────────┤
    │ 1. 读取加密登录态        │
    │   %APPDATA%\Trae CN\User\globalStorage\storage.json
    │   → iCubeAuthInfo://icube.cloudide (AES-128-CBC 加密)
    │                         │
    │ 2. AES-128-CBC 解密     │
    │   SHA-512(key) + XOR(ure,dre) → AES key + IV
    │   → JSON { token, userRegion }
    │                         │
    │ 3. 读取设备 ID           │
    │   %APPDATA%\Trae CN\ModularData\ckg_server\local_env.json
    │   → device_id (纯数字)
    │                         │
    │ 4. 查状态 POST status   │
    │   checked_in=true → 输出"今日已签到"并退出(0)
    │   checked_in=false → 继续
    │                         │
    │ 5. 领取 POST claim      │
    │   code===0 → 签到成功   │
    │                         │
    │ 6. 刷新状态获取最新积分  │
    └─────────────────────────┘
```

---

## 六、接口清单

网关：`https://api.trae.cn`（与 TraeWork 共用）

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

## 七、关键文件路径速查

| 文件 | 路径 |
|------|------|
| 签到脚本 | `C:\Users\Administrator\Desktop\定时任务脚本\traecn_checkin.js` |
| 签到入口 | `C:\Users\Administrator\Desktop\定时任务脚本\run_traecn_checkin.cmd` |
| 签到日志 | `C:\Users\Administrator\Desktop\定时任务脚本\checkin_traecn.log` |
| 加密登录态 | `%APPDATA%\Trae CN\User\globalStorage\storage.json` → `iCubeAuthInfo://icube.cloudide` |
| 设备 ID | `%APPDATA%\Trae CN\ModularData\ckg_server\local_env.json` → `device_id` |
| 客户端版本 | `%LOCALAPPDATA%\Programs\Trae CN\resources\app\package.json` → `version` |
| 客户端代码 | `%LOCALAPPDATA%\Programs\Trae CN\resources\app\out\` (未打包) |

---

## 八、排障指南

### 登录态过期

```
现象: 错误：登录态读取/解密失败
```

打开 Trae CN 客户端重新登录，`storage.json` 会刷新。

### 设备 ID 缺失

```
现象: 警告：未找到设备 ID，签到可能被服务端拒绝
```

检查 `local_env.json` 是否存在。Trae CN 首次启动后会自动生成。

### API 返回 404

确认使用的是 `api.trae.cn`（不是 `api.trae.com.cn`）。product.json 中的 `api.trae.com.cn` 不是签到 API 的域名。

### 客户端升级后接口变更

```powershell
# 搜索新接口路径
$rg = "C:\Program Files\TeleAgent\resources\ripgrep\win32-x64\rg.exe"
& $rg -a -o -N "/[a-z0-9/_\-]*checkin[a-z0-9/_\-]*" "C:\Users\Administrator\AppData\Local\Programs\Trae CN\resources\app\out" | Where-Object { $_ -notmatch "checking" }
```

---

## 九、四套签到方案完整对照

| 维度 | TraeWork | Trae CN | TeleAgent | WorkBuddy |
|------|----------|---------|-----------|-----------|
| 产品方 | 字节跳动 | 字节跳动 | 中电信人工智能 | 腾讯 |
| 数据目录 | `%APPDATA%\TRAE SOLO CN\` | `%APPDATA%\Trae CN\` | `%USERPROFILE%\.local\share\TeleAgent\` | `%LOCALAPPDATA%\CodeBuddyExtension\` |
| token 加密 | AES-CBC+SHA-512 | **同 TraeWork** | DPAPI+AES-256-GCM | 明文 JSON |
| API 域名 | api.trae.cn | **api.trae.cn** | agent.teleai.com.cn | copilot.tencent.com |
| 定时任务 | 每日签到 00:10 | **TraeCN积分签到 01:20** | TeleAgent积分签到 01:00 | WorkBuddy积分签到 01:10 |
| 脚本文件 | checkin.js | **traecn_checkin.js** | teleagent_checkin.js | workbuddy_checkin.js |

---

*本文档由逆向分析生成，基于 Trae CN v1.107.1 客户端代码静态分析 + 接口实测。*

> AI生成