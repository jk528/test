# 第 2 步 · 本地解出 Trae 凭证

> 目标：从你自己电脑上的 Trae 客户端文件里，解出"签到许可证"（token）。
> 这步**只在本地做**，服务器还没沾手。
> **只在 token 失效时才重新做一次**，平时不用管。

---

## 前置条件

电脑上 **Trae 客户端已登录**（打开 Trae，右上角头像能看到账号就算）。

---

## 做法：跑现成脚本

打开一个**本地 PowerShell**（不是远程 SSH 那个），进入签到程序目录：

```powershell
cd "C:\Users\Administrator\Desktop\JK-temp\自动化与工具\签到程序"
```

然后执行：

```powershell
node ".temp\extract_trae_cred.js"
```

成功的话会看到类似输出：

```
OK token_len=1004 prefix=eyJhbGciOi...
device_id=1870736766****（真实值见 .temp/trae_cred.json）
region=CN
app_version=1.107.1
os_version=10.0.20348
output=C:\...\签到程序\.temp\trae_cred.json
```

**关键文件**：`.temp\trae_cred.json` 这个文件里装了 token、device_id 等全部签到所需信息。下一步要把它传到服务器。

> ⚠️ 这个文件**等同账号密码**，别发给别人，别提交到 git。用完之后可以删掉。

---

## 脚本原理（不用管，好奇的看看）

Trae 客户端把登录态存在 `%APPDATA%\Trae CN\User\globalStorage\storage.json` 里，用了一套纯 AES-128-CBC + SHA-512 的加密。脚本照抄了客户端自己的解密逻辑（逆向出来的），不碰 DPAPI，所以解出来的 token 能"外带"到别的机器用。

和它对比，另外 5 个平台（TeleAgent / WorkBuddy / CodeArts / Qoder / OfficeAce）的解密都强绑 Windows DPAPI，解出来也带不走，所以这次只迁 Trae。

---

## 如果脚本报错

| 报错信息 | 原因 | 怎么修 |
|---|---|---|
| `未检测到 Trae CN 数据目录` | Trae 没登录或装在旧名 `TRAE SOLO CN` | 打开 Trae 登录一次；不行就检查 `%APPDATA%` 下到底叫什么 |
| `未找到登录态数据 iCubeAuthInfo://icube.cloudide` | Trae 刚升级或重登过，storage.json 结构变了 | 重开 Trae 让它刷新登录态 |
| `登录态中没有 token` | storage.json 损坏 | Trae 退出重开；不行就卸载重装 |

遇到上面修不好的，去 [99-故障排查.md](99-故障排查.md) 第 1 节找更细的处理。
