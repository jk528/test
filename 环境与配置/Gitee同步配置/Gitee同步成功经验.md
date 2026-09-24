# Gitee 同步 + Trae 配置：成功经验总结

> 日期：2026-08-07
> 环境：Windows 11 + Trae IDE + Git 2.54.0 + Gitee

---

## 🎯 一句话结论

Gitee SSH 同步在 Trae 中完全可行，核心是 **SSH config 用 ANSI 编码 + scp 格式 URL + 仓库级 user config**。

---

## 🏁 最终可用配置

### SSH config（`C:\Users\Administrator\.ssh\config`）

```
Host gitee.com
    HostName gitee.com
    User git
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

> ⚠️ **编码必须是 ANSI**（记事本另存为），UTF-8 BOM 会导致 SSH 解析失败

### Git 远程 URL

```
origin  git@gitee.com:jk528528/test.git  (scp 格式，让 SSH config 生效)
```

> ⚠️ **不能用** `ssh://git@gitee.com:29418/...`（URL 中端口会覆盖 config）

### Git 用户配置（仓库级）

```bash
git config user.name "jk528528"
git config user.email "jk528528@gitee.com"
```

---

## 🔑 踩过的 5 个坑

### 坑 1：PowerShell 5 写文件自带 BOM

**现象**：`ssh -T git@gitee.com` 报 `Bad configuration option: \357\273\277host`

**原因**：PowerShell 5 的 `Out-File -Encoding UTF8` 会在文件头写入 3 字节 BOM（EF BB BF），SSH 无法识别

**解决**：记事本打开 config → 文件 → 另存为 → 编码选 **ANSI**

### 坑 2：Gitee SSH 端口用了废弃的 29418

**现象**：`Connection timed out port 29418`

**原因**：旧版 Gitee 文档用 29418 端口，现已迁移到默认 22

**解决**：config 中 `Port 22`，同时删除 URL 中的端口号

### 坑 3：URL 格式覆盖 SSH config

**现象**：config 设了 Port 22，但 `git fetch` 仍尝试 29418

**原因**：`ssh://git@gitee.com:29418/...` 格式中 URL 的端口号优先级高于 config

**解决**：改用 scp 格式 `git@gitee.com:jk528528/test.git`，让 SSH config 完全生效

### 坑 4：Trae 无法直接修改系统文件

**现象**：Trae 拒绝写入 `C:\Users\Administrator\.ssh\config`

**原因**：Trae 出于安全考虑，对非项目目录的文件操作有白名单限制

**解决**：
- SSH config **手动用记事本**编辑
- 项目内备用：在项目根放 `.git-ssh-config`，测试时用 `$env:GIT_SSH_COMMAND` 指向

### 坑 5：Git 未配置 user.name/email

**现象**：`git commit` 报 `Author identity unknown`

**原因**：新环境默认没有 Git 提交身份信息

**解决**（仓库级，不污染全局）：
```bash
git config user.name "jk528528"
git config user.email "jk528528@gitee.com"
```

---

## ✅ 验证通过的命令

```bash
# 1. SSH 认证
ssh -T git@gitee.com
# 输出: Hi jk528(@jk528528)! You've successfully authenticated

# 2. 远程获取
git fetch origin

# 3. 远程推送
git push origin main
# 输出: Everything up-to-date

# 4. 身份配置
git config user.name    # jk528528
git config user.email   # jk528528@gitee.com

# 5. 提交测试
git commit --allow-empty -m "测试提交"
# 输出: [main xxxxxxx] 测试提交
```

---

## 🧠 核心经验总结

| 经验点 | 要点 |
|---|---|
| **编码为王** | Windows 下配置文件尽量用 ANSI，避免 BOM |
| **端口要新** | Gitee SSH 已迁移到 22，抛弃旧文档的 29418 |
| **URL 格式** | scp 格式让 config 生效，URL 格式会覆盖 config |
| **身份隔离** | 仓库级 config 比全局更安全，适合多账号 |
| **Trae 限制** | 系统级文件手动操作，项目内用备用方案绕过 |
| **BOM 检测** | `Format-Hex config` 可快速判断是否有 BOM |

---

## 📋 快速恢复 Checklist

如果 Gitee 同步挂了，按此顺序排查：

1. ✅ `ssh -T git@gitee.com` → 认证成功？
2. ✅ `git remote -v` → URL 是 scp 格式？
3. ✅ `Get-Content ~/.ssh/config` → 有 BOM？Port 是 22？
4. ✅ `git config user.name` / `user.email` → 已配置？
5. ✅ `git fetch origin` → 能拉取？
6. ✅ `git push origin main` → 能推送？

---

## 📁 相关文件

| 文件 | 路径 | 用途 |
|---|---|---|
| 详细配置文档 | [Gitee同步与Trae配置逻辑.md](./Gitee同步与Trae配置逻辑.md) | 完整配置流程 |
| SSH 私钥 | `C:\Users\Administrator\.ssh\id_ed25519` | 认证密钥（保密） |
| SSH 公钥 | `C:\Users\Administrator\.ssh\id_ed25519.pub` | 上传 Gitee |
| SSH config | `C:\Users\Administrator\.ssh\config` | SSH 主机配置 |
| Git 配置 | `../.git/config` | 远程 URL、仓库级身份 |
| .gitignore | `../.gitignore` | 忽略规则 |
| 备用 SSH config | [.git-ssh-config](./.git-ssh-config) | Trae 内测试用 |
| 核心配置逻辑 | [Gitee同步核心配置逻辑.md](./Gitee同步核心配置逻辑.md) | 可复现零踩坑版 |
| 项目规则文件 | [../.trae/rules/project_rules.md](../.trae/rules/project_rules.md) | Trae AI 行为约束 |

---

**文档结束** | 详细配置：[Gitee同步与Trae配置逻辑.md](./Gitee同步与Trae配置逻辑.md) | 核心逻辑：[Gitee同步核心配置逻辑.md](./Gitee同步核心配置逻辑.md) | 项目规则：[../.trae/rules/project_rules.md](../.trae/rules/project_rules.md)
