# Trae 签到逆向过程

> 独立文档：记录 Trae 每日签到接口的逆向分析过程，可脱离原项目单独阅读。

## 一、目标

实现 Trae（字节跳动 AI IDE）每日签到的自动化：
不打开客户端窗口，直接调用后端 API 完成签到。

## 二、关键结论

| 项 | 值 |
|---|---|
| 状态查询 | `POST https://api.trae.cn/trae/api/v2/ug/checkin_credits/status` |
| 签到领取 | `POST https://api.trae.cn/trae/api/v2/ug/checkin_credits/claim` |
| 鉴权方式 | 请求头 `Authorization: Cloud-IDE-JWT <token>` |
| 必需请求头 | `x-device-id`、`x-device-type`、`x-os-version`、`x-app-version`、`X-User-Region` |
| 请求体 | 固定 `{"req_source": 2}` |
| 凭证位置 | `%APPDATA%\Trae CN\User\globalStorage\storage.json` 的<br>`iCubeAuthInfo://icube.cloudide` 字段（**加密存储**） |
| 设备 ID | `%APPDATA%\Trae CN\ahanet\tt_net_config.config` 的 `device_id`（旧版本：`ModularData\ttnet\` 同名文件 / `ModularData\ckg_server\local_env.json`） |
| 成功判定 | claim 返回 `code: 0`；重复签到由 status 的 `checked_in` 幂等拦截 |
| 签名/加密 | 请求本身**无签名**；难点全在本地凭证的加密存储 |

## 三、逆向步骤

### 1. 凭证定位：token 不在明文里

Trae 是 Electron 应用，用户数据在 `%APPDATA%` 下。
`storage.json` 里**没有**明文 token，只有一个可疑的加密字段：

```
iCubeAuthInfo://icube.cloudide = "<Base64 长字符串>"
```

### 2. 解密算法：AES-128-CBC，密钥从密文自身推导

逆向客户端代码后还原出解密流程（纯算法，无机密外泄）：

```
密文(Base64) = [6B 头][32B key][AES-CBC 密文]
明文 = [64B 前缀][JSON]

keyMaterial = SHA512( key )          (64B)
xorTable    = 内置常量A ^ 内置常量B   (64B，两组写死在客户端)
finalHash   = SHA512( keyMaterial || xorTable )
AES-128 key = finalHash[0:16]
IV          = finalHash[16:32]
```

即：解密所需的全部材料都在密文和客户端常量里，**无需联网、无需用户密码**。
解密后得到 JSON，含 `token` 和 `userRegion.region`。

### 3. 接口定位：checkin_credits 系列

签到功能挂在 `api.trae.cn` 的 ug（用户增长）模块下：

- `POST /checkin_credits/status` —— 查状态：`checked_in`（今日已签）、
  `credits`（当前积分）、`enable`（功能开关）
- `POST /checkin_credits/claim` —— 领取：返回 `code: 0` 为成功

### 4. 请求头分析：设备指纹是硬要求

逐项增删测试后的结论：

| 请求头 | 必需 | 来源 |
|---|---|---|
| `Authorization` | 是 | `Cloud-IDE-JWT ` + 解密出的 token |
| `x-device-id` | 是 | `local_env.json` 的 `device_id`，缺失会被拒 |
| `x-device-type` | 是 | 固定 `Windows` |
| `x-os-version` | 是 | `os.release()` 现取 |
| `x-app-version` | 建议 | 从安装目录 `resources/app/package.json` 读 version |
| `X-User-Region` | 建议 | 解密 JSON 的 `userRegion.region` |

### 5. 幂等性确认

签到前先查 status：`checked_in=true` 直接跳过。
因此定时任务重复触发、手动补跑都安全。

### 6. 凭证保活

token 会过期（客户端升级、长期未用、服务端会话失效）。
失效表现：status 接口返回 HTTP 401/403。

处理方式：**打开 Trae 客户端重新登录**，`storage.json` 的加密块即被刷新，
脚本下次运行自动读取新值，无需修改任何配置。

## 四、落地调用链

```
storage.json 读 iCubeAuthInfo 加密块
      │  AES-128-CBC 解密（密钥材料由密文+常量推导）
      ▼
拼请求头（Cloud-IDE-JWT + 设备指纹 + 版本/区域）
      │
      ▼
POST status ──► checked_in? 已签则结束
      │ 否
      ▼
随机延迟 30~300 秒（防检测，--no-delay 可跳过）
      │
      ▼
POST claim ──► code 0 成功
      │
      ▼
再 POST status 复查积分
```

- **零依赖**：只用 Node 18+ 内置模块（`fetch` / `crypto.subtle` / `fs`）
- **零配置**：凭证、设备 ID、版本号全部现场自动探测
- **无硬编码路径**：`%APPDATA%` 动态定位 + 注册表探测安装位置，
  新旧客户端目录名（Trae CN / TRAE SOLO CN）自动适配

## 五、合规说明

本逆向仅涉及读取并解密本机自己账号的登录态，调用平台自身的公开接口；
未绕过任何服务端校验（设备指纹等照实提供）。仅限个人学习研究，
请遵守平台条款。
