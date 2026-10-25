# Git 同步与仓库清理记录

> 用途：记录 Gitee 同步链路的全部历史问题、处理方式与经验教训，作为后续优化同步逻辑/清理仓库的操作手册。
> 仓库：`C:\Users\Administrator\Desktop\JK-temp` → `git@gitee.com:jk528528/test.git`（SSH，main 分支）
> 脚本：`签到程序\sync_gitee.ps1`（计划任务每 30 分钟执行，单实例锁防并发）

## 一、同步架构现状

- **同步方向**：单机 → Gitee 单向归档，无第二台机器协作
- **触发**：计划任务「新闻联播Gitee同步30分钟」（每 30 分钟）
- **防护**：`.sync_gitee.lock` 单实例锁 → stale `index.lock` 自愈 → 体积检查 → 空闲轮 pull-only → add/commit/push（全程退出码校验）
- **日志**：`sync_gitee.log` 超 256KB 自动轮转为 `.old`（只留一代）

## 二、问题时间线（现象 → 根因 → 处理）

### 2026-09-09 计划任务集体失败

- **现象**：同步与签到任务全部报「文件不存在」（Last Result -196608）
- **根因**：脚本被移动到 `旧版本` 子目录，任务仍指向原路径；且 PowerShell 5 读取**无 BOM 的 UTF-8** 脚本时中文路径解析为乱码，git 报 `not a git repository`
- **处理**：脚本集中到一个固定目录、仓库路径改绝对路径、脚本统一保存为 **UTF-8 BOM**、`schtasks /change` 重新绑定
- **教训**：① 任务计划程序用绝对路径引用脚本后，**绝不再移动脚本**；② 含中文的 .ps1 必须带 BOM 保存

### 2026-10-16 「假成功」事件

- **现象**：同步日志显示 `sync success`，计划任务 LastTaskResult=0，但远端长期无新提交
- **根因**：sync 进程曾被强杀，残留 `.git\index.lock` → 每轮 `git add` 报 exit 128；旧脚本**不检查 add 退出码**，commit 失败仍继续 pull/push 并打印 success
- **处理**：脚本加入 stale lock 自愈（无 git 进程且锁龄 >5 分钟才删，否则跳过本轮）；add/commit 失败立即 `exit 1`
- **教训**：**每个 git 命令都必须校验 `$LASTEXITCODE`**，否则失败被静默吞掉

### 2026-10-17 脚本加固（防挂起 + 减噪）

| 改动 | 作用 |
|---|---|
| `$env:GIT_TERMINAL_PROMPT = "0"` | 凭证失效时快速报错，不再永久挂起等密码输入（计划任务无交互环境） |
| `git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=60` | 传输停滞 60 秒自动断开（pull/push 均加） |
| `pull --ff-only` | 历史分叉时报错而非产生 merge commit（归档仓库不应有 merge） |
| `git status --porcelain` 为空 → pull-only 退出 | 空闲轮跳过 add/commit/push，日志量减半 |
| `git count-objects -v` 超 700MB 打 WARN | 提前预警 Gitee 配额 |

### 2026-10-17 仓库体积治理（清理历史大文件）

- **背景**：pack 达 962MB，超 Gitee 819MB 配额；当前工作区文件正常（小说/字体），**问题在历史**——曾提交 `Git-2.56.0.2-64-bit.exe`（63.7MB）、z-lib PDF（38.2MB）、大量已删除的小说/PDF（history-only 共 5058 个 blob、原始 530MB）
- **方案**：`git filter-branch --index-filter` 按路径清单（2643 个仅存在于历史的路径，当前树 2299 个文件全部保留）改写 624 个提交 → gc → 删远端游离分支 `origin/master`（非 main 祖先，会钉住旧历史）→ `push --force` main
- **安全措施**：改写前 `git bundle create --all` 全量备份（944MB，`桌面\JK-temp-backup.bundle`）；暂停同步计划任务防并发
- **过程曲折**：第一次用 `git rm -r --cached` 做过滤器，误删当前树大量文件（见踩坑 6），靠改写后校验抓住并完整回滚，改用 `git update-index` 重做

## 三、本次清理踩坑记录（重要）

1. **`cat-file` stdin 管道在 PowerShell 下的编码坑**：`$objs | git cat-file --batch-check` 对含中文的行全部误报 `missing`（PS 管道重编码导致 sha+path 被当成 `<sha>:<path>` 解析）。**正确做法：`git cat-file --batch-all-objects --batch-check` 直接读对象库，不走 stdin**
2. **filter-branch 报 `empty string is not a valid pathspec`**：路径清单文件**尾部换行**和**混入的空行**被 `tr '\n' '\0' | xargs -0` 原样传给 `git rm`。清单需 `TrimEnd` + 过滤空行
3. **`cmd /c` 被本机安全策略禁用**：所有重定向操作必须用 PowerShell 原生命令
4. **后台进程在会话切换后仍然存活**：filter-branch 由后台 Shell 启动，会话/模型切换丢失的是任务句柄，**进程本体继续运行**。判断依据：`.git-rewrite` 目录存在 + `Win32_Process` 可见 git filter-branch 进程。**此状态下严禁手动 git 操作或删 .git-rewrite**
5. **`git count-objects` 报 `garbage found: tmp_obj_*`**：改写产生的临时对象，gc 时自动清理，无害
6. **`git rm -r --cached` 的 pathspec 递归匹配陷阱**：清单路径若与当前树目录重合（历史上是文件、现在成了目录），pathspec 会递归匹配整个子树 → 改写后 624 提交变 49、diff 出现大量误删。幸有 refs/original 备份，`git reset --hard refs/original/refs/heads/main` 完整回滚。**教训：改写后必须校验 diff 为空，任何非空立即回滚
7. **正确工具：`git update-index --force-remove -z --stdin`**：纯索引精确路径操作，无 pathspec 展开、不递归、对不存在路径静默 exit 0（`git rm` 实测对不存在路径直接报错）。改写前先做**零损伤干跑**：复制 `.git\index` 到临时文件，设 `GIT_INDEX_FILE` 环境变量跑一遍过滤器，`git ls-files` 前后数量不变（2299→2299）再上真改写
8. **工具链通信坑**：PowerShell 超长命令（约 700 字符）会被截断或在字符串内部混入换行（路径损坏）；`$pwd` 不跨命令持久，始终用绝对路径。中文长字符串经 IDE 通道传输可能失配——`Grep` 能找到而 `Edit` 报 not found 时，改用 `[IO.File]` 直接读写磁盘**

## 四、清理完成后的收尾步骤（待办）

filter-branch 跑完后依次执行（在 `JK-temp` 目录，PATH 加 `C:\Program Files\Git\cmd`）：

```powershell
# 1. 校验：当前树与改写前必须零差异
git diff refs/original/refs/heads/main main --stat        # 应为空
git status --porcelain                                     # 应为空

# 2. 清旧引用与 reflog，回收空间
git update-ref -d refs/original/refs/heads/main
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git count-objects -vH                                      # 目标 size-pack < 700MB

# 3. 远端：先删游离 master（钉住旧历史），再强推 main
git push origin --delete master
git push origin main --force-with-lease

# 4. 恢复计划任务并实测一轮
#    Get-ScheduledTask | ? { ($_.Actions | % { "$($_.Execute) $($_.Arguments)" }) -match 'sync_gitee' } | Enable-ScheduledTask
#    手动跑 sync_gitee.ps1，确认 clean pull-only 轮正常
```

## 五、后续优化方向

- **若 filter-branch 再失败**：换 `git filter-repo`（需 Python，快 10 倍+）或 BFG（需 Java），本机两者皆无，需先装运行时
- **防再次膨胀**：`.gitignore` 加入 `*.exe`、`*.pdf`、`*.zip` 或设单文件大小预检（pre-commit hook 拒绝 >10MB）；大文件如需归档考虑 Gitee LFS（注意 Gitee LFS 也占配额）
- **配额余量管理**：体积预警阈值 700MB 已内置于 sync_gitee.ps1；Gitee 推送时才校验配额，日常 push 成功不代表没超
- **多分支残留**：远端历史分支会阻止服务端回收空间，强推前务必先清理（本次的 origin/master 即此情况）

> AI生成
