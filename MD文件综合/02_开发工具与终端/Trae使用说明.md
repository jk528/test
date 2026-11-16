# Trae 使用说明总结

> 本文档基于 Trae 官方文档与社区实践整理，涵盖本地与云端的核心区别、Git 同步配置、数据保存策略等关键内容。

---

## 目录

- [一、总纲：本地 vs 云端](#一总纲本地-vs-云端)
- [二、云端环境详解](#二云端环境详解)
- [三、Git 同步配置](#三git-同步配置)
- [四、数据保存策略](#四数据保存策略)
- [五、打包与构建能力](#五打包与构建能力)
- [六、工作流建议](#六工作流建议)

---

## 一、总纲：本地 vs 云端

### 1.1 核心区别对照表

| 维度 | 本地模式 | 云端模式 |
|------|---------|---------|
| **文件存储** | 直接写入指定本地目录 | 存放在云端沙箱容器，会话关闭后清理 |
| **文件持久化** | 永久保存在本地硬盘 | 仅会话存续期间保存，删除会话永久删除 |
| **环境配置** | 需本地安装依赖 | 预装绝大多数语言环境，开箱即用 |
| **访问方式** | 仅限安装 Trae 的电脑 | 网页版/桌面版/移动端三端联动 |
| **本地系统访问** | 可访问宿主机文件系统 | 沙箱隔离，无法访问本地文件系统 |
| **资源限制** | 受本地设备性能限制 | 云端算力，具体规格未公开 |
| **Git 支持** | 完整支持所有 Git 操作 | 仅 GitHub 官方集成，Gitee 需手动配置 |

### 1.2 三端联动架构

```
📱 TRAE 移动端（任务下发中心）
    │
    ├── 下发云端任务 → ☁️ 云端沙箱（智能体自动执行）
    ├── 下发本地任务 → 💻 桌面版（公司电脑）
    └── 下发本地任务 → 💻 桌面版（家庭电脑）

三端共享同一账号体系，任务信息实时全量同步。
```

### 1.3 三种模式

| 模式 | 适用人群 | 核心场景 |
|------|---------|---------|
| **Work 模式** | 产品经理、数据分析师、运营 | 文档、数据、演示稿处理 |
| **Code 模式** | 开发工程师 | 编码、调试、代码库管理、Git 工作流 |
| **Design 模式** | 设计人员 | 设计、修改、定稿交付全流程 |

---

## 二、云端环境详解

### 2.1 预装语言与版本

Trae 官方维护 all-in-one 通用容器镜像，预装以下语言：

| 语言 | 支持版本 |
|------|---------|
| Python | 3.10、3.11、3.12、3.13、3.14 |
| Node.js | 18、20、22、24 |
| Go | 1.22.12 ~ 1.25.1 |
| Rust | 1.83.0 ~ 1.92.0 |
| Java | 11、17、21、22、23、24、25 |
| Ruby | 3.2.3 ~ 3.4.4 |
| PHP | 8.2 ~ 8.5 |
| Swift | 5.10、6.1、6.2 |

### 2.2 可自定义配置项

| 配置项 | 说明 | 限制 |
|--------|------|------|
| 预装依赖 | 指定语言版本，默认最新版 | 仅支持官方列表内版本 |
| 环境变量 | 明文 JSON 存储 | 最多 100 个 |
| 敏感变量 | KMS 加密存储，仅运行时使用 | 最多 50 个 |
| 安装脚本 | 环境启动时自动执行（阻塞） | 长度 ≤ 10KB |
| 启动脚本 | 依赖安装完成后执行（后台） | 长度 ≤ 10KB |
| 默认命令行 | 并行打开的后台终端 | 最多 10 个 |

### 2.3 网络策略

云端沙箱网络访问受白名单限制，且**不支持用户自定义**：

**允许访问的依赖源：**
`npm`、`pypi`、`maven`、`goproxy`、`rubygems`、`packagist`、`crates`、`docker`、`github`、`gitlab`

> ⚠️ **注意**：`gitee.com` 不在白名单中，云端可能无法访问 Gitee。

### 2.4 沙箱文件访问权限

| 权限类型 | 目录类型 | 权限范围 |
|----------|---------|---------|
| 读写 | 当前会话工作目录 | 仅当前项目或会话内创建的文件 |
| 读写 | 沙箱临时与缓存目录 | 仅当前会话运行所需 |
| 不可访问 | 宿主机文件系统 | 无法访问用户本地设备 |
| 不可访问 | 其他会话数据目录 | 会话间完全隔离 |

---

## 三、Git 同步配置

### 3.1 GitHub：官方集成（推荐）

#### 集成步骤

1. 点击 **头像** → **设置** → **外部应用授权**
2. 在 **GitHub** 应用处点击 **连接**
3. 登录 GitHub 账号，授权 **TRAE-AI CN** 访问仓库
4. 授权完成后，集成方显示 **Web** 和 **Desktop**

#### 支持功能

- 一键发布项目到 GitHub
- AI 创建 PR、检查 PR
- 克隆 GitHub 仓库到云端
- 源代码管理（提交、分支、标签、远程仓库）

### 3.2 Gitee：手动配置

> ⚠️ **风险提示**：Gitee 不在云端网络白名单中，可能无法访问。建议先测试 `curl -I https://gitee.com`。

#### 方案 A：Personal Access Token

**步骤 1：Gitee 生成 Token**
- 登录 Gitee → 头像 → **设置** → **私人令牌**
- 勾选 `projects` 权限
- 复制 Token（只显示一次）

**步骤 2：配置敏感变量**

在 **头像 → 设置 → 云端运行环境** 中添加：

| Key | Value |
|-----|-------|
| `GITEE_TOKEN` | Gitee 私人令牌 |
| `GITEE_USERNAME` | Gitee 用户名 |

**步骤 3：安装脚本配置 Git 凭据**

```bash
#!/bin/bash
git config --global user.name "你的Gitee用户名"
git config --global user.email "你的邮箱"
git config --global credential.helper "!f() { echo username=$GITEE_USERNAME; echo password=$GITEE_TOKEN; }; f"
```

**步骤 4：添加远程仓库并推送**

```bash
cd /workspace/你的项目
git init
git remote add gitee https://gitee.com/用户名/仓库.git
git add .
git commit -m "init"
git push -u gitee master
```

#### 方案 B：SSH Key

**步骤 1：生成 SSH Key**

```bash
ssh-keygen -t ed25519 -C "你的邮箱" -f ~/.ssh/id_ed25519 -N ""
```

**步骤 2：获取公钥并添加到 Gitee**

```bash
cat ~/.ssh/id_ed25519.pub
```

粘贴到 Gitee → 设置 → SSH 公钥。

**步骤 3：安装脚本配置 SSH**

```bash
#!/bin/bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keyscan gitee.com >> ~/.ssh/known_hosts 2>/dev/null
cat > ~/.ssh/config << 'EOF'
Host gitee.com
    HostName gitee.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
EOF
chmod 600 ~/.ssh/config
```

**步骤 4：使用 SSH 地址推送**

```bash
git remote add gitee git@gitee.com:用户名/仓库.git
git push -u gitee master
```

### 3.3 双仓库同步（Gitee + GitHub）

```bash
# 添加两个远程仓库
git remote add github https://github.com/用户名/仓库.git
git remote add gitee https://gitee.com/用户名/仓库.git

# 分别推送
git push github master
git push gitee master
```

**一键推送脚本 `push-all.sh`：**

```bash
#!/bin/bash
git push github "$@"
git push gitee "$@"
```

---

## 四、数据保存策略

### 4.1 数据保存时长

| 场景 | 保存时长 |
|------|---------|
| 会话存续期间 | 代码数据、对话内容、上下文一直保存 |
| 主动删除会话 | 相关数据永久删除，不再保留 |
| 会话关闭/超时 | `/workspace` 工作目录被清理 |
| 长时间挂起任务 | 超过 24 小时，恢复时缓存失效，执行失败 |
| 移动端与电脑配对 | 有效期 180 天 |

### 4.2 数据类型与保存位置

| 数据类型 | 保存位置 | 跨设备同步 |
|----------|---------|-----------|
| 对话内容 | 云端 | ✅ 支持 |
| AI 生成产物（文档、代码变更） | 云端 | ✅ 支持 |
| 工作目录文件 | 云端沙箱（临时） | ❌ 会话关闭后清理 |
| 本地项目文件 | 本地硬盘 | ❌ 仅本机 |

### 4.3 数据安全提示

- 云端代码数据仅用于维持产品功能，**不会用于模型训练**
- 敏感信息务必使用**敏感变量**存储（KMS 加密）
- 重要产物及时下载到本地或 push 到 Git 仓库

---

## 五、打包与构建能力

### 5.1 支持的打包类型

| 类型 | 支持情况 | 说明 |
|------|---------|------|
| Web 应用 | ✅ | `npm run build` 等，可云端预览 |
| Rust 二进制 | ✅ | 可内嵌资源，产出单一可执行文件 |
| Android APK | ✅ | 需配置 SDK，常用 GitHub Actions 流水线 |
| Docker 镜像 | ✅ | 支持 `docker build`、`docker compose` |
| Python 包 | ✅ | 支持 `pyinstaller`、`setuptools` 等 |

### 5.2 打包注意事项

1. **产物及时保存**：会话关闭后工作目录清理，打包产物需下载或 push 到 Git
2. **资源限制**：大型项目编译可能受云端资源限制
3. **环境配置**：Android 等需特定 SDK 的，通过安装脚本配置
4. **依赖安装**：通过安装脚本（`install`）预装依赖

### 5.3 社区实践案例

- **Rust 全栈项目**：Web UI 通过 `rust-embed` 内嵌进二进制，产出无外部依赖的单一可执行文件
- **Android App**：AI 生成 GitHub Actions 脚本，push 后自动触发云端流水线打包 APK
- **Docker 部署**：通过 `docker compose` 一键部署到云服务器

---

## 六、工作流建议

### 6.1 场景一：需要稳定自动化同步（推荐本地方案）

**适用场景**：需要定时同步到 Gitee、文件需长期持久化

```
本地运行 Trae → 文件写入本地目录 → 任务计划程序同步到 Gitee → Gitee 同步到 GitHub
```

**优点**：文件完全可控，自动化可靠，不受云端网络限制

### 6.2 场景二：随时随地轻量开发（推荐云端方案）

**适用场景**：临时任务、快速验证、外出办公

```
网页版/移动端下发任务 → 云端沙箱执行 → push 到 GitHub → Gitee 镜像同步
```

**优点**：无需本地环境，有网就能用

**缺点**：文件不持久，Gitee 可能无法直接访问

### 6.3 场景三：混合方案（兼顾灵活与稳定）

```
日常编辑：云端（随时随地）
    ↓
最终同步：本地模式（可访问 Gitee）
    ↓
定时备份：任务计划程序 → Gitee → GitHub
```

### 6.4 Gitee 无法访问时的替代方案

| 方案 | 说明 |
|------|------|
| **Gitee 镜像同步** | 云端只 push 到 GitHub，Gitee 端开启从 GitHub 导入/同步 |
| **本地中转** | 云端 push GitHub → 本地 pull → push Gitee |
| **纯本地** | 放弃云端 Git，全部本地操作 |

---

## 附录：关键链接

| 文档 | 链接 |
|------|------|
| Trae Work 概述 | https://docs.trae.cn/work_what-is-trae-solo |
| 云端运行环境配置 | https://docs.trae.cn/work_set-up-the-remote-environment |
| GitHub 集成 | https://docs.trae.cn/work_github-integration |
| 沙箱说明 | https://docs.trae.cn/work_sandbox |
| 云端数据存储声明 | https://docs.trae.cn/work_data-storage-policy-for-remote-agents |
| 源代码管理 | https://docs.trae.cn/ide/source-control |

---

> **文档版本**：v1.0
> **更新日期**：2026-11-10
> **整理依据**：Trae 官方文档 + 社区实践
