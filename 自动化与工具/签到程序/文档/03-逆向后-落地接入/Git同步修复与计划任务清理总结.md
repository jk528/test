# Git 同步修复与计划任务清理总结

> 时间：2026-10-21 ~ 2026-10-23
> 仓库：签C:\Users\Administrator\Desktop\JK-temp签 → 签git@gitee.com:jk528528/test.git签
> 关联脚本：签签到程序\sync_gitee.ps1签、签签到程序\run_checkin.cmd签

---

## 一、问题全景

### 1.1 Gitee 远端 1294 MB 超 1024 MB 免费配额 → push 全部被拒

- **现象**：`sync_gitee.ps1` 每 30 分钟跑一次，日志里 `push exit code: 1`，远端无新提交
- **远端返回**：
  签签签
  remote: Repo size: 1294.617MB, exceeds quota 1024MB
  ! [remote rejected] main -> main (pre-receive hook declined)
  签签签
- **根因**：`MD`件综合\签 下 17 个 PDF（288 MB）被误纳入版本库，历史中 PDF blob 累计约 400+ MB；之前 `filter-branch` 清理旧大文件后未在 Gitee 执行服务端 GC，远端不可达对象（旧 blob）钉住了体积
- **之前以为的原因**：SSH 密钥失效？网络？merge 冲突？全部排除（`git fetch`、`git pull` 均正常）

### 1.2 计划任务乱码

- **现象**：Gitee 同步任务名显示为 签鏂伴椈鑱旀挱Gitee鍚屾30鍒嗛挓签（GBK 编码残留，中文显示乱码）
- **影响**：排障时用 签Get-ScheduledTask -TaskName "Gitee同步30分钟"签 找不到，只能通过 Actions 参数模糊匹配

### 1.3 新闻联播 11:10 总结触发器藏在 PM2 里

- **现象**：用户问"每天 11:10 的新闻联播总结是哪个定时程序"，查计划任务找不到
- **根因**：PM2 常驻进程 `yzzsAgent` 内部每轮检查 `config.json` 的 签"trigger_time": "11:10"签 触发，不在 Windows 计划任务体系里
- **排查方法**：`pm2 list` → 签pm2 env <id>签 或全局搜 `11:10` 配置值

### 1.4 计划任务/PM2 冗余

机器上挂了一批非系统自带的 Ready 状态任务（签check_report_img_*签、`npcapwatchdog`、QuarkUpdater 等），PM2 还有一个闲置进程，没有统一梳理。

### 1.5 签到脚本无日志轮转

`sync_gitee.ps1` 有 256 KB 自动轮转，但 `run_checkin.cmd` 的输出直接 append 到 `checkin_all.log`，长时间运行日志会无限膨胀。

---

## 二、解决方案（按执行顺序）

### 2.1 停任务 → 备份 → 加忽略 → 取消跟踪

签签签powershell
# 1. 停 30 分钟同步，避免产生注定失败的提交
Get-ScheduledTask | ? { ($_.Actions | % { "$($_.Execute) $($_.Arguments)" }) -match 'sync_gitee' } | Disable-ScheduledTask

# 2. 全量备份（防止 filter-branch 改坏）
git bundle create "C:\Users\Administrator\Desktop\JK-temp-backup-20261021.bundle" --all

# 3. 仓库根 .gitignore 增加 *.pdf
#    作用范围：该仓库内所有子目录，不影响本机其他 Git 仓库

# 4. 取消 17 个已跟踪 PDF（本地文件保留）
git rm --cached --ignore-unmatch -q -- "*.pdf"
git commit -m "chore: PDF 文件不再纳入版本库"
签签签

### 2.2 filter-branch 重写历史

签签签powershell
# 重写所有 38 个提交，从每个提交的索引里删除 PDF
$env:FILTER_BRANCH_SQUELCH_WARNING="1"
git filter-branch -f --index-filter "git rm --cached --ignore-unmatch -q -- '*.pdf'" -- main

# 校验 1：重写前后树 diff 应为 0 行（不能误删了别的）
git diff --stat refs/original/refs/heads/main main

# 校验 2：历史里不应再有 PDF
git log main --oneline -- "*.pdf"   # 应无输出

# 清理旧引用 + gc
git update-ref -d refs/original/refs/heads/main
git reflog expire --expire=now --all
git gc --prune=now
签签签

重写后 main 历史原始体积：490 MB → **96.9 MB**。

### 2.3 远端 Gitee 配额的正确解锁姿势

- **所有 push 都被拒**（包括 `git push origin --delete master`），必须先走 Gitee 设置页执行仓库 GC
- GC 入口：签https://gitee.com/jk528528/test/settings#git-gc签
- GC 后再强推：
  签签签powershell
  git push origin --delete master                     # 先删钉住旧历史的游离分支
  git push origin main --force-with-lease             # 强推清理后的历史
  git branch --set-upstream-to=origin/main main
  签签签
- **教训**：之前 `filter-branch` + 强推后没执行远端 GC，旧 blob 仍被服务端钉住（Gitee 强推后不会自动 GC）。每次历史重写 + 强推都必须跟进服务端 GC

### 2.4 计划任务清理与加固

签签签powershell
# ---- PM2 ----
pm2 delete yzzsAgent     # 新闻联播 11:10 的触发器
pm2 save

# ---- 禁用多余任务 ----
Disable-ScheduledTask -TaskName "check_report_img_daily"
Disable-ScheduledTask -TaskName "check_report_img_onstart"
Disable-ScheduledTask -TaskName "check_report_img_random"
Disable-ScheduledTask -TaskName "npcapwatchdog"

# ---- 乱码任务干净重注册 ----
# 先注销旧的（乱码名），再用 UTF-8 任务名 + 加固参数注册
Unregister-ScheduledTask -TaskName "<乱码名>" -Confirm:$false
Register-ScheduledTask -TaskName "Gitee同步30分钟" 签
    -Action (New-ScheduledTaskAction -Execute powershell.exe -Argument "...") 签
    -Trigger (New-ScheduledTaskTrigger -Once -At <now+30min> -RepetitionInterval 30min) 签
    -Settings (New-ScheduledTaskSettingsSet 签
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries 签
        -StartWhenAvailable 签
        -ExecutionTimeLimit 5min 签
        -MultipleInstances IgnoreNew 签
        -RestartCount 1 -RestartInterval 1min) 签
    -RunLevel Highest -Force

# ---- 签到任务同样加固 ----
Register-ScheduledTask -TaskName "统一签到" 签
    -Action ... -Trigger (New-ScheduledTaskTrigger -Daily -At 10:35) 签
    -Settings (... ExecutionTimeLimit 90min, RestartCount 2 ...)
签签签

### 2.5 日志轮转

在 `run_checkin.cmd` 开头加 5 MB 自动轮转（只保留一代 `.old`），与 `sync_gitee.ps1` 的 256 KB 轮转策略独立。

---

## 三、最终状态

### 3.1 远端仓库

| 项 | 清理前 | 清理后 |
|---|---|---|
| Repo size（Gitee 显示） | 1294 MB | < 1024 MB |
| main 历史原始体积 | 490 MB | 96.9 MB |
| HEAD 中的 PDF | 17 个 / 288 MB | 0 |
| 历史中的 PDF | 每个提交都有 | 0 |
| 远端 master 分支 | 存在（钉住旧历史） | 已删 |

### 3.2 计划任务

| 任务 | 触发器 | 状态 |
|---|---|---|
| **统一签到** | 每日 10:35 | ✅ Ready，90min 超时，失败重启 2 次 |
| **Gitee同步30分钟** | 每 30 分钟 | ✅ Ready，5min 超时，失败重启 1 次 |

系统自带任务（NPCAP watchdog、PM2Resurrect、QuarkUpdater、SilCollector 等）未动。

### 3.3 PM2

| 进程 | 动作 |
|---|---|
| yzzsAgent（新闻联播 11:10 触发器） | 删除并 save |
| 其他 | 无 |

### 3.4 备份

全量 bundle 已落盘：签C:\Users\Administrator\Desktop\JK-temp-backup-20261021.bundle签（292 MB）。包含重写前完整历史，后续确认稳定运行一周后可删除。

---

## 四、关键教训

1. **`filter-branch` 改完本地历史 ≠ 远端体积变了**。强推 + Gitee 服务端 GC 是成套动作，缺一不可
2. **计划任务乱码是 GBK 编码残留**。干净注销再注册（`Unregister-ScheduledTask` + `Register-ScheduledTask`）是修复方式
3. **新闻联播的 11:10 触发器藏在 PM2 里**。排查定时任务时，先查 `Get-ScheduledTask`，再查 `pm2 list`，再搜配置文件里的时间字符串，三者结合
4. **忽略规则 签*.pdf签 只作用于未跟踪文件**。已被 `git add` 过的必须 `git rm --cached` 才能生效
5. **PowerShell 管道中中文路径容易编码错位**，验证时直接用 签git check-ignore -v "完整路径"签 而不要转管道
6. **每 30 分钟一次的任务不适合 `DailyTrigger`**，要用 `TimeTrigger` + `RepetitionInterval`

---

## 五、后续清理建议

| 目标 | 操作 |
|---|---|
| 废弃脚本 | 签新闻联播/流程/旧版本/签 整个目录 + 签新闻联播/最终版/不用积分/scripts/签（与 签最新版本/签 功能重叠） |
| 备份 bundle | 稳定运行 1 周后删除 `JK-temp-backup-20261021.bundle` 释放 292 MB |
| `.gitignore` 复查 | 上次有人手动删除过根目录 `.gitignore`，每次大改动后需验证它存在且 签*.pdf签 规则在 |

## 六、以后查看计划任务

签签签powershell
# 最常用（PowerShell）
Get-ScheduledTask | Where-Object { $_.TaskPath -notmatch 'Microsoft' } | Select TaskName,State

# 只看自己项目的
Get-ScheduledTask | ? { $_.Actions | % { "$($_.Execute) $($_.Arguments)" } -match 'JK-temp|签到|sync' } | Select TaskName,State

# GUI
taskschd.msc

# PM2 进程列表
pm2 list
签签签
