# Git 忽略配置说明

> 用途：说明本仓库（`C:\Users\Administrator\Desktop\JK-temp` → `git@gitee.com:jk528528/test.git`）的忽略规则体系、当前生效规则、验证与维护方法。
> 关联文档：[Git同步与仓库清理记录.md](Git同步与仓库清理记录.md)

## 一、忽略规则的作用范围（四级）

| 层级 | 位置 | 作用范围 | 是否随仓库同步 | 本仓库是否使用 |
|---|---|---|---|---|
| 仓库级 | 仓库根目录 `.gitignore` | 该仓库内**所有子目录** | ✅ 提交后全端生效 | ✅ **当前唯一使用** |
| 子目录级 | 某子目录内 `.gitignore` | 仅该子目录及以下 | ✅ 同步 | ❌（子目录里的 .gitignore 是各子项目自带，与本仓库忽略体系无关） |
| 本机级 | `.git/info/exclude` | 仅本机该仓库 | ❌ 不同步 | ❌（默认模板，未启用） |
| 全局级 | `core.excludesFile` 指向的文件 | 本机**所有**仓库 | ❌ 不同步 | ❌ 未配置（2026-10-22 检查为空） |

**结论：本仓库所有忽略规则集中在根目录 `.gitignore`，例如 `*.pdf` 对仓库内任意层级的 PDF 都生效，但不影响本机其他 Git 仓库。**

## 二、当前生效规则清单（按类别）

### 1. 大文件（防仓库膨胀，重点维护区）

| 规则 | 加入时间 | 原因 |
|---|---|---|
| `*.pdf` | 2026-10-21 | PDF 文档/电子书体积大且可从源站重新下载；本地保留但不入版本库。曾致 Gitee 仓库 1294MB 超 1024MB 配额、push 全被拒，已做历史重写清理 |
| `Git-2.56.0.2-64-bit.exe` | 2026-10-18 | 63.7MB 安装包，曾进历史后被清理 |
| `语料与文本/小说/`、`语料与文本/去重备份/`、`小说/` | 2026-10-18 | 小说原文/备份，体积大 |
| `彩读分析/.temp/` | 2026-10-18 | 临时目录 |
| `*.ecdl` | 2026-10-18 | 大体积数据文件 |

### 2. 依赖与构建产物

`__pycache__/`、`*.pyc`、`*.pyo`、`.venv/`、`venv/`、`env/`、`node_modules/`、`dist/`、`*.local`、`**/src-tauri/target/`、`target/`

### 3. 内嵌独立仓库

`阅读器项目/彩读分析/.temp/ColorTxt/`（自身是 GitHub 仓库，不作为 gitlink 纳入）

### 4. 密钥与本地配置（严禁提交）

`.env`、`.env.*`（`!.env.example` 除外）、`secrets.vault`、`*.key`

### 5. 系统 / 编辑器

`Thumbs.db`、`ehthumbs.db`、`Desktop.ini`、`.DS_Store`、`.idea/`、`.vscode/*`（保留 `extensions.json` 与 `settings.json`）、`*.swp`、`*~`

### 6. 小说拆分产物

`**/*_自动/`、`**/拆分文档/`、`保留大于等于*_*.txt`、`清理小于*_*.txt`

### 7. 云盘同步 / 临时 / 冲突文件

`~$*`（Office 锁文件）、`*.tmp`、`*.lock`、`*.bak`、`*.orig`、`*.crdownload`、`*.partial`、`*冲突副本*`、`*-Conflict*`、`*conflicted copy*`、`*.conflict*`、`.tmp/`、`**/.tmp/`

### 8. 工具运行产物

`.git-rewrite/`、`.merkle-snapshot.json`、`JK_del_list.txt`、`sync_gitee.log`、`.agent_history/`

### 9. OfficeAce / 小通 智能体工作区（2026-10-19）

`/MD文件综合/` 下的 `.office-claw/`、`agents/`、`coding_memory/`、`context/`、`docs/`、`memory/`、`messages/`、`prompt_attachment/`、`skills/`、`todo/` 及 `AGENT.md`、`SOUL.md`、`IDENTITY.md`、`USER.md`、`HEARTBEAT.md`、`BACKLOG.md` —— 本机运行状态，本地保留、不进版本库。

## 三、常用维护操作

### 验证某文件是否被忽略、被哪条规则命中

```powershell
git check-ignore -v "路径/文件.pdf"
# 输出形如：.gitignore:78:*.pdf    路径/文件.pdf
```

### 新增一条忽略规则

1. 编辑仓库根目录 `.gitignore`，写入规则并注明日期与原因（保持本文件风格）
2. 若该文件**从未被跟踪**：到此即可
3. 若**已被跟踪**（重点坑）：忽略对已跟踪文件无效，必须先从索引移除（本地文件保留）：
   ```powershell
   git rm --cached -- "路径/文件"
   git commit -m "chore: 停止跟踪 XXX"
   ```

### 批量取消某类已跟踪文件（以 PDF 为例）

```powershell
git rm --cached --ignore-unmatch -q -- "*.pdf"
git commit -m "chore: PDF 文件不再纳入版本库"
```

### 历史清理（体积已进历史时）

仅加忽略 + 取消跟踪**不会缩小仓库体积**，历史中的 blob 仍在。需历史重写（`git filter-branch --index-filter`）+ 强推 + 远端 GC，完整流程与踩坑见 [Git同步与仓库清理记录.md](Git同步与仓库清理记录.md)。

## 四、规则写法速查

| 写法 | 含义 |
|---|---|
| `*.pdf` | 任意层级的 .pdf 文件 |
| `/MD文件综合/todo/` | 仅仓库根下的该目录（前导 `/` 锚定根） |
| `target/` | 任意层级名为 target 的目录 |
| `**/拆分文档/` | 任意层级名为 拆分文档 的目录 |
| `!.env.example` | 取反：前面的规则排除它，此项例外放行 |

## 五、注意事项

1. **含中文路径**在 PowerShell 管道中易乱码，验证时用 `git check-ignore -v` 直接传路径，不要经管道转码
2. 规则变更会随 `sync_gitee.ps1` 的 30 分钟任务自动提交并推送，无需手动 commit
3. 新增大文件类型规则后，建议观察一轮同步日志确认无 `git add` 误纳
4. 切勿把密钥类规则（`.env`、`*.key`）删除或注释
