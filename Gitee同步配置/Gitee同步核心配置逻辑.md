# Gitee SSH 同步：核心配置逻辑与避坑红线

> 文档性质：**可复现、零思考、零踩坑**
> 适用环境：Windows + Trae IDE + Git + Gitee
> 版本：2026-08-07

---

## 一、配置逻辑总览（一张图讲清）

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Gitee SSH 同步配置链                         │
│                                                                     │
│  ① 生成密钥                                                         │
│  ssh-keygen -t ed25519 ──► ~/.ssh/id_ed25519 (.pub)                 │
│         │                                                           │
│         ▼                                                           │
│  ② 上传公钥                                                         │
│  Gitee → 设置 → SSH公钥 → 粘贴 id_ed25519.pub                       │
│         │                                                           │
│         ▼                                                           │
│  ③ 写 SSH config  ──► 编码=ANSI, Port=22                            │
│  ~/.ssh/config    ──► IdentityFile 指向私钥路径                     │
│         │                                                           │
│         ▼                                                           │
│  ④ 改远程 URL  ──► scp 格式: git@gitee.com:user/repo.git            │
│                   ──► 不能用 ssh:// 格式（端口会覆盖 config）         │
│         │                                                           │
│         ▼                                                           │
│  ⑤ 配 Git 身份  ──► 仓库级: git config user.name / user.email       │
│         │                                                           │
│         ▼                                                           │
│  ⑥ 验证          ──► ssh -T git@gitee.com → Hi user!                │
│                   ──► git push origin main → Everything up-to-date   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心配置（可直接复制）

### 2.1 SSH config 文件

**路径**：`C:\Users\Administrator\.ssh\config`

**内容**：
```
Host gitee.com
    HostName gitee.com
    User git
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

**编辑方式**：记事本 → 另存为 → 编码选 **ANSI**

### 2.2 远程 URL

```bash
git remote set-url origin git@gitee.com:jk528528/test.git
```

### 2.3 Git 身份

```bash
git config user.name "jk528528"
git config user.email "jk528528@gitee.com"
```

---

## 三、避坑红线（绝对不能做的事）

| # | 红线 | 后果 | 正确做法 |
|---|---|---|---|
| 1 | ❌ PowerShell `Out-File -Encoding UTF8` 写 config | BOM 导致 SSH 报 `\357\273\277host` | ✅ 记事本另存为 ANSI |
| 2 | ❌ SSH config 用 `Port 29418` | 连接超时 | ✅ `Port 22`（Gitee 已迁移） |
| 3 | ❌ URL 用 `ssh://git@gitee.com:29418/...` | URL 端口覆盖 config | ✅ scp 格式 `git@gitee.com:user/repo.git` |
| 4 | ❌ 私钥文件提交到 Git | 密钥泄露 | ✅ `.gitignore` 排除 `id_*` |
| 5 | ❌ 远程 URL 嵌密码 `https://user:pwd@...` | 密码明文暴露 | ✅ 用 SSH Key 认证 |
| 6 | ❌ Trae 直接修改 `~/.ssh/config` | Trae 白名单拒绝写入 | ✅ 手动用记事本编辑 |
| 7 | ❌ 忘记配 user.name/email | commit 报 `Author identity unknown` | ✅ 仓库级 config |

---

## 四、验证命令（6 步绿灯检查）

```bash
# === 第 1 步：SSH 认证 ===
ssh -T git@gitee.com
# ✅ 期望: Hi jk528(@jk528528)! You've successfully authenticated
# ❌ 失败: 检查公钥是否已上传 Gitee

# === 第 2 步：config 无 BOM ===
Format-Hex "$env:USERPROFILE\.ssh\config" | Select-Object -First 1
# ✅ 期望: 第一字节是 48 (字符 'H')
# ❌ 失败: 开头是 EF BB BF → 有 BOM，用记事本另存为 ANSI

# === 第 3 步：远程 URL ===
git remote -v
# ✅ 期望: origin 显示 git@gitee.com:jk528528/test.git
# ❌ 失败: 如果是 ssh://...:29418/... → 改回 scp 格式

# === 第 4 步：Git 身份 ===
git config user.name; git config user.email
# ✅ 期望: 输出用户名和邮箱
# ❌ 失败: 空值 → 执行第 2.3 节命令

# === 第 5 步：远程获取 ===
git fetch origin
# ✅ 期望: 无报错（PowerShell 可能误报 stderr，看 exit code）
# ❌ 失败: 报 Permission denied → 重查第 1 步

# === 第 6 步：远程推送 ===
git push origin main
# ✅ 期望: Everything up-to-date 或推送成功
# ❌ 失败: 报身份错误 → 第 4 步；报认证错误 → 第 1 步
```

---

## 五、从零复现 Checklist

按此顺序执行，不会出错：

```
□ 1. ssh-keygen -t ed25519 -C "user@gitee.com" -f ~/.ssh/id_ed25519 -N '""'
□ 2. Get-Content ~/.ssh/id_ed25519.pub → 复制全部内容
□ 3. Gitee → 设置 → SSH公钥 → 粘贴 → 添加
□ 4. 记事本新建 ~/.ssh/config → 写入第 2.1 节内容 → 另存为 ANSI
□ 5. git remote set-url origin git@gitee.com:USER/REPO.git
□ 6. git config user.name "USER"  /  git config user.email "USER@gitee.com"
□ 7. ssh -T git@gitee.com → 看到 Hi user!
□ 8. git push origin main → 成功
```

---

## 六、故障速查（现象 → 直接修复）

| 现象 | 直接修复 |
|---|---|
| `Bad configuration option: \357\273\277host` | 记事本打开 config → 另存为 ANSI |
| `Connection timed out port 29418` | config 改 `Port 22`；URL 改 scp 格式 |
| `Permission denied (publickey)` | 确认公钥已上传 Gitee；确认 config 中 IdentityFile 路径 |
| `Author identity unknown` | `git config user.name` + `git config user.email` |
| `fatal: not a git repository` | `cd` 到项目目录 |
| `remote contains work that you do not have` | `git pull origin main` 先拉取，再 push |

---

## 七、配置文件位置速查

| 文件 | 路径 | 可否用 Trae 修改 |
|---|---|---|
| 私钥 | `C:\Users\Administrator\.ssh\id_ed25519` | ❌ |
| 公钥 | `C:\Users\Administrator\.ssh\id_ed25519.pub` | ❌ |
| SSH config | `C:\Users\Administrator\.ssh\config` | ❌ 手动用记事本 |
| known_hosts | `C:\Users\Administrator\.ssh\known_hosts` | ❌ |
| Git 远程 URL | `../.git/config` | ✅ |
| Git 身份 | `../.git/config` | ✅ |
| .gitignore | `../.gitignore` | ✅ |
| 备用 config | [.git-ssh-config](./.git-ssh-config) | ✅ |

---

## 附：完整 SSH config 模板

```
Host gitee.com
    HostName gitee.com
    User git
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

| 字段 | 作用 | 必填 |
|---|---|---|
| Host | 别名，用于 URL 中 | ✅ |
| HostName | Gitee 服务器地址 | ✅ |
| User | 固定为 git | ✅ |
| Port | 22（Gitee 当前端口） | ✅ |
| IdentityFile | 私钥路径 | ✅ |
| IdentitiesOnly | 只用此密钥，跳过其他 | ❌ 建议 |
| StrictHostKeyChecking | 首次连接自动接受 | ❌ 建议 |
| ServerAliveInterval | 每 60 秒发送心跳 | ❌ 建议 |
| ServerAliveCountMax | 3 次心跳超时断开 | ❌ 建议 |

---

## 相关文档

| 文档 | 路径 | 说明 |
|---|---|---|
| 详细配置流程 | [Gitee同步与Trae配置逻辑.md](./Gitee同步与Trae配置逻辑.md) | 完整配置流程与原理 |
| 成功经验总结 | [Gitee同步成功经验.md](./Gitee同步成功经验.md) | 踩坑记录与核心经验 |
| 项目规则 | [../.trae/rules/project_rules.md](../.trae/rules/project_rules.md) | Trae AI 行为约束 |
