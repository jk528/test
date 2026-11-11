# Trae Linux 客户端逆向与服务器原生身份部署记录

> 逆向日期：2026-11-12　|　状态：**逆向完成，服务器部署到"设备身份生成"一步，最后验证被暂停**
> 目标：在华为云 2核2G 服务器（x86_64）上实现 Trae 每日签到，使用 **Linux 原生设备身份**，
> 避免出现"同一设备指纹（Windows device_id）出现在不同 IP（云端机房）"的风控风险。
> 关联文档：
> - [trae本地化与修复总结.md](../04-维护-巡检排障/trae本地化与修复总结.md)（Windows 侧全史）
> - [Trae积分API直连-逆向研究全记录.md](签到逆向研究/Trae积分API直连-逆向研究全记录.md)（接口合并版）
> - [02-提取 Trae 凭证.md](../05-服务器部署/02-提取%20Trae%20凭证.md)（现有 Windows 凭证外带方案）
> - 现行服务器脚本：`.temp/trae_checkin_server.js`（已部署于 `/opt/trae-checkin/`）

---

## 一、任务目标

| 项 | 内容 |
|---|---|
| 需求来源 | 在华为 2C2G 服务器上签到 Trae，担心 IP 与设备指纹不一致导致无法签到/风控 |
| 技术路线 | 下载官方 Trae Linux 客户端 → 参照 Windows 逆向步骤逆向 → 在服务器生成 Linux 原生设备身份 → Linux 原生脚本签到 |
| 服务器 | `root@121.36.27.69`（SSH 公钥免密可用） |

---

## 二、Linux 客户端获取与拆包

### 2.1 官方下载地址（实测抓取）

下载页 `https://www.trae.cn/ide/download` 的按钮是前端动态生成 URL，直接抓 HTML 拿不到。
本次用浏览器自动化点击「.deb (x64)」菜单项，从网络请求中抓到真实直链：

```
https://lf-cdn.trae.com.cn/obj/trae-com-cn/pkg/app/releases/stable/2.3.102387/linux/TRAE_CN-linux-x64.deb
```

- 大小：475.5 MB，HTTP 200，CDN 直链无鉴权，可直接 `curl -L` / `wget`
- 下载页同时提供四个变体：`.deb (x64)`、`.rpm (x64)`、`.deb (arm64)`、`.rpm (arm64)`（arm64 直链按同目录推测为 `TRAE_CN-linux-arm64.deb`，未实测）
- 版本规律：URL 中 `stable/2.3.102387` = `product.json` 的 `tronBuildVersion`，后续版本号变了改这个路径即可

### 2.2 拆包步骤（Windows 本机即可完成）

deb = ar 容器，Windows 自带 bsdtar 可解第一层；xz 需要 7-Zip（官方单文件 `7zr.exe` 即可）：

```powershell
# 1) 解 ar 容器
tar -xf TRAE_CN-linux-x64.deb -C trae_deb
#   → debian-binary / control.tar.xz / data.tar.xz

# 2) 解 xz（7zr.exe 下载自 https://www.7-zip.org/a/7zr.exe）
7zr.exe x trae_deb\data.tar.xz -otrae_data     # → data.tar (1.8GB)

# 3) 解 tar
tar -xf trae_data\data.tar -C trae_root
#   → usr/share/trae-cn/（完整程序目录）
```

### 2.3 包内结构关键发现

| 项 | 值 |
|---|---|
| 安装目录 | `/usr/share/trae-cn/`，入口 `/usr/bin/trae-cn` |
| 代码打包 | **明文 JS（无 app.asar）**：`resources/app/out/main.js`（3.3MB）+ `out/vs/**` |
| `package.json` version | `1.107.1`（VS Code 基线版本，**不是**对外版本） |
| `product.json` appVersion | **`3.4.18`**（真正发到 `x-app-version` 的值） |
| `product.json` tronBuildVersion | `2.3.102387` |
| nameShort / 应用名 | `Trae CN`（Linux userData 目录名同 Windows） |
| dataFolderName | `.trae-cn`（远程 server 数据目录，与本机无关） |
| deb 依赖 | GTK3/ALSA/NSS/NSS 等 ~30 个库，`Installed-Size: 1773786 KB`（≈1.7GB） |
| deb Version | `1.107.1-1794319913` |

> **版本号勘误**：现有 `extract_trae_cred.js` / 服务器脚本取的是 `package.json` 的 `1.107.1`，
> 但 Linux 客户端真实发送 `x-app-version: 3.4.18`（product.json 的 `appVersion`）。历史一直能用说明服务端未强校验，
> 但**新脚本应改为读 product.json 的 appVersion**，与客户端行为完全对齐。

---

## 三、逆向核心结论（Linux main.js 逐段分析）

### 3.1 登录态加密：与 Windows 完全一致，跨平台通用 ✅

`out/main.js` 内嵌 `out-build/vs/base/common/byteCrypto.js`，与 Windows 逆向出的算法逐字节相同：

```
密文(Base64) = [6B 魔数头][32B key][AES-CBC 密文]
魔数头固定     = 116, 99, 5, 16, 0, 0（sL,rL,nL,oL,aL,cL）
派生：SHA512(key) ⊕(Jhe^Khe 常量表, 64B) → 拼接 → SHA512 → 前16B=AES key, 16-32B=IV
明文 = [64B SHA512 校验前缀][JSON]，解密后剥除前 64B
```

- 常量表 `Jhe`/`Khe` 与 Windows 脚本里的 `ure`/`dre` **完全相同**（82,9,106,213… / 31,221,168,51…）
- 另有 `AES_PRIVATE` 变体（魔数 18,57,32,32,2,3，用 zhe^Ghe 表），当前登录态走普通 `AES` 变体
- **不涉及 Electron safeStorage / DPAPI / keyring**（safeStorage 只用于别的值），因此
  Windows 解出的 token 可以直接在 Linux 侧使用，`decryptTrae()` 代码零改动可复用

### 3.2 签到接口与鉴权：不变 ✅

- `POST https://api.trae.cn/trae/api/v2/ug/checkin_credits/status|claim`，body `{"req_source":2}`
- `Authorization: Cloud-IDE-JWT <token>`，`X-User-Region: CN`

### 3.3 设备请求头构造：由 commonParams 动态生成（平台相关）

主进程 `ob(e)`（checkinLottery / workBenefit 等共用）注入逻辑：

```js
e["x-device-id"]    = guaranteedDeviceId;              // ahaDeviceService
const i = commonParams;
i?.device_model     && (e["x-device-brand"]   = i.device_model);   // 新增头（可选）
i?.os_name          && (e["x-device-type"]    = i.os_name);
i?.os_version       && (e["x-os-version"]     = i.os_version);
i?.app_version      && (e["x-app-version"]    = i.app_version);
```

`iCubeSystemInformationService` 各平台取值（Linux 分支读 `/etc/os-release`）：

| 请求头 | Windows 现值 | Linux 实际值（本服务器实测） |
|---|---|---|
| `x-device-type`（osName） | `windows` | **`linux`**（process.platform 原样小写） |
| `x-os-version`（osVersion） | `10.0.20348` | **`PRETTY_NAME`** → `Ubuntu 24.04.4 LTS` |
| `x-os-release`（osRelease，仅上报） | 内核号 | `VERSION_ID` → `24.04` |
| `x-app-version` | 3.4.18 | `3.4.18`（product.json） |
| `x-device-brand`（deviceModel，可空不发） | 机型 | 服务器为空 → 不发 |

> 结论：**Linux 原生身份 = 新 device_id + `x-device-type: linux` + `x-os-version: Ubuntu 24.04.4 LTS` + `x-app-version: 3.4.18`**。

### 3.4 device_id 的来源与形态

- 代码链：`iCubeDeviceRegisterMainService` → `ahaDeviceService`（字节魔改 Electron 内置模块，非 JS 实现）
- `guaranteedDeviceId = deviceId || localDeviceId`
- **本地身份（未注册时）是 UUID**：服务器首启崩溃日志实证 `local_device_id/device_id = fba4cfe9-d33a-…`
- **注册后的远端身份是 16 位纯数字**：Windows 本机 `ahanet/tt_net_config.config` 实测
  `device_id&#*1870736766583371@$*tnc_abtest&#*…`（纯数字 1870…，与 2026-10-28 迁移结论一致）
- 数字 ID 大概率在**登录态生效、客户端向服务端注册设备**后由 aha 分发并写回 `ahanet/tt_net_config.config`
  （Windows 上 `has_device_id_updated_to_aha=true` 后清除旧 `device_id`/`install_id` 存储键，佐证"更新到 aha"这一动作）
- ⚠️ Windows 历史教训：UUID 型 device_id 打到签到接口返回 9074 风控（当时是 VS Code 的 telemetry UUID）；
  aha 的 localDeviceId UUID 是否被服务端接受**未实测**

### 3.5 JWT 载荷：无设备绑定 ✅

本机现登录态 token（len=1004）解码：

```json
{ "data": { "id": "4361129547281210", "source": "refresh_token", "source_id": "…",
            "tenant_id": "7o2d894p7dr0o4", "type": "user" },
  "iat": 1794372899, "exp": 1795582499 }
```

- **不含 device_id**：token 与设备解耦，同一个 token 配任何 device_id 服务端协议层都收
- 有效期 **14 天**（iat≈2026-11-11 → exp≈2026-11-25），到期重跑 `extract_trae_cred.js` 即可
- 风控层面 device_id 只作为风控信号，不参与鉴权

---

## 四、服务器连接与操作实录（2026-11-12）

### 4.1 服务器现状确认（SSH 公钥免密连通）

| 检查项 | 结果 |
|---|---|
| `uname -m` | `x86_64` |
| 系统 | `Ubuntu 24.04.4 LTS`（PRETTY_NAME） |
| Node | `v22.22.1`（已有） |
| Xvfb | **已装**（`/usr/bin/xvfb-run`、`/usr/bin/Xvfb`，此前部署遗留） |
| 磁盘 | `/` 40G 已用 9.4G，剩 29G（装 1.7GB 客户端无压力） |
| 内存 | 总 1775M，可用约 1.1G（跑 Electron 需 `--disable-gpu`，一次性短跑可行） |
| 既有目录 | `/opt/trae-checkin/`（现行 Windows 凭证版脚本 + `trae_cred.json` + cron 00:10） |

### 4.2 已完成的操作

```bash
# ① 服务器直连 CDN 下载（476MB，约 6 分钟，1.3MB/s）
curl -L -o /tmp/trae-cn.deb 'https://lf-cdn.trae.com.cn/obj/trae-com-cn/pkg/app/releases/stable/2.3.102387/linux/TRAE_CN-linux-x64.deb'

# ② 安装（自动补齐 GTK 等依赖，成功）
DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/trae-cn.deb
#   → Setting up trae-cn (1.107.1-1794319913)，/usr/bin/trae-cn 可用

# ③ 首次启动（隔离 profile，避免污染 /root/.config）
mkdir -p /opt/trae-checkin/profile
timeout 90 xvfb-run -a /usr/bin/trae-cn --no-sandbox --disable-gpu \
    --disable-dev-shm-usage --user-data-dir=/opt/trae-checkin/profile > /tmp/trae_first.log 2>&1
```

首次启动观察：

- 进程能起来（无缺库报错），90 秒后被 timeout 结束时触发了 aha 崩溃上报（正常关停路径的 FATAL，可忽略）
- **崩溃日志拿到关键证据**：`local_device_id = fba4cfe9d33a4a749961ed6251af2198`（UUID），
  `device_id` 同值 → 未登录/未注册状态下 aha 只有本地 UUID，**无 `tt_net_config.config` 文件生成**
- profile 下仅生成 `aha/`（空）、`Crashpad/`、`logs/`，主程序日志只有一行 `No config file found`
  （这是 product.json 附带 `Local Storage/config.db` 的 md5 解密探测，无 config.db 时的正常输出，非报错）

### 4.3 登录态注入（已做，验证被暂停）

```powershell
# Windows 本机 → 服务器
scp "$env:APPDATA\Trae CN\User\globalStorage\storage.json" \
    root@121.36.27.69:/opt/trae-checkin/profile/User/globalStorage/storage.json
ssh root@121.36.27.69 chmod 600 /opt/trae-checkin/profile/User/globalStorage/storage.json
```

随后计划用同样命令再启动 150 秒验证 `ahanet/tt_net_config.config` 是否生成（数字 ID），
**该步检查命令被拒绝执行，验证暂停**。按现有证据推断：

- `storage.json` 的 `iCubeAuthInfo://icube.cloudide` 是纯算法加密，Linux 客户端可正常解出 token → 客户端应视为已登录
- 登录生效后 aha 完成设备注册 → 写出数字 device_id（与 Windows 行为一致）
- **此推断尚未实测确认**

### 4.4 服务器遗留物清单（含敏感项）

| 位置 | 内容 | 处理建议 |
|---|---|---|
| `/tmp/trae-cn.deb` | 安装包 476MB | 可删 `rm /tmp/trae-cn.deb` |
| 已安装包 `trae-cn` | 1.7GB 程序 | 方案 A 需要，保留；放弃则 `apt-get remove --purge trae-cn` |
| `/opt/trae-checkin/profile/` | Linux 客户端 profile，**含注入的 storage.json（内含账号 token）** | ⚠️ 敏感：`chmod -R go-rwx /opt/trae-checkin/profile`；放弃则整目录删除 |
| `/opt/trae-checkin/trae_cred.json` | Windows 凭证（现行方案） | 原样保留，勿动 |
| `/tmp/trae_first.log` `/tmp/trae_second.log` | 启动日志 | 可删 |

> Windows 本机 `.temp/` 下本次新增：`TRAE_CN-linux-x64.deb`（475MB）、`trae_root/`（解包 1.8GB）、
> `trae_cred.json`（**等同账号密码，已在 .temp，确认 .gitignore 覆盖**）、若干扫描脚本与中间产物。
> 逆向结论已全部写入本文档，这些中间产物可清理。

---

## 五、方案对比与结论

### 方案 A：Linux 原生身份（本次目标，推荐，差最后一步验证）

```
token：Windows storage.json 解出（14 天有效，到期重提）
        │  注入 Linux 客户端 profile → 启动一次 → aha 注册设备
        ▼
device_id：/opt/trae-checkin/profile/ahanet/tt_net_config.config 正则提取（数字 ID）
请求头：x-device-id=<Linux数字ID>  x-device-type=linux
        x-os-version=<PRETTY_NAME>  x-app-version=3.4.18
```

- 服务端视角：一个"正常的 Linux 新设备"在机房 IP 登录并签到 —— 指纹自洽，无跨 IP 同设备矛盾
- 待办：§4.3 的 150 秒启动验证（确认数字 ID 生成 + `status` 接口在 Linux 头组合下返回 `code:0`）

### 方案 B：沿用 Windows 凭证 + Windows 头（现行已部署）

- `.temp/trae_checkin_server.js` 硬编码 `x-device-type: Windows` + Windows device_id/os_version
- 实际已稳定运行；缺点是"Windows 设备常年挂在华为云 IP"，风控视角不自洽，属踩线方案
- 若方案 A 验证受阻，可继续用 B 过渡，并保留 B 作为回退

### 风控要点（逆向实证）

1. token 与设备解耦（JWT 无 device claim），协议层换设备零障碍
2. 风险在风控信号层：**UUID 型 device_id 打接口 → 9074**（Windows 实测），数字 ID 必须
3. `req_source` 必须为 2，否则 9004
4. 服务端没强校验 `x-app-version`/`x-os-version`（1.107.1 混用也能过），但新脚本按真实值发送

---

## 六、下一步待办（按序）

1. **补验**（需在服务器执行，一条命令）：
   `timeout 150 xvfb-run -a /usr/bin/trae-cn --no-sandbox --disable-gpu --user-data-dir=/opt/trae-checkin/profile`，
   然后检查 `/opt/trae-checkin/profile/ahanet/tt_net_config.config` 是否出现数字 device_id
2. 编写 `trae_checkin_linux.js`：读 profile 下 `storage.json`（decryptTrae 现成）+ `ahanet/tt_net_config.config`，
   头组合按 §3.3，随机延迟复用现行脚本；先 `--status` 验证，再试 claim
3. 验证通过后：cron 切换到新脚本（旧脚本保留回退），更新 `05-服务器部署` 文档
4. 修订 `extract_trae_cred.js`：`app_version` 改读 `product.json` 的 `appVersion`（3.4.18）
5. token 到期（≈2026-11-25）前走既有 §05-日常维护 流程重提一次

---

## 七、经验沉淀

1. **官方直链不用逆向客户端也能拿**：下载页按钮 URL 是前端拼的，浏览器自动化点一下抓 network 即得
   `lf-cdn.trae.com.cn/obj/trae-com-cn/pkg/app/releases/stable/<tronBuildVersion>/linux/TRAE_CN-linux-x64.deb`
2. **Trae Linux 包无 app.asar**，`resources/app/out/main.js` 明文，逆向成本比 Windows 更低
3. **byteCrypto 是跨平台纯算法**：魔数头 + 密文内嵌 key + 双常量表 XOR + 双 SHA512，任何平台可解，
   这是 Trae 能"凭证外带"的根本原因（对比 TeleAgent/WorkBuddy/CodeArts 的 DPAPI 系）
4. **版本号有两套**：deb/package.json 的 `1.107.1` 是 VS Code 基线，对外真实版本是 product.json 的
   `appVersion`（3.4.18）+ `tronBuildVersion`（2.3.102387），发请求头一律用后者体系
5. **未登录的 aha 只有 UUID**：数字 device_id 是登录注册后的产物，做服务器原生身份必须让客户端
   带着 token 启动一次，不能凭空造
6. Windows 的 `ahanet/tt_net_config.config` 键值格式（`device_id&#*数字@$*`）在 Linux 侧预期一致，
   提取正则 `/device_id&#\*(\d+)@\$\*/` 可直接复用

> AI生成
