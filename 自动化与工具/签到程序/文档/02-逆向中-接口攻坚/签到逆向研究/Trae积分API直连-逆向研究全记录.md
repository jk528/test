# Trae 积分签到 API 直连 —— 逆向研究全记录（合并版）

> 合并日期：2026-10-25　|　合并自《TraeWork积分API直连-逆向研究全记录》《TraeCN积分API直连-逆向研究全记录》
> 研究日期：2026-09-18　|　结论：**已成功**，已集成 `scripts/checkin_all.js`
> 关键背景：TraeWork（TRAE SOLO CN）与 Trae CN 原是两个客户端，**签到 API 完全一致**；2026-10-16 两客户端合并为同一客户端/同一账号，签到入口随之合并为单平台「Trae」

---

## 一、接口与鉴权（两客户端通用）

| 项目 | 值 |
|---|---|
| 签到接口 | `https://api.trae.cn/trae/api/v2/ug/checkin_credits/claim`（POST） |
| 状态查询 | 同路径 `/status`（POST） |
| 鉴权头 | `Authorization: Cloud-IDE-JWT <token>` |
| 必要请求头 | `x-device-id`、`x-device-type: Windows`、`x-app-version` |
| 请求体 | `{"req_source": 2}` |

## 二、登录态提取链路（核心技术点）

1. **存储位置**：`%APPDATA%\Trae CN\User\globalStorage\storage.json`（新名优先，旧名 TRAE SOLO CN 兜底）的 `iCubeAuthInfo://icube.cloudide` 字段
2. **加密方式**：AES-128-CBC + SHA-512 派生
   - 密文 Base64 解码后：前 6 字节跳过 → 取 32 字节作为派生输入
   - 派生：SHA512(key) 与固定异或表（ure⊕dre，见 checkin_all.js 源码常量）拼接后再 SHA512
   - 结果前 16 字节为 AES key，16~32 字节为 IV
   - 解密后明文前 64 字节为随机填充，剥除后得 JSON（含 token、userRegion）
3. **设备 ID**：`ModularData\ckg_server\local_env.json` 的 `device_id`（缺失时签到可能被拒）
4. **版本号**：注册表 `HKCU\...\Uninstall` 搜 "Trae" 取 InstallLocation → `resources\app\package.json`

## 三、演进史（冗余信息的来龙去脉）

| 时间 | 状态 |
|---|---|
| 2026-09-18 | 两客户端各自逆向完成，各自独立脚本（traework_checkin.js / traecn_checkin.js）+ 独立定时任务 |
| 后续 | 并入 checkin_all.js 统一脚本，两个入口 |
| 2026-10-16 | 官方客户端合并 → 脚本合并为单平台 Trae，数据目录候选双名兼容 |
| 2026-10-19 | 增补 1024 签到抽奖（活动已结束，代码 10-25 剔除，记录见《Trae1024签到抽奖逆向记录》） |

## 四、详细技术参考

- 通用 Electron 逆向方法：《Electron应用API逆向通用指南.md》（同目录）
- 与 TeleAgent 的实现差异：《TeleAgent与Trae签到实现对比.md》（同目录）
- 汇总视角：《../签到逆向研究总集.md》
- 生效代码：`scripts/checkin_all.js` 的 `checkinTrae()` 及公共工具区（DPAPI/AES-GCM/AES-CBC 全实现）
