# TraeWork 每日自动签到 —— 本地化与修复步骤总结

## 一、任务目标

对「TraeWork 每日自动签到」插件完成：

1. **本地化**：界面输出中文化、路径适配本机环境
2. **测试运行**：跑通签到全流程，确保积分能实际领取

## 二、环境确认

| 项目 | 值 |
| --- | --- |
| Node.js | v24.15.0（`C:\Program Files\nodejs\node.exe`） |
| 客户端 | TRAE SOLO CN v1.107.1 |
| 客户端路径 | `%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe` |
| 登录态文件 | `%APPDATA%\TRAE SOLO CN\User\globalStorage\storage.json` |
| 系统代码页 | GBK（936） |

## 三、本地化改动

### 1. checkin.js（核心脚本）

所有英文输出中文化：

| 原文 | 中文 |
| --- | --- |
| `ERROR: APPDATA environment variable not set` | `错误：未检测到 APPDATA 环境变量` |
| `ERROR: No auth data found` | `错误：未找到登录态数据` |
| `Already checked in today. Credits: X` | `今日已签到。积分：X` |
| `Check-in successful! Credits: X` | `签到成功！积分：X` |
| `Check-in failed: ...` | `签到失败：...` |
| `Fatal: ...` | `致命错误：...` |

### 2. run_checkin.cmd（批处理入口）

- 硬编码的原作者路径 `D:\1·AI agent\TRAE CN\...` 改为通用路径：
  ```cmd
  set "TRAE_EXE=%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe"
  ```
- **踩坑**：在批处理里写中文 `echo`，因系统是 GBK(936) 代码页、文件为 UTF-8 编码，cmd 解析时报错（`'RAE_EXE' is not recognized` 等乱码错误）。`chcp 65001` 也无法解决解析阶段问题。
- **结论**：批处理注释与报错保持纯 ASCII，中文输出统一由 JS 侧负责（Node 原生支持 UTF-8）。

## 四、问题定位：签到失败 9004

### 现象

- 登录态读取 ✅、AES-128-CBC 解密 ✅、status 接口 ✅（`checked_in:false, enable:true, credits:200`）
- claim 接口 ❌ 返回：
  ```json
  {"code":9004,"message":"The submitted order parameters are incorrect. Please try placing the order again"}
  ```

### 排查过程

1. 尝试空 body、`{credits:200}`、`X-Tenant-Id` 头、`Accept-Language` 头等多种组合，均 9004
2. 逆向官方客户端 `resources\app\out\main.js`，搜索 `checkin_credits`，定位到请求方法 `eb()`：

   ```js
   async eb(e, i, r) {
     // ...
     const o = this.cb(s.token);
     this.fb(o.headers);              // 注入设备头
     const a = Dr(this.P) ? 2 : 1;    // TraeWork=2，IDE=1
     const l = await this.Q.fetchWithHeaders({
       url: n, method: i,
       data: i === "POST" ? { req_source: a } : void 0,  // 请求体
       ...o
     });
   }
   ```

3. 发现脚本与官方请求的**两处关键差异**：
   - **请求体**：官方为 `{"req_source":2}`（2 = TraeWork/Solo Lite 桌面端），脚本发的是空对象 `{}`
   - **设备头**：`fb(e)` 方法会注入 `x-device-id`、`x-device-type`、`x-os-version`、`x-app-version`，脚本完全没有

### 设备 ID 来源确认

| 候选 | 来源 | 结果 |
| --- | --- | --- |
| `telemetry.devDeviceId`（UUID 格式） | storage.json | ❌ 返回 `9074 当前参与用户太多`（风控） |
| `device_id`（纯数字 `1963102595468793`） | `%APPDATA%\TRAE SOLO CN\ModularData\ckg_server\local_env.json` | ✅ 正确 |

## 五、修复内容（checkin.js）

1. 新增读取设备 ID：
   ```js
   const envPath = `${root}\\ModularData\\ckg_server\\local_env.json`;
   deviceId = String(JSON.parse(fs.readFileSync(envPath, 'utf8')).device_id || '');
   ```
2. 新增读取客户端版本号（`resources\app\package.json` 的 `version`）
3. 补齐设备请求头：`x-device-id` / `x-device-type: Windows` / `x-os-version` / `x-app-version`
4. 请求体由 `{}` 改为 `{ req_source: 2 }`（status 与 claim 接口一致）
5. claim 成功后再调一次 status 刷新积分（claim 响应体不含积分数）

## 六、验证结果

四种参数组合实测：

| 组合 | 结果 |
| --- | --- |
| `req_source=2`，无设备头 | ❌ 9004 |
| `req_source=2` + UUID 设备头 | ❌ 9074（风控） |
| `req_source=2` + 数字设备头 | ✅ `code:0 success` |
| `req_source=1` + 数字设备头 | ✅ `code:0 success`（对照） |

今日签到**实际领取成功**，状态复查：

```json
{"checked_in":true,"code":0,"credits":200,"did_checked_in":true,"enable":true,"message":"success"}
```

两个入口最终输出：

```
> node checkin.js        →  今日已签到。积分：200
> .\run_checkin.cmd      →  今日已签到。积分：200
```

## 七、关键经验

1. **接口风控参数缺一不可**：TraeWork 签到接口要求请求体带 `req_source=2`，且请求头必须带与客户端一致的 `x-device-id`，否则返回 9004。
2. **设备 ID 要用 aha 数字 ID**：不能用 VS Code 体系的 UUID（`telemetry.devDeviceId`），会触发风控 9074；正确来源是 `ModularData\ckg_server\local_env.json` 的 `device_id`。
3. **Windows 批处理避免非 ASCII 字符**：GBK 代码页下 UTF-8 中文 `echo` 会导致 cmd 解析崩溃，中文输出应放在 JS/程序层。
4. **逆向客户端是最可靠的接口对照方式**：直接在 `out\main.js` 中搜索接口路径即可定位官方请求的完整参数构造逻辑。

## 八、Windows 任务计划自动触发配置（每天 00:10）

### 配置方式

以管理员身份打开 PowerShell 执行（任务名「每日签到」）：

```powershell
$dir = "c:\Users\Administrator\Downloads\TraeWork每日自动签到"   # 脚本实际目录
$arg = '/s /c ""' + $dir + '\run_checkin.cmd" >> "' + $dir + '\checkin.log" 2>&1"'
$action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arg
$trigger  = New-ScheduledTaskTrigger -Daily -At "00:10"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName "每日签到" -Action $action -Trigger $trigger -Settings $settings -Force
```

### 配置要点与踩坑

1. **用 PowerShell `Register-ScheduledTask` 而非 `schtasks`**：原生 Unicode 支持，中文任务名「每日签到」在 GBK(936) 代码页下无乱码风险。
2. **`cmd /c` 含 `>>`、`&` 时必须加 `/s` 参数**：不加 `/s` 时引号不会被自动剥除，导致重定向被当作命令解析、日志文件无法生成（退出码仍为 0，具有迷惑性）。标准写法：
   ```
   /s /c ""脚本绝对路径" >> "日志绝对路径" 2>&1"
   ```
3. **日志与脚本路径都用绝对路径**：计划任务默认工作目录是 `C:\Windows\System32`，相对路径会导致日志落错位置。
4. **`-StartWhenAvailable`**：00:10 电脑关机时，开机后自动补跑；`-ExecutionTimeLimit 10分钟` 防止任务挂死。
5. 每日运行结果追加写入脚本目录的 `checkin.log`（UTF-8）。

### 常用管理命令

```powershell
# 查看任务状态与下次运行时间
Get-ScheduledTask -TaskName "每日签到"
Get-ScheduledTaskInfo -TaskName "每日签到"

# 手动触发测试
Start-ScheduledTask -TaskName "每日签到"

# 删除任务
Unregister-ScheduledTask -TaskName "每日签到" -Confirm:$false
```

### 实测验证结果（2026-09-07）

| 检查项 | 结果 |
| --- | --- |
| 任务名称 | 每日签到 |
| 任务状态 | Ready（已就绪） |
| 触发器 | 每天 00:10（本机时区 UTC+8） |
| 执行命令 | `cmd.exe /s /c ""...\run_checkin.cmd" >> "...\checkin.log" 2>&1"` |
| 手动触发结果码 | 0（成功） |
| checkin.log 写入 | ✅ `今日已签到。积分：200` |
| 下次自动运行 | 2026-09-08 00:10:00 |

**结论：自动签到已配置成功，次日起每天 00:10 自动执行，无需人工干预。**

## 九、2026-10-15 路径迁移修复（客户端更名 Trae CN）

### 问题现象

`checkin.log` 持续报错：
```
ERROR: TRAE SOLO CN.exe not found at: B:\trae work\TRAE SOLO CN\TRAE SOLO CN.exe
错误：未找到登录态数据
```

### 根因

客户端从 **TRAE SOLO CN** 更名为 **Trae CN**，导致两处硬编码路径全部失效：

| 项 | 旧值（失效） | 新值（实际） |
| --- | --- | --- |
| 客户端 EXE | `B:\trae work\TRAE SOLO CN\TRAE SOLO CN.exe` | `B:\Trae CN\Trae CN.exe` |
| 登录态目录 | `%APPDATA%\TRAE SOLO CN` | `%APPDATA%\Trae CN` |

### 修复策略

核心思路：**消除硬编码，全部改为自动探测**，避免客户端再次更名/迁移时复发。

#### 1. `run_checkin.cmd`：改用系统 Node + 注册表兜底

不再依赖固定的 `TRAE_EXE` 路径，运行时选择优先级：
1. `node`（PATH）—— 本机 Node v24.19.0，原生支持 `fetch`
2. `C:\Program Files\nodejs\node.exe`
3. 注册表 `HKCU\...\Uninstall` 探测 Trae CN 安装目录，用其 EXE 作 Node 运行时（`ELECTRON_RUN_AS_NODE=1`），同时兼容 `Trae CN.exe` 与旧名 `TRAE SOLO CN.exe`

#### 2. `checkin.js`：自动探测数据目录与版本

- `findAppDataRoot()`：遍历 `%APPDATA%` 下 `Trae CN`、`TRAE SOLO CN`，选择含 `storage.json` 的目录
- `findAppVersion()`：优先从注册表读取 `InstallLocation`，拼接 `resources\app\package.json`，再回退常见路径
- 所有输出加时间戳前缀，便于日志排查

### 验证结果

```
> node checkin.js
[2026/10/15 08:32:12] 检测到数据目录：C:\Users\代\AppData\Roaming\Trae CN
[2026/10/15 08:32:13] 今日已签到。积分：100

> run_checkin.cmd   →  同上

计划任务手动触发：LastTaskResult = 0，checkin.log 正常写入
下次自动运行：2026-10-16 00:10
```

### 经验

- **客户端更名/迁移是高频事件**，签到脚本不应硬编码任何客户端路径
- **系统 Node 是更稳定的运行时**，比耦合到客户端 EXE 更可靠（Node 18+ 已内置 `fetch`）
- 登录态目录名也可能随客户端更名变化，必须自动探测而非写死

## 十、2026-10-26 设备 ID 位置迁移修复（客户端内部结构变更）

### 问题现象

`checkin.log` 自 2026-10-24 起持续出现：

```
[2026/10/26 08:27:17] 警告：未找到设备 ID，签到可能被服务端拒绝
[2026/10/26 08:27:18] 签到失败：The submitted order parameters are incorrect. Please try placing the order again
```

「Trae每日签到」文件夹注册的计划任务同样失败（两脚本共用同一读取逻辑）。

### 根因

客户端更新后，`%APPDATA%\Trae CN\ModularData\ckg_server\` 目录整体消失（进程仍在，见 `ModularData\pids\*.ckg.pid`），旧读取路径 `local_env.json` 失效。设备 ID 迁移到了 ttnet 网络组件的配置文件中。

| 项 | 旧位置（已失效） | 新位置（实测） |
| --- | --- | --- |
| 设备 ID | `ModularData\ckg_server\local_env.json`（JSON 的 `device_id` 字段） | `ModularData\ttnet\tt_net_config.config`、`ahanet\tt_net_config.config` |

新位置为 ttnet 自定义键值格式，非 JSON：

```
device_id&#*2144514107022570@$*tnc_abtest&#*15168109@$*tnc_etag&#*...
```

提取正则：`/device_id&#\*(\d+)@\$\*/`

### 修复内容

两个脚本（`checkin.js`、`Trae每日签到\scripts\trae_checkin.js`）同步新增 `findDeviceId(root)`，多候选优先级：

1. `ModularData\ckg_server\local_env.json`（旧路径，兜底兼容）
2. `ModularData\ttnet\tt_net_config.config`（新路径，正则提取）
3. `ahanet\tt_net_config.config`（新路径冗余副本）

### 验证结果

```
> node checkin.js
[2026/10/26 08:42:16] 检测到数据目录：C:\Users\代\AppData\Roaming\Trae CN
[2026/10/26 08:42:16] 签到成功！积分：100
```

### 经验

- **客户端内部数据文件同样是易变点**：不仅外层目录会更名，`ModularData` 下的子模块（ckg_server → ttnet）也会随版本重构，设备标识读取必须做多候选探测
- ttnet 配置为 `key&#*value@$*` 链式格式，解析时注意转义正则中的 `&`、`#`、`@`、`$`、`*` 字符

## 十一、2026-10-28 设备 ID 再次迁移修复（ahanet 目录）

### 问题现象

2026-10-28 凌晨 `checkin_ai.log`：

```
[2026-10-28 00:09:51] 检测到数据目录：C:\Users\Administrator\AppData\Roaming\Trae CN
[2026-10-28 00:09:51] 警告：未找到设备 ID，签到可能被拒绝
[2026-10-28 00:09:52] 签到失败：The submitted order parameters are incorrect...
```

### 根因

客户端更新后目录结构再次变化：`ModularData\ttnet\` 被移除，`ModularData` 下仅剩 `ai-agent`；设备 ID 改由 aha 网络组件写在**数据根目录**的 `ahanet\tt_net_config.config`（不是 `ModularData` 下）。

| 项 | 旧位置（已失效） | 新位置（实测） |
| --- | --- | --- |
| 设备 ID | `ModularData\ttnet\tt_net_config.config` | `%APPDATA%\Trae CN\ahanet\tt_net_config.config` |

另外发现：`ahanet\server.json` 里出现的 `device_id` 只是请求头白名单，不是值；`aha\TinyStorage` 的 `aha.device.device_id` 是加密串，均不可用。

### 修复内容

`checkin_all.js` 与 `分享文件夹\Trae每日签到\scripts\trae_checkin.js` 同步新增 `findTraeDeviceId(root)`：

1. `ModularData\ckg_server\local_env.json`（最早的 JSON 位置，兜底）
2. `ModularData\ttnet\tt_net_config.config`（2026-10-26 位置，兜底）
3. `ahanet\tt_net_config.config`、`ModularData\ahanet\tt_net_config.config`（当前位置）
4. **兜底扫描**：限深 3 层递归查找 `tt_net_config*.config`，跳过缓存/日志/工作区等大目录，客户端下次搬位置仍可自动找到

### 验证结果

```
> trae_checkin.js --status --no-delay  →  当前积分：100（含额外 100）　今日已签：否
> trae_checkin.js --no-delay           →  签到成功！积分：100（含额外 100）
> checkin_all.js --group=ai --no-delay →  [OK] Trae（今日已签到。积分：100）
```

### 经验

- 设备 ID 的存放位置已迁移两次（`ckg_server` → `ModularData\ttnet` → 根目录 `ahanet`），纯路径探测始终滞后于客户端更新
- 因此必须保留**目录扫描兜底**：只要文件仍叫 `tt_net_config*.config`，位置怎么变都能命中
- 判断候选文件要看值而非名字：`server.json` 的 `device_id` 是字段名列表，不能误用
