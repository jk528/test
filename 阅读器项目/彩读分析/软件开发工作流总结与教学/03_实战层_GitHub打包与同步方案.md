# 实战层 · GitHub 打包与同步方案

> **适合人群**：已能开发软件，准备发布给用户的项目
> **学习目标**：掌握从本地开发到用户手中的全链路：打包 + CI/CD + 自动更新 + 同步
> **案例基底**：彩读三平台五架构 CI + GitHub Releases + WebDAV 同步 + 书包加密
> **预计学习时间**：3-4 小时

---

## 第一课：打包流水线全流程

### 1.1 彩读的打包流水线

```
npm run build / npm run release
    │
    ├─ Step 1: electron-vite build
    │          编译主进程 (dist/main/)
    │          编译 preload (dist/preload/)
    │          编译渲染进程 (dist/renderer/)
    │          编译 AI embedding worker
    │          运行 Vite 插件：Monaco 补丁、pdfjs 资源拷贝
    │
    ├─ Step 2: electron-rebuild -f -w better-sqlite3,opencc
    │          按目标 Electron 版本重编译原生 .node 文件
    │
    ├─ Step 3: node scripts/prune-pack-deps.mjs
    │          裁剪 node_modules（减少数十 MB）
    │          交叉编译时补装目标架构原生包
    │
    ├─ Step 4: electron-builder
    │          beforePack 钩子 → 再次执行 prune
    │          onNodeModuleFile 钩子 → 排除非目标平台文件
    │          打包为 NSIS/DMG/AppImage
    │          asar 打包 + asarUnpack 解包原生模块
    │
    └─ Step 5 (release only): electron-builder --publish always
               上传到 GitHub Releases
```

### 1.2 每一步的作用与新人易错点

| 步骤 | 作用 | 新人易错点 |
|------|------|-----------|
| Step 1 编译 | 产出三端代码 | 忘了编译 worker |
| Step 2 重编译 | 原生模块按 Electron ABI | 跳过这步导致 .node 加载失败 |
| Step 3 裁剪 | 减小包体 | 不裁剪包体大几十 MB |
| Step 4 打包 | 生成安装包 | 没配 asar 导致源码暴露 |
| Step 5 发布 | 上传 Release | Token 权限不够导致失败 |

### 1.3 package.json scripts 配置

```json
{
  "scripts": {
    "dev": "electron-vite dev",
    "build": "electron-vite build && electron-rebuild -f -w better-sqlite3,opencc && node scripts/prune-pack-deps.mjs && electron-builder",
    "release": "同 build + --publish always",
    "typecheck": "vue-tsc --noEmit",
    "test": "node --experimental-strip-types --test"
  }
}
```

### 1.4 动手练习：配你的打包脚本

1. 写 `npm run build` 能产出当前平台的安装包
2. 本地验证安装包能正常安装运行
3. 再配 `npm run release`（先别真发布，用 `--publish never` 测试）

---

## 第二课：node_modules 裁剪（体积控制核心）

### 2.1 为什么需要裁剪

```
不裁剪：node_modules 几百 MB → 安装包几百 MB
裁剪后：node_modules 几十 MB → 安装包几十 MB
```

### 2.2 彩读的裁剪分类

| 类别 | 被裁剪的内容 | 理由 |
|------|-------------|------|
| 整包移除 | onnxruntime-web | Web/WASM 推理，不需要 |
| 整包移除 | 完整 sharp + @img/* | 不做图像推理 |
| 按平台移除 | 非目标平台的 sqlite-vec-* | 原生包按平台分发 |
| 按平台移除 | 非目标平台的 @node-rs/jieba-* | 只留当前平台 |
| 按路径裁剪 | 各包的 src/、deps/、*.map、README | 非运行时文件 |

### 2.3 裁剪脚本的设计要点

```js
// prune-pack-deps.mjs 核心逻辑
// 1. 整包移除：直接 rm -rf
// 2. 按平台移除：读 --platform 参数，移除非目标平台包
// 3. 按路径裁剪：遍历各包，移除 src/、*.map 等
// 4. 交叉编译补装：npm pack 补装目标架构原生包
// 5. macOS 校验：lipo -archs 校验 .node 的 Mach-O 架构
```

### 2.4 electron-builder 阶段的双层裁剪

| 钩子 | 脚本 | 作用 |
|------|------|------|
| `beforePack` | electron-before-pack.mjs | 收集依赖前执行 prune |
| `onNodeModuleFile` | electron-on-node-module-file.mjs | 逐文件排除非目标平台 .node |

### 2.5 动手练习：分析你的 node_modules

```bash
# 看哪些包最大
du -sh node_modules/* | sort -rh | head -20
# 看哪些是原生包（按平台分发）
find node_modules -name "*.node" | head -20
```

找出可以裁剪的包，写一个简单的裁剪脚本。

---

## 第三课：CI/CD 多架构并行构建

### 3.1 彩读的 CI 矩阵

GitHub Actions（`.github/workflows/release.yml`），推送版本 tag 后 5 个 job 并行：

| 平台 | 架构 | Runner | 产物 |
|------|------|--------|------|
| Windows | x64 | windows-2025-vs2026 | NSIS + Portable |
| macOS | arm64 | macos-latest | DMG |
| macOS | x64 | macos-15-intel（原生 Intel） | DMG |
| Linux | arm64 | ubuntu-24.04-arm | AppImage |
| Linux | x64 | ubuntu-latest | AppImage |

### 3.2 CI 触发方式

```yaml
on:
  push:
    tags:
      - "v*"          # 推送 v 开头的 tag 自动触发
  workflow_dispatch:   # 也可在 Actions 页面手动触发（补跑）
```

### 3.3 完整 CI 流程（2 个 Job）

```
Job 1: build（5 个并行矩阵）
  checkout → setup-node → verify-tag-matches-version
  → cache-electron → npm ci
  → electron-vite build
  → electron-rebuild --arch <target>
  → prune-pack-deps --platform <target> --arch <target>
  → electron-builder --publish never --<target> --<arch>
  → [Linux x64] verify AppImage < 200MB
  → upload-artifact (release-<platform-arch>)

Job 2: publish（依赖 build 完成）
  checkout → setup-node → npm ci --ignore-scripts
  → download-artifact (所有 5 个 build job 的产物)
  → collect release assets (exe/dmg/AppImage/yml/blockmap)
  → electron-builder publish --policy always --files ...
  → 统一发布到同一条 GitHub Release
```

### 3.4 CI 环境变量优化

```yaml
env:
  CSC_IDENTITY_AUTO_DISCOVERY: false       # 无证书时跳过签名
  ONNXRUNTIME_NODE_INSTALL_CUDA: skip      # 跳过 300MB+ CUDA 下载
```

### 3.5 缓存优化

```yaml
- name: Cache Electron downloads
  uses: actions/cache@v5
  with:
    path: |
      ~/.cache/electron
      ~/.cache/electron-builder
    key: electron-${{ runner.os }}-${{ matrix.arch }}-${{ hashFiles('package-lock.json') }}
```

按 `runner.os + arch + package-lock.json hash` 缓存，避免每次 CI 重新下载。

### 3.6 包体大小自动校验

```yaml
- name: Verify Linux x64 package size
  if: matrix.name == 'Linux-x64'
  shell: bash
  run: |
    appimage=(release/*.AppImage)
    size=$(stat -c%s "${appimage[0]}")
    if [ "$size" -gt 200000000 ]; then
      echo "Linux x64 AppImage exceeds 200 MB — prune or pack regression"
      exit 1
    fi
```

AppImage 超过 200MB，CI 直接 fail——防止裁剪脚本退化。

### 3.7 动手练习：配你的 CI

1. 写一个 `.github/workflows/release.yml`
2. 先只配当前平台（别一上来就五架构）
3. 加包体大小校验门禁
4. 本地推 tag 测试 CI 是否成功

---

## 第四课：发布到 GitHub Releases

### 4.1 开发者视角的发布流程

```bash
# 1. 提交代码
git commit -a -m "修改了xxx"

# 2. 更新版本号（自动改 package.json + 打 tag）
npm version patch|minor|major

# 3. 推送代码和 tag
git push && git push --tags

# CI 自动完成：5 架构并行构建 → 统一发布到 GitHub Release
# 全程无需人工干预，无需在三台机器上分别打包
```

### 4.2 发布产物管理的自动化细节

| 自动化点 | 实现 | 解决的问题 |
|----------|------|------------|
| Tag 版本校验 | CI 比对 tag 与 package.json | 不一致直接 fail |
| 中文文件名规避 | artifactName 用 ${name} 而非 ${productName} | GitHub Release 上传失败 |
| 多架构更新文件隔离 | publish.channel 为 latest-${arch} | arm64/x64 互相覆盖 |
| builder-debug 清理 | rm -f release/builder-debug.yml | 调试文件混入 Release |
| 并发控制 | concurrency.group + cancel-in-progress: false | 避免半成品 Release |
| artifact 合并 | download-artifact + merge-multiple: true | 5 个 build job 产物合并 |
| macOS 未签名处理 | CSC_IDENTITY_AUTO_DISCOVERY: false | 无证书时未签名包发布 |

### 4.3 撤销发布

```bash
# 1. 网页端删除 Release 记录
# 2. 删除 tag
git tag -d v1.0.0          # 删本地
git push origin :refs/tags/v1.0.0  # 删远端
```

### 4.4 本地手动发布（CI 不可用时的降级方案）

```bash
# 设置 GitHub Token
export GH_TOKEN='你的TOKEN'  # 需要 repo 权限

# 创建 tag + 推送
git tag v1.0.0
git push origin v1.0.0

# 构建打包并发布
npm run release
# = electron-vite build + electron-rebuild + prune-pack-deps + electron-builder --publish always
```

> 限制：本地 `npm run release` 只能打**当前机器**对应平台/架构的包。多架构需走 CI。

### 4.5 动手练习：发布你的第一个版本

1. 配好 CI（上一课）
2. 本地 `npm version patch` 打 tag
3. `git push --tags` 触发 CI
4. 等 CI 跑完，去 GitHub Release 页面看产物

---

## 第五课：自动更新

### 5.1 electron-updater 配置

彩读用 electron-updater + GitHub Releases 实现自动更新：

```json
// electron-builder 配置
{
  "publish": {
    "provider": "github",
    "owner": "ssnangua",
    "repo": "ColorTxt"
  }
}
```

### 5.2 多架构更新文件隔离

```json
{
  "publish": {
    "provider": "github",
    "channel": "latest-${arch}"   // arm64 和 x64 的 latest*.yml 不互相覆盖
  }
}
```

### 5.3 中文文件名规避

```json
{
  "build": {
    "artifactName": "${name}-${version}-${os}-${arch}.${ext}"
    // 用 ${name}（colortxt-...）而非 ${productName}（彩读）
    // electron-builder 不对中文路径做 URL 编码，上传会失败
  }
}
```

### 5.4 动手练习：配自动更新

1. electron-builder 配 publish provider
2. 主进程写 autoUpdater 逻辑
3. 发布一个版本，再发布一个版本，验证能自动更新

---

## 第六课：同步方案

### 6.1 彩读的三线同步

| 同步线 | 内容 | 冲突策略 |
|--------|------|----------|
| 主窗配置/书包 | 阅读进度、书签、高亮词、笔记、角色卡 | 一律覆盖 + 增量 |
| 找书窗书架 | 书架数据 | 按内容 hash/mtime |
| 找书窗书源 | 书源列表 | 合并不删本地多出的源 |

### 6.2 WebDAV 同步设计

```
冲突策略：一律覆盖（不比较时间）
增量策略：
  - 书包按内容 hash/mtime
  - 背景图按文件名+大小
  - 书源合并不删本地多出的源
```

### 6.3 书包打包与加密

```
书包 = txt/md/插图目录 + 书签/高亮词/笔记/角色卡 + 阅读进度

.ctz  = 普通 zip 压缩包
.ctzx = 加密包（AES-256-GCM + PBKDF2）
```

- 安装时注册 .ctz/.ctzx 的打开方式（双击打开）
- .txt/.md 仅加入「打开方式」，不抢系统默认
- 打开/导入按文件名匹配做更新或解压

### 6.4 多窗口防覆盖

```
多窗口共用同一份 localStorage
写会触发其它窗口的 storage 事件
落盘时先读最新快照，仅把本窗有改动的字段盖上去
```

### 6.5 动手练习：设计你的同步方案

1. 列出需要同步的数据
2. 对每类数据定冲突策略（覆盖/合并/跳过）
3. 选同步通道（WebDAV/云存储/自建服务）

---

## 第七课：启动器制作（Windows 一键启动）

### 7.1 三种交付物

| 文件 | 作用 | 放在哪 |
|------|------|--------|
| 主启动器 `启动<名字>.vbs` | 检查端口 → 后台起服务 → 等待就绪 → 检测窗口 | 项目目录 |
| 辅助脚本 `start_<name>.bat` | 真正执行启动命令，输出写日志 | 与 VBS 同目录 |
| 桌面快捷方式 `<名字>.lnk` | 指向 VBS，双击触发 | 桌面 |

### 7.2 VBS 核心流程

```
1. CheckPort(port)?
   ├─ Yes + app running  → 退出（已在运行，幂等）
   ├─ Yes + app gone     → KillPortOwners → Sleep 3s → 走 ②
   └─ No                  → 走 ②
2. 启动 BAT（minimized）
3. 等 port 就绪（max 60s）→ 超时 = 弹错误框 + 退出 1
4. 等 app 进程出现（max 30s）→ 超时 = 弹警告框
5. 成功 → 记日志结束
```

### 7.3 踩坑教训

| Bug | 根因 | 修复 |
|-----|------|------|
| vite 在跑但 electron 已退出 → 不重启 | 端口复用分支没检查应用进程 | 端口在跑时先检查 app 进程，不在则 kill 残留重启 |
| vite 60 秒没起来时静默继续 | 超时只 warn 不退出 | 超时 = 致命错误，弹窗 + 退出 |

**核心教训**：
- 端口复用必须验证应用进程也在
- 超时必须是致命退出，不能静默继续

### 7.4 动手练习：为你的项目做启动器

1. 写 VBS 检查项目目录 + 依赖
2. 写 BAT 执行 `npm run dev`
3. 用 PowerShell 生成桌面快捷方式
4. 验证双击能启动、再次双击不重复启动

---

## 第八课：后续演进——POC 验证文化

### 8.1 彩读万维读书计划的 POC 优先

即使是成熟项目，下一阶段也先做 POC 验证：

```
阶段 0 · POC 技术验证（1.5 周）
  POC-1: jieba 词性准确率 ≥ 95%?
  POC-2: decorations 八维渲染可行?
  POC-3: 字间距错位可接受?
  POC-4: 窗口化性能 ≥ 55 fps?
  POC-5: transformers 对比 jieba?

POC 全部通过 → 进入阶段 1（α MVP）
POC 关键项失败 → 调整方案，不盲目投入
```

### 8.2 POC 的设计原则

| 原则 | 说明 |
|------|------|
| 证伪优先 | POC 的目的是发现"做不到"，而非证明"做得到" |
| 量化标准 | 每项 POC 有量化通过标准（如准确率 ≥ 95%） |
| 时间盒 | 每项 POC 有时间上限（如 2 天），超时即止 |
| 决策矩阵 | POC 结果直接决定 Go/No-Go |

### 8.3 动手练习：为你的下一阶段写 POC

1. 列出下一阶段的 3-5 个关键假设
2. 为每个假设写验证方法 + 量化标准 + 时间上限
3. POC 结果决定是否投入正式开发

---

## 实战层总结：从开发到用户的 8 步清单

```
□ 1. 配打包流水线（build + release 脚本）
□ 2. 写 node_modules 裁剪脚本
□ 3. 配 CI/CD（先单平台，再多架构）
□ 4. 加质量门禁（包体大小 + 版本校验）
□ 5. 发布到 GitHub Releases
□ 6. 配自动更新（electron-updater）
□ 7. 设计同步方案（WebDAV/书包/冲突策略）
□ 8. 做启动器（VBS + BAT + 快捷方式）
```

完成这 8 步，你的软件就能从开发机器到达用户手中，并持续更新。

---

## 三层教学总结

| 层级 | 核心问题 | 答案 |
|------|---------|------|
| 入门层 | 如何从零开始？ | 立项决策 + 技术选型 + 范围控制 |
| 进阶层 | 如何高质量迭代？ | 10 条控制哲学 + 全链路自动化 |
| 实战层 | 如何发布给用户？ | 打包 + CI/CD + 同步 + 启动器 |

**彩读的完整公式**：
```
高质量软件 = (清晰定位 × 积木式架构)           ← 入门层
           + (小步快跑 × 发布即公告)           ← 进阶层
           + (补丁优先 × 兼容不复制)           ← 进阶层
           + (全链路自动化 × 诚实风险声明)     ← 实战层
```

> **关键提醒**：实战层最重要的是**真的发布一次**。配 CI、推 tag、看 Release 页面出现产物——这个正反馈会让你理解整个工作流的意义。不要永远停留在"本地能跑"的阶段。