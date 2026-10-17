# 彩读 ColorTxt 全部依赖项目库

> 彩读 ColorTxt 项目中引用的所有上游开源项目（含文本处理、框架构建、网络、多媒体等）
> 整理日期：2026-09-29
> 总计：**49 个项目，约 861 MB**
> 分类：9 大类
> 分析深度：基于彩读 src 目录逐文件 import 追踪 + 调用点上下文分析

---

## 如何阅读本文件

每个项目包含以下信息块：

| 字段 | 说明 |
|------|------|
| ⭐ 标记 | 彩读项目直接使用的核心依赖 |
| **仓库** | GitHub 仓库地址 |
| **大小** | 源码大小（shallow clone） |
| **语言** | 主要开发语言 |
| **彩读中的包** | package.json 中的包名和版本 |
| **彩读中的使用文件数** | 在 src 中被 import 的文件数量 |
| **核心 API** | 彩读实际调用的关键方法 |
| **具体用途** | 在彩读中承担的具体功能 |
| **上游依赖** | 该项目依赖的其他项目（已下载的） |
| **下游协作** | 彩读中哪些模块调用它，以及和哪些项目配合工作 |

---

## 目录

- [01 - 分词与 NLP](#01---分词与-nlp-7-个)
- [02 - 文档解析](#02---文档解析-7-个)
- [03 - 文本处理](#03---文本处理-9-个)
- [04 - 编辑器与可视化](#04---编辑器与可视化-7-个)
- [05 - 数学公式](#05---数学公式-2-个)
- [06 - 框架与构建](#06---框架与构建-10-个)
- [07 - 网络与协议](#07---网络与协议-3-个)
- [08 - 多媒体处理](#08---多媒体处理-3-个)
- [09 - 其他工具](#09---其他工具-1-个)
- [核心功能链路图](#核心功能链路图)
- [模块协作矩阵](#模块协作矩阵)
- [附录 A：通用工作流程（可复用到其他项目）](#附录-a通用工作流程可复用到其他项目)
- [附录 B：分类模板与命令速查](#附录-b分类模板与命令速查)
- [补充说明](#补充说明)

---

## 附录 A：通用工作流程（可复用到其他项目）

> 本方法可用于任何 Node.js/npm 项目，快速收集和分析其全部上游开源依赖。
> 以彩读 ColorTxt 为示例项目。

### A.1 工作流程总览（5 步法）

```
1. 提取依赖 → 2. 分类规划 → 3. 批量下载 → 4. 深度分析 → 5. 文档整理
```

| 步骤 | 目标 | 产出 | 耗时（参考） |
|------|------|------|-------------|
| 1. 提取依赖 | 从 package.json 拿到完整依赖列表 | 依赖清单（dependencies + devDependencies） | 5 分钟 |
| 2. 分类规划 | 按功能领域分组，规划文件夹结构 | 分类方案 + 文件夹 | 10 分钟 |
| 3. 批量下载 | shallow clone 所有 GitHub 仓库 | 源码文件夹 | 10-30 分钟（取决于数量和网速） |
| 4. 深度分析 | 逐文件搜索 import，追踪实际调用方式 | 每个依赖的用途/API/协作关系 | 1-2 小时 |
| 5. 文档整理 | 写入 README，含链路图和协作矩阵 | 完整 README.md | 30-60 分钟 |

---

### A.2 第一步：提取依赖

**目标**：拿到项目所有直接依赖的完整清单。

**方法**：读取 `package.json` 中的 `dependencies` 和 `devDependencies` 字段。

```bash
# 快速查看所有依赖
cat package.json | grep -E '"(@?[a-zA-Z0-9_-]+/)?[a-zA-Z0-9_-]+":'
```

**注意事项**：
- `dependencies` 是运行时依赖，**必须下载**
- `devDependencies` 是开发/构建时依赖，按需下载
- `@types/*` 类型定义包通常不需要下载源码（纯声明文件）
- `file:` 协议的本地包不是上游依赖，跳过
- monorepo 的子包只需下载主仓库（如 markmap-lib 和 markmap-view 都在 markmap 仓库里）

**彩读示例结果**：12 个 dependencies + 30 个 devDependencies = 42 个包，其中 33 个非 @types 包需要下载。

---

### A.3 第二步：分类规划

**目标**：按功能领域对依赖进行分组，便于理解和查阅。

**通用 9 大类分类法**（可按项目类型调整）：

| 分类编号 | 分类名称 | 包含内容 | 适用项目 |
|---------|---------|---------|---------|
| 01 | 核心业务 | 项目最核心的领域依赖 | 因项目而异 |
| 02 | 数据解析 | 各种文件格式/数据格式解析 | 所有项目 |
| 03 | 数据处理 | 编码转换、数据库、压缩解压 | 所有项目 |
| 04 | UI 与可视化 | 编辑器、图表、动画 | 前端/桌面项目 |
| 05 | 专项领域 | 数学公式、GIS、音频处理等 | 有专项功能的项目 |
| 06 | 框架与构建 | 运行时框架、构建工具、编译器 | 所有项目 |
| 07 | 网络与协议 | HTTP、WebSocket、代理、Cookie | 有网络功能的项目 |
| 08 | 多媒体处理 | 图片、音频、视频处理 | 有多媒体的项目 |
| 09 | 其他工具 | 系统工具、辅助工具 | 所有项目 |

**彩读的分类映射**：

| 通用分类 | 彩读分类 | 说明 |
|---------|---------|------|
| 01 核心业务 | 01 分词与 NLP | 阅读器的核心差异化能力 |
| 02 数据解析 | 02 文档解析 | EPUB/PDF/Markdown/词典格式 |
| 03 数据处理 | 03 文本处理 | 编码、数据库、压缩、格式化 |
| 04 UI 与可视化 | 04 编辑器与可视化 | Monaco、词云、思维导图 |
| 05 专项领域 | 05 数学公式 | KaTeX 数学公式渲染 |
| 06 框架与构建 | 06 框架与构建 | Electron/Vue/Vite/TS |
| 07 网络与协议 | 07 网络与协议 | ws/tough-cookie/socks |
| 08 多媒体处理 | 08 多媒体处理 | sharp/heic/speex |
| 09 其他工具 | 09 其他工具 | font-list |

**创建文件夹命令**：

```powershell
# PowerShell
$base = "d:\your-project-deps"
$categories = @("01-核心业务", "02-数据解析", "03-数据处理", "04-UI与可视化", "05-专项领域", "06-框架与构建", "07-网络与协议", "08-多媒体处理", "09-其他工具")
foreach ($cat in $categories) {
    New-Item -ItemType Directory -Path "$base\$cat" -Force | Out-Null
}
```

---

### A.4 第三步：批量下载

**目标**：将所有依赖的 GitHub 源码 shallow clone 到对应分类文件夹。

**批量下载命令模板**：

```powershell
$git = "C:\Program Files\Git\bin\git.exe"
$base = "d:\your-project-deps"
$dir = "$base\01-核心业务"

# 单个下载
& $git clone --depth 1 https://github.com/owner/repo.git "$dir\repo-name"

# 批量下载（把项目列表放在数组里）
$projects = @(
    @{ name = "project-a"; url = "https://github.com/owner-a/project-a.git" },
    @{ name = "project-b"; url = "https://github.com/owner-b/project-b.git" }
)

foreach ($p in $projects) {
    Write-Host "Downloading: $($p.name)"
    & $git clone --depth 1 $p.url "$dir\$($p.name)" 2>&1 | Select-Object -Last 1
    Write-Host ""
}
```

**寻找 GitHub 仓库地址的方法**：

1. **首选**：直接在 npm 页面搜索包名，找到 Repository 链接
2. **次选**：查看 node_modules 中对应包的 package.json，找 `repository` 或 `homepage` 字段
3. **搜索**：用 `npm view <package-name> repository.url` 命令获取
4. **Web 搜索**：GitHub + 包名 + "npm" 关键词

```powershell
# 从 node_modules 中提取仓库地址
$pkg = "d:\your-project\node_modules\some-package\package.json"
$json = Get-Content $pkg -Raw | ConvertFrom-Json
$json.repository.url  # 或 $json.homepage
```

**下载策略**：
- 全部使用 `--depth 1` 浅克隆，节省空间和时间
- monorepo 只下载主仓库，子包在仓库子目录中
- 找不到 GitHub 地址的包，先记下来后面补
- 下载完成后统计大小，检查是否有异常大的项目

---

### A.5 第四步：深度分析

**目标**：弄清楚每个依赖在项目中**实际怎么用**，而不是只看 package.json。

**分析方法（逐文件 import 追踪法）**：

```
1. 全局搜索 import/require → 2. 找到调用点 → 3. 看上下文 → 4. 梳理协作关系
```

**具体操作**：

```bash
# 1. 搜索所有 import 语句，找到使用该依赖的文件
grep -rn "from ['\"]package-name['\"]" src/
grep -rn "require(['\"]package-name['\"]" src/

# 2. 统计使用文件数（衡量依赖的重要程度）
grep -rl "from ['\"]package-name['\"]" src/ | wc -l

# 3. 深入每个调用点，看调用了哪些 API
#    打开文件，搜索变量名，查看具体调用方式

# 4. 记录：
#    - 核心 API 列表（实际调用的方法）
#    - 在哪个功能模块中使用
#    - 与其他哪些依赖配合工作
```

**分析维度**（每个依赖都回答这些问题）：

| 维度 | 问题 |
|------|------|
| 引入方式 | import 还是 require？静态还是动态？ |
| 使用频率 | 多少个文件用到？是核心还是边缘？ |
| 核心 API | 实际调用了哪些方法/类？（不要列没用上的） |
| 业务用途 | 承担什么具体功能？（不是"是什么"，而是"用来干嘛"） |
| 上游依赖 | 它依赖哪些已下载的项目？ |
| 下游协作 | 哪些模块调用它？和哪些项目配合？ |

**深度分析的价值**：
- 区分"核心依赖"和"边缘依赖"（用的文件越多越核心）
- 发现意想不到的依赖关系（比如 A 和 B 看似无关，实际在某个模块里紧密配合）
- 画出功能链路图，理解项目架构
- 为后续替换/升级依赖提供依据

---

### A.6 第五步：文档整理

**目标**：把分析结果整理成结构化的 README，方便查阅和复用。

**README 结构模板**：

```markdown
# 项目名 全部依赖项目库

> 一句话说明
> 整理日期：YYYY-MM-DD
> 总计：N 个项目，约 X MB
> 分类：N 大类
> 分析深度：基于 src 目录逐文件 import 追踪 + 调用点上下文分析

---

## 如何阅读本文件
（每个项目的信息字段说明）

## 目录
（所有分类的链接）

## 01 - 分类名（N 个）

### ⭐ 1. 项目名
- 仓库：GitHub 链接
- 大小：X MB / N 文件
- 语言：主要语言
- 项目中的包：包名 ^版本
- 使用文件数：N 个
- 核心 API：（表格，列出实际调用的方法）
- 具体用途：（分点说明承担的功能）
- 上游依赖：（该项目依赖的其他已下载项目）
- 下游协作：（哪些模块调用它，和哪些项目配合）

（每个项目重复以上结构）

## 核心功能链路图
（用 ASCII 图画出主要业务流程的依赖链路）

## 模块协作矩阵
（中心模块 × 协作依赖的矩阵表）

## 附录 A：通用工作流程
（本章节内容，可复用）

## 附录 B：分类模板与命令速查
（分类模板和常用命令）

## 补充说明
（许可证、版本、monorepo 说明等）
```

---

## 附录 B：分类模板与命令速查

### B.1 通用 9 大类分类模板

| 编号 | 分类名 | 典型包含 | 彩读对应 |
|------|--------|---------|---------|
| 01 | 核心业务 | 项目最核心的差异化能力 | 分词与 NLP |
| 02 | 数据解析 | 文件格式、数据格式、协议解析 | 文档解析 |
| 03 | 数据处理 | 编码、数据库、压缩、加密、格式化 | 文本处理 |
| 04 | UI 与可视化 | 编辑器、图表、动画、UI 组件库 | 编辑器与可视化 |
| 05 | 专项领域 | 数学、GIS、音频、视频、3D 等 | 数学公式 |
| 06 | 框架与构建 | 运行时框架、构建工具、编译器、测试框架 | 框架与构建 |
| 07 | 网络与协议 | HTTP、WebSocket、RPC、代理、认证 | 网络与协议 |
| 08 | 多媒体处理 | 图片、音频、视频编解码与处理 | 多媒体处理 |
| 09 | 其他工具 | 系统工具、辅助工具、不好分类的 | 其他工具 |

**调整建议**：
- 后端项目：把 04 换成"API 框架"，增加"中间件/缓存"分类
- 移动端项目：把 04 换成"原生能力/组件"
- CLI 工具：把 04 换成"终端 UI/交互"
- 纯库项目：分类可以更少，按功能模块分

---

### B.2 常用命令速查

#### 提取依赖

```bash
# 查看所有依赖（dependencies + devDependencies）
cat package.json | grep -E '^\s*"(@?[a-zA-Z0-9_-]+/)?[a-zA-Z0-9_-]+":\s*"'

# 只看 dependencies
node -e "const p=require('./package.json'); Object.keys(p.dependencies||{}).forEach(k=>console.log(k))"

# 只看 devDependencies
node -e "const p=require('./package.json'); Object.keys(p.devDependencies||{}).forEach(k=>console.log(k))"

# 统计依赖总数
node -e "const p=require('./package.json'); console.log('deps:', Object.keys(p.dependencies||{}).length, 'devDeps:', Object.keys(p.devDependencies||{}).length)"
```

#### 获取仓库地址

```bash
# 用 npm view 获取仓库地址
npm view <package-name> repository.url
npm view <package-name> homepage

# 从本地 node_modules 读取
node -e "console.log(require('<package-name>/package.json').repository?.url || require('<package-name>/package.json').homepage)"
```

#### 批量下载

```powershell
# PowerShell 批量 shallow clone
$git = "C:\Program Files\Git\bin\git.exe"
$dir = "d:\target-dir\01-分类"

$projects = @(
    @{ n = "name1"; u = "https://github.com/owner/repo1.git" },
    @{ n = "name2"; u = "https://github.com/owner/repo2.git" }
)

foreach ($p in $projects) {
    Write-Host "→ $($p.n)"
    & $git clone --depth 1 $p.u "$dir\$($p.n)" 2>&1 | Select-Object -Last 1
}
```

#### 统计大小

```powershell
# 统计某个分类下所有项目的大小
$dir = "d:\target-dir\01-分类"
Get-ChildItem $dir -Directory | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    [PSCustomObject]@{
        Name = $_.Name
        Files = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
        SizeMB = [math]::Round($size / 1MB, 2)
    }
} | Format-Table -AutoSize
```

#### 搜索 import

```bash
# 搜索某个包的所有 import 位置
grep -rn "from ['\"]package-name['\"]" src/
grep -rn "require(['\"]package-name['\"]" src/

# 统计使用文件数
grep -rl "from ['\"]package-name['\"]" src/ | wc -l

# 搜索调用点（先找到 import 的变量名，再搜变量的使用）
grep -rn "import .* from ['\"]package-name['\"]" src/
# 然后用变量名继续搜索
```

#### 检查遗漏

```bash
# 1. 提取所有非 @types 依赖名
node -e "
  const p = require('./package.json');
  const all = {...p.dependencies, ...p.devDependencies};
  Object.keys(all).filter(k => !k.startsWith('@types/')).forEach(k => console.log(k));
" | sort > all-deps.txt

# 2. 提取已下载的项目名（需要手动对应 npm 包名 → 文件夹名）
# 3. diff 对比找差异
```

---

### B.3 避坑指南

| 坑 | 现象 | 解决方法 |
|----|------|---------|
| monorepo 重复下载 | markmap-lib 和 markmap-view 下了两个仓库，其实是同一个 | 先查 npm 页的 repository 字段，monorepo 只下主仓库 |
| 包名 ≠ 仓库名 | npm 叫 `mdict-js`，GitHub 叫 `js-mdict` | 查 repository 字段或 npm 页的链接 |
| 仓库搬家/改名 | clone 时 404 | 用 npm view 查最新地址，或 GitHub 会自动 redirect |
| 类型定义包太多 | @types/* 有十几个，占数量但没源码价值 | 统一跳过，在补充说明里列出即可 |
| 本地 file: 依赖 | `"sharp": "file:scripts/sharp-pack-stub"` | 不是上游依赖，跳过 |
| 中文路径编码问题 | MSBuild 编译 opencc 词典时乱码 | 避开或用其他方式处理（详见万维读书环境配置记录） |
| shallow clone 没历史 | 需要看历史/切版本 | `git fetch --unshallow` 或 `git checkout <tag>` |

---

## 01 - 分词与 NLP（7 个）

### ⭐ 1. node-rs（@node-rs/jieba）

- **仓库**：https://github.com/napi-rs/node-rs
- **大小**：16.6 MB / 231 文件
- **语言**：Rust + TypeScript (monorepo)
- **彩读中的包**：`@node-rs/jieba` ^2.0.1
- **彩读中使用文件数**：2 个
- **子包位置**：`packages/jieba/`

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `Jieba.withDict(dict)` | 用内置词典构造 jieba 实例 |
| `jieba.tag(text)` | 词性标注（返回 word + tag） |
| `jieba.cut(text, true)` | 全切分分词（用于词云） |
| `require("@node-rs/jieba/dict")` | 加载内置词典 Buffer |

**具体用途：**
- **Omni 词性标注引擎**（万维读书）：对章节文本进行词性标注，生成带偏移量的词元列表，供 8 维语义视觉通道使用
- **AI 词云分词**：对文本全切分分词，过滤无效 token，统计词频，生成词云数据
- 两个模块共享同一套 jieba 实例和词典，避免重复加载
- 采用运行时 `require()` 懒加载，优化启动速度

**上游依赖（已下载）：**
- **jieba-rs** — 底层 Rust 实现，@node-rs/jieba 是基于它的 napi-rs 绑定
- **jieba** — 算法源头，Python 原版

**下游协作：**
- 与 **better-sqlite3**（segmentCache.ts）协作：分词结果按章节缓存到 SQLite，避免重复计算
- 与 **d3-cloud / d3-scale** 协作：分词 + 词频统计 → 词云可视化
- 与 **omni 模块** 协作：词性标注结果 → 8 维视觉通道映射矩阵 → Monaco decorations 渲染

---

### 2. jieba（Python 原版）

- **仓库**：https://github.com/fxsjy/jieba
- **大小**：52.5 MB / 105 文件
- **语言**：Python
- **星标**：~35k
- **与彩读关系**：算法源头

**核心特性：**
- 三种分词模式：精确模式、全模式、搜索引擎模式
- 支持繁体分词、自定义词典、关键词提取（TF-IDF / TextRank）
- 词性标注、并行分词

**依赖层级：**
```
jieba (Python 原版) → jieba-rs (Rust 移植) → @node-rs/jieba (Node.js 绑定) → 彩读
```

---

### 3. jieba-rs（Rust 版）

- **仓库**：https://github.com/messense/jieba-rs
- **大小**：15.2 MB / 33 文件
- **语言**：Rust
- **与彩读关系**：间接依赖（@node-rs/jieba 的底层）

**核心特性：**
- jieba 分词算法的 Rust 实现
- 支持分词、词性标注、关键词提取
- 性能远超 Python 版本，且无运行时依赖

**依赖层级：**
```
jieba-rs → @napi-rs/jieba（napi-rs 包装）→ @node-rs/jieba（npm 包）→ 彩读
```

---

### 4. jieba-analysis（Java 版）

- **仓库**：https://github.com/huaban/jieba-analysis
- **大小**：22.1 MB / 28 文件
- **语言**：Java
- **与彩读关系**：同类参考

**核心特性：**
- jieba 的 Java 实现
- 支持精确模式和搜索引擎模式
- 适用于 Java 后端、Elasticsearch 插件等场景

---

### 5. THULAC（清华大学）

- **仓库**：https://github.com/thunlp/THULAC-Python
- **大小**：0.07 MB / 33 文件（模型需单独下载）
- **语言**：Python / C++
- **机构**：清华大学自然语言处理实验室
- **与彩读关系**：同类参考

**核心特性：**
- 中文词法分析工具包（分词 + 词性标注一体）
- 训练数据规模大，准确率高
- 支持多种分词粒度

---

### 6. pkuseg-python（北京大学）

- **仓库**：https://github.com/lancopku/pkuseg-python
- **大小**：4.5 MB / 31 文件
- **语言**：Python
- **机构**：北京大学语言计算与机器学习研究所
- **与彩读关系**：同类参考

**核心特性：**
- 多领域分词（支持不同领域模型切换）
- 新词识别能力强
- 提供词性标注功能

---

### 7. SnowNLP

- **仓库**：https://github.com/isnowfy/snownlp
- **大小**：55.1 MB / 39 文件
- **语言**：Python
- **与彩读关系**：同类参考（一站式方案）

**核心特性：**
- 一站式中文文本处理库
- 功能涵盖：分词、词性标注、情感分析、文本分类、关键词提取、自动摘要、拼音转换
- 内置训练好的模型，开箱即用

---

## 02 - 文档解析（7 个）

### ⭐ 1. OpenCC

- **仓库**：https://github.com/BYVoid/OpenCC
- **大小**：36.1 MB / 1345 文件
- **语言**：C++（Node.js 版为原生绑定）
- **彩读中的包**：`opencc` ^1.3.1
- **彩读中使用文件数**：1 个（`textConvertOpenCc.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `new OpenCC(configPath)` | 创建转换器实例（指定配置文件如 s2t.json / t2s.json） |
| `converter.convertSync(text)` | 同步转换文本 |

**具体用途：**
- 提供统一的繁简/异体字转换接口
- 支持多种配置：简→繁(s2t)、繁→简(t2s)、大陆→台湾(s2tw)、台湾→大陆(tw2s)、大陆→香港(s2hk)、香港→大陆(hk2s) 等共 16 种
- 转换器实例按 config 缓存复用，避免重复创建
- 打包后需处理 `app.asar.unpacked` 路径问题（原生模块 + 词典文件需要物理路径）

**上游依赖（已下载）：**
- 无（这是上游原生项目）

**下游协作：**
- 被 **书源引擎**（`legadoJavaApi.ts` 等）调用，用于书源内容的繁简转换
- 被 **文本工具模块** 调用，提供全局繁简转换能力
- 与 **iconv-lite** 同属"文本编码/转换"基础设施层

---

### ⭐ 2. js-mdict（mdict-js 上游）

- **仓库**：https://github.com/terasum/js-mdict
- **大小**：15.3 MB / 93 文件
- **语言**：TypeScript
- **彩读中的包**：`mdict-js` ^10.0.1（fork 自此项目）
- **彩读中使用文件数**：1 个（`mdictReader.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `new Mdict(filePath)` | 打开 MDX/MDD 词典文件 |
| `mdict.lookup(word)` | 查找单词释义 |

**具体用途：**
- MDX（词条文本）和 MDD（资源文件：图片/音频/CSS）词典格式读取
- 带实例缓存和资源 data URL 缓存
- 支持读取 MDX header 判断是否加密
- 与词典查找候选生成模块 `lookupCandidates` 配合

**上游依赖（已下载）：**
- 无直接依赖（mdict-js 内部处理解压，使用 pako 但自己打包了）

**下游协作：**
- 被 **词典模块**（`dictionary/`）调用，是彩读多词典支持的核心格式之一
- 与 **pako** 间接相关：其他词典格式（Slob/DictZip/BGL）用 pako 解压，mdict 内部自处理

---

### ⭐ 3. marked

- **仓库**：https://github.com/markedjs/marked
- **大小**：1.3 MB / 533 文件
- **语言**：JavaScript
- **彩读中的包**：`marked` ^16.0.1
- **彩读中使用文件数**：3 个

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `marked.use(extension)` | 挂载扩展（如 KaTeX） |
| `marked(markdown)` | 渲染 Markdown 为 HTML |
| `Lexer.lexInline(text)` | 行内词法分析（提取链接/图片等） |

**具体用途：**
- **AI 助手对话渲染**：Markdown 消息统一渲染入口，配置了 KaTeX 数学公式扩展
- **阅读器内链识别**：用 Lexer 解析 Markdown 中的链接、脚注、图片
- 作为 AI Markdown 的统一出口（`aiMarkdownMarkedSetup.ts`），确保各处使用同一套配置
- 内链/图片解析结果供 **Monaco 装饰层** 使用

**上游依赖（已下载）：**
- **katex**（通过 marked-katex-extension）—— 数学公式渲染扩展

**下游协作：**
- 与 **monaco-editor** 协作：解析结果作为装饰层数据源
- 与 **katex + marked-katex-extension** 组成完整 Markdown 数学公式渲染链路

---

### ⭐ 4. pdf.js（pdfjs-dist）

- **仓库**：https://github.com/mozilla/pdf.js
- **大小**：149.9 MB / 2560 文件
- **语言**：JavaScript
- **彩读中的包**：`pdfjs-dist` ^5.1.84
- **彩读中使用文件数**：2 个 + 类型声明

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `GlobalWorkerOptions.workerSrc = pdfjsWorker` | 设置 Worker 脚本路径 |
| `getDocument({ data, cMapUrl, standardFontDataUrl, wasmUrl, iccUrl }).promise` | 加载 PDF 文档 |
| `doc.getPage(num)` | 获取指定页 |
| `page.getTextContent()` | 提取页面文本块（带坐标） |
| `page.getAnnotations()` | 获取页面注释/链接 |
| `doc.getOutline()` | 获取文档大纲（书签目录） |
| `Jbig2Image` / `JpxImage` | JBIG2/JPEG2000 图像解码器（WASM） |

**具体用途：**
- 将 PDF 转换为内部 Markdown 格式，统一阅读器体验
- 提取文本位置信息用于行匹配与目录锚点
- 提取 PDF 内嵌图片（支持 JPX/JBIG2 等特殊编码，需 WASM 解码器）
- 解析 PDF 书签大纲作为书籍目录
- 使用 legacy build 兼容 Electron 渲染进程

**上游依赖（已下载）：**
- 无（这是 Mozilla 官方项目，自包含）

**下游协作：**
- 与 **电子书 Markdown 转换框架**（ebookMarkdownEmit 等）深度协作
- 最终输出统一 Markdown → **monaco-editor** 渲染
- 图像解码依赖 WASM 资源，需配置打包静态目录

---

### ⭐ 5. cheerio

- **仓库**：https://github.com/cheeriojs/cheerio
- **大小**：1.4 MB / 126 文件
- **语言**：JavaScript
- **彩读中的包**：`cheerio` ^1.0.2
- **彩读中使用文件数**：6 个（书源引擎核心）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `cheerio.load(html)` | 加载 HTML 并返回 `$` 对象 |
| `$(selector)` | CSS 选择器查询 |
| `$.attr(name)` / `$.text()` / `$.html()` | 属性/文本/HTML 获取 |
| `$.find(selector)` / `$.each(fn)` / `$.toArray()` | 子查询/遍历/转数组 |

**具体用途：**
- **书源规则引擎核心**：实现 Legado 的 CSS 选择器规则（Default 类型），是书源三引擎之首
- **HTML 内容提取**：从书源站点提取书名、作者、目录、正文等
- **登录态检测**：解析登录后页面判断登录状态
- **XPath 容错**：当 xmldom 解析失败时，用 cheerio 纠错重排后再试 xpath
- **Jsoup 兼容层**：模拟 Jsoup API 供书源 JS 规则调用

**上游依赖（已下载）：**
- 无直接依赖

**下游协作：**
- 与 **@xmldom/xmldom + xpath** 组成完整的书源解析引擎（CSS 选择器走 cheerio，XPath 走 xmldom+xpath）
- 与 **jsonpath-plus** 互补（HTML 书源走 cheerio，JSON 书源走 jsonpath-plus）
- 在 `analyzeRule.ts` 统一调度：根据规则类型自动选择提取引擎
- 与 **iconv-lite** 协作：iconv-lite 先解码 → cheerio 再解析

---

### ⭐ 6. @xmldom/xmldom

- **仓库**：https://github.com/xmldom/xmldom
- **大小**：4.6 MB / 169 文件
- **语言**：JavaScript
- **彩读中的包**：`@xmldom/xmldom` ^0.9.8
- **彩读中使用文件数**：1 个（`htmlXPath.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `new DOMParser({ onError })` | 创建 DOM 解析器（可自定义错误处理） |
| `parser.parseFromString(html, "text/html")` | 解析 HTML 字符串为 Document 对象 |
| `new XMLSerializer().serializeToString(node)` | 将 DOM 节点序列化为 HTML 字符串 |

**具体用途：**
- 为 XPath 查询构建标准 DOM 树（cheerio 的 DOM 不兼容标准 XPath）
- 序列化 XPath 匹配结果为 HTML 片段（供后续规则继续解析）
- 处理命名空间问题（XHTML 默认命名空间导致 XPath `//ul` 匹配失败）
- 大量预处理逻辑：转义裸 &、补命名空间声明、剥未声明前缀属性

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **xpath** 紧密配合：xmldom 建 DOM → xpath 执行查询
- 与 **cheerio** 容错配合：xmldom 解析失败时，先用 cheerio 纠错再重试
- 三者共同构成书源引擎的 HTML/XML 解析层

---

### ⭐ 7. xpath

- **仓库**：https://github.com/goto100/xpath
- **大小**：0.4 MB / 17 文件
- **语言**：JavaScript
- **彩读中的包**：`xpath` ^0.0.36
- **彩读中使用文件数**：1 个（`htmlXPath.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `xpath.select(expr, docNode)` | 执行 XPath 查询，返回节点数组/字符串/数值 |

**具体用途：**
- 执行书源的 XPath 规则（Legado AnalyzeByXPath），是书源三引擎之一
- 支持 JsoupXpath 扩展函数：`html()`、`outerHtml()`、`allText()`
- 处理命名空间问题：将 XPath 中的元素名改写为 `*[local-name()='name']` 形式

**上游依赖（已下载）：**
- **@xmldom/xmldom** — 提供标准 DOM 树

**下游协作：**
- 与 **@xmldom/xmldom** 组成 XPath 解析链路
- 与 **cheerio** 互补：常见场景（meta 标签、script 文本、id 子节点）走 cheerio 快速路径，复杂 XPath 走 xmldom+xpath
- 与 **jsonpath-plus** 一起作为书源三引擎的两大分支

---

## 03 - 文本处理（9 个）

### ⭐ 1. iconv-lite

- **仓库**：https://github.com/ashtuchkin/iconv-lite
- **大小**：1.1 MB / 113 文件
- **语言**：JavaScript（纯 JS，无原生依赖）
- **彩读中的包**：`iconv-lite` ^0.7.2
- **彩读中使用文件数**：5 个（广泛使用）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `iconv.decode(buffer, encoding)` | 将 Buffer 按指定编码解码为字符串 |
| `iconv.encode(text, encoding)` | 将字符串按指定编码编码为 Buffer |
| `iconv.encodingExists(encoding)` | 检查编码是否受支持 |

**具体用途：**
- **文本文件编码检测与解码**：配合 jschardet 检测文本文件编码，支持 GB18030/GBK/UTF-16/Shift_JIS/Big5 等
- **书源 HTTP 响应解码**：多级回退策略（Content-Type charset → 请求 charset → HTML meta → 字节探测）
- **Legado URI 编码**：模拟 Java 的 `encodeURI(str, charset)`，支持非 UTF-8 编码的 URL 编码
- 纯 JS 实现，无需编译，跨平台（彩读中无需 electron-rebuild）

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **jschardet** 紧密配合：jschardet 检测编码 → iconv-lite 实际解码
- 与 **书源引擎** 各模块广泛协作（analyzeUrl、downloadService、legadoJavaApi 等）
- 与 **opencc** 同属"文本编码/转换"基础设施层，但分工不同：iconv-lite 管字节编码，opencc 管字符集转换

---

### ⭐ 2. jschardet

- **仓库**：https://github.com/aadsm/jschardet
- **大小**：14.4 MB / 194 文件
- **语言**：JavaScript
- **彩读中的包**：`jschardet` ^3.1.4
- **彩读中使用文件数**：1 个（`detectTextEncoding.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `jschardet.detect(buffer)` | 检测 Buffer 的编码，返回 `{ encoding, confidence }` |

**具体用途：**
- 作为编码检测的核心引擎，对文本字节进行统计分析推断编码
- 检测结果需经过多层启发式校验（BOM 检测 → UTF-8 合法性 → GBK 字节结构 → 中文区域偏好等）
- 低置信度场景下，结合 locale（如 zh-CN）偏向 GB18030 回退

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **iconv-lite** 组成「检测 + 解码」完整链路
- 被 `detectTextEncoding.ts` 封装后，供文本文件导入和书源引擎使用

---

### ⭐ 3. better-sqlite3

- **仓库**：https://github.com/WiseLibs/better-sqlite3
- **大小**：10.5 MB / 121 文件
- **语言**：C++ + JavaScript（原生模块）
- **彩读中的包**：`better-sqlite3` ^11.7.0
- **彩读中使用文件数**：3 个数据库模块

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `new Database(filePath)` | 打开/创建 SQLite 数据库 |
| `db.pragma("journal_mode = WAL")` | 设置 WAL 模式（高性能并发） |
| `db.exec(sql)` | 执行 DDL / 批量 SQL |
| `db.prepare(sql).all()/.get()/.run()` | 预编译查询与执行 |
| `db.loadExtension(path)` | 加载 SQLite 扩展（用于 sqlite-vec） |
| `db.close()` | 关闭数据库 |

**具体用途：**
- **书源存储**：`book_sources` 表存储书源配置、`book_source_login` 登录态、`book_source_cache` 缓存、`book_source_cookies` Cookie
- **AI 向量库**：`chunks` 文本块、`threads`/`messages` 对话、`vec_embeddings` 向量索引（通过 sqlite-vec）
- **分词缓存**：`seg_chapter_freq` 按章节缓存分词词频，避免重复计算
- 三个数据库分别在不同目录（书源、RAG、分词缓存）

**上游依赖（已下载）：**
- 无直接依赖

**下游协作：**
- 与 **sqlite-vec** 通过 `loadExtension()` 紧密集成：better-sqlite3 是底座，sqlite-vec 是向量扩展
- 与 **@node-rs/jieba** 协作：segmentCache 存储分词结果
- 与 **@huggingface/transformers** 协作：vectorDb 存储向量嵌入
- 需 **electron-rebuild** 为 Electron 编译原生模块

---

### ⭐ 4. sqlite-vec

- **仓库**：https://github.com/asg017/sqlite-vec
- **大小**：2.7 MB / 325 文件
- **语言**：C + SQLite 扩展
- **彩读中的包**：`sqlite-vec` ^0.1.6
- **彩读中使用文件数**：1 个（间接使用，通过 better-sqlite3 加载）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `require("sqlite-vec").getLoadablePath()` | 获取扩展 .node 文件路径 |
| `CREATE VIRTUAL TABLE vec_embeddings USING vec0(embedding float[N])` | 创建向量虚拟表 |
| `vec_embeddings MATCH ? AND k = ?` | KNN 近邻搜索语法 |

**具体用途：**
- 为 SQLite 增加向量存储与近似最近邻搜索能力
- 支持向量维度动态调整（变更时重建向量表）
- KNN 搜索结果与 `id_mapping` 表 JOIN，关联到实际 chunk

**上游依赖（已下载）：**
- **better-sqlite3** — 通过 `loadExtension()` 加载，与 better-sqlite3 深度绑定

**下游协作：**
- 与 **@huggingface/transformers** 配合：transformers 生成向量 → sqlite-vec 存储与检索
- 是 RAG 功能的核心组件之一

---

### ⭐ 5. jszip

- **仓库**：https://github.com/Stuk/jszip
- **大小**：24.5 MB / 200 文件
- **语言**：JavaScript
- **彩读中的包**：`jszip` ^3.10.2
- **彩读中使用文件数**：6 个

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `JSZip.loadAsync(buffer)` | 读取 ZIP 文件 |
| `zip.file(path).async("string"/"uint8array")` | 读取 ZIP 内文件 |
| `zip.folder(name)` | 操作 ZIP 内目录 |
| `zip.file(path, data)` | 写入文件到 ZIP |
| `zip.generateAsync({ type: "blob" })` | 生成 ZIP 文件 |

**具体用途：**
- **EPUB 解析**：读取 OPF/XHTML/图片等资源，解析目录与正文
- **FB2 解析**：处理 .fb2.zip 格式
- **配色导出**：将配色 JSON + 自定义背景纹理打包为 .zip
- **书籍打包**：导出完整阅读数据（书签、标注、进度等）为 .zip
- **角色卡打包**：导入/导出角色卡片集为 .zip

**上游依赖（已下载）：**
- 无

**下游协作：**
- 电子书解析链路中与 **Markdown 转换模块** 协作（解压 → 提取 → 转 Markdown → monaco 渲染）
- 导出类功能与各业务数据模块协作（配色、书籍、角色卡）
- 在 EPUB 场景与 **@xmldom/xmldom + xpath** 配合（解压后用 XPath 解析 OPF）

---

### ⭐ 6. pako

- **仓库**：https://github.com/nodeca/pako
- **大小**：3.1 MB / 116 文件
- **语言**：JavaScript
- **彩读中的包**：`pako` ^2.1.0
- **彩读中使用文件数**：4 个

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `pako.inflate(bytes)` | 原始 deflate 解压 |
| `pako.ungzip(bytes)` | gzip 格式解压 |
| `new pako.Inflate({ windowBits: -15 })` | 流式 Inflate（DictZip 分块随机访问） |

**具体用途：**
- **Slob 词典**（Aard 2 格式）：zlib 压缩的 blob 数据解压
- **DictZip**：流式分块解压，支持随机访问（不从头开始解压整个文件）
- **BGL 词典**（Babylon 格式）：gzip 偏移解压后解析块流
- **MOBI 电子书**：在渲染进程中处理 PalmDOC 等压缩记录

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与各词典/电子书格式解析模块深度协作（slobReader、dictZip、bglReader、parseMobi）
- DictZip 场景下与 Node.js 原生 `zlib` 互补（pako 处理流式分块，gunzipSync 处理整体）
- 与 **mdict-js** 互补：mdict 自己处理解压，pako 服务于其他三种格式

---

### ⭐ 7. js-beautify

- **仓库**：https://github.com/beautify-web/js-beautify
- **大小**：2.7 MB / 193 文件
- **语言**：JavaScript
- **彩读中的包**：`js-beautify` ^1.15.4
- **彩读中使用文件数**：1 个（`formatBookSourceFieldText.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `jsBeautify.js(code, options)` | 格式化 JavaScript 代码 |

**具体用途：**
- 书源字段编辑器的代码格式化功能
- 支持 Legado 风格的 `<js>` / `@js:` / `@webjs:` 内嵌代码美化
- 与 legado-E 的 CodeEditViewModel.webFormatCode 选项对齐
- JSON 字段用原生 `JSON.stringify`，JS/规则字段用 js-beautify

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **monaco-editor** 配合：在 Monaco 编辑器中调用格式化
- 服务于书源编辑器模块

---

### ⭐ 8. jsonpath-plus

- **仓库**：https://github.com/JSONPath-Plus/JSONPath
- **大小**：1.9 MB / 136 文件
- **语言**：JavaScript
- **彩读中的包**：`jsonpath-plus` ^10.3.0
- **彩读中使用文件数**：2 个

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `JSONPath({ path, json, wrap, ... })` | 执行 JSONPath 查询 |

**具体用途：**
- 解析 JSON 类型书源的提取规则（书源三引擎之一）
- 支持 Legado 的 `$.` 前缀 JSONPath 语法
- 与 CSS/XPath 规则并列，作为书源规则引擎的三大提取方式之一

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **cheerio**（HTML 提取）、**xpath**（XML 提取）互补
- 在 `analyzeRule.ts` 统一调度：根据规则类型自动选择提取引擎
- JSON 书源场景下：HTTP 请求 → 得到 JSON → jsonpath-plus 提取数据

---

### ⭐ 9. tldts

- **仓库**：https://github.com/remusao/tldts
- **大小**：1.7 MB / 125 文件
- **语言**：TypeScript
- **彩读中的包**：`tldts` ^6.1.71
- **彩读中使用文件数**：1 个（`cookieManager.ts`）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `getDomain(hostname)` | 获取可注册域名（eTLD+1，如 `example.com`） |

**具体用途：**
- **Cookie 按域归档**：Cookie 按可注册域（eTLD+1）存储，子域名共享登录态
- 解决登录发生在 `accounts.example.com` 但业务在 `www.example.com` 时的 Cookie 共享问题
- IP / localhost 等无可注册域时退回原始主机名

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **tough-cookie**（未单独下载）配合：tldts 提取可注册域 → tough-cookie 管理 Cookie Jar
- 为书源引擎的网络请求提供 Cookie 管理基础设施

---

## 04 - 编辑器与可视化（7 个）

### ⭐ 1. monaco-editor

- **仓库**：https://github.com/microsoft/monaco-editor
- **大小**：20.6 MB / 994 文件
- **语言**：TypeScript
- **彩读中的包**：`monaco-editor` ^0.55.1
- **彩读中使用文件数**：26+ 个（阅读器核心基础设施）

**核心 API（彩读实际调用，按功能分组）：**

| 分类 | 代表 API | 用途 |
|------|---------|------|
| 编辑器创建 | `monaco.editor.create()` | 创建编辑器实例 |
| 主题与语言 | `defineTheme()`, `languages.register()` | 自定义主题与语言（txtr 文本高亮） |
| 模型操作 | `ITextModel`, `setValue()`, `getLineContent()` | 文本模型读写 |
| **装饰层** | `deltaDecorations()`, `DecorationOptions` | 高亮、标注、内联图片等装饰 |
| 视口 | `revealLineInCenter()`, `getVisibleRanges()` | 视口控制与查询 |
| **ViewZones** | `changeViewZones()` | 行内图片占位（ViewZone 机制） |
| 事件 | `onDidChangeCursorPosition()`, `onMouseDown()` | 编辑器事件监听 |
| Emitter | `new Emitter<T>()` | 自定义事件发射器 |
| 搜索 | `setSearchRangeProvider()` | 搜索锚点 |
| Diff Editor | `createDiffEditor()` | 智能排版对比视图 |

**具体用途：**
- **阅读器核心**：整个阅读界面基于 Monaco 构建，利用其强大的装饰层、ViewZone、滚动定位等能力
- **自定义文本高亮**：Monarch 语法定义（txtrTextMonarch, txtrHighlightMonarch）实现彩色标注
- **章节粘性滚动**：章节标题吸顶效果（chapterStickyScroll）
- **行内图片**：通过 ViewZone 机制在文本中插入图片（readerImageViewZones）
- **搜索/标注/批注**：基于装饰层实现
- **书源编辑器**：书源规则编辑、JSON/JS 语法高亮
- **智能排版对比**：Diff Editor 对比排版前后差异
- **万维读书 Omni 渲染**：利用 decorations 实现 8 维视觉通道

**上游依赖（已下载）：**
- 无（这是 VS Code 同款核心，自包含）

**下游协作：**
- 作为整个阅读器的 UI 基础设施，与几乎所有阅读器模块协作
- 书源编辑器场景与 **js-beautify** 配合（代码格式化）
- Omni 渲染场景基于装饰层实现词性/语义可视化（**@node-rs/jieba** → omni 映射 → **monaco decorations**）
- 内链/图片场景与 **marked** 配合（marked Lexer 解析 → Monaco 装饰层）
- 词云/思维导图作为独立视图，与 Monaco 同屏展示

---

### ⭐ 2. transformers.js（@huggingface/transformers）

- **仓库**：https://github.com/xenova/transformers.js
- **大小**：3.5 MB / 747 文件
- **语言**：JavaScript / TypeScript
- **彩读中的包**：`@huggingface/transformers` ^3.8.1
- **彩读中使用文件数**：1 个（Worker 动态 import）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `pipeline("feature-extraction", modelId, options)` | 创建特征提取（向量化）管线 |
| `pipeline(text, { pooling: "mean", normalize: true })` | 对文本进行向量化 |
| `env.allowRemoteModels` | 允许从远程下载模型 |
| `env.cacheDir` | 设置模型缓存目录 |
| `env.backends.onnx.executionProviders` | 设置 ONNX 执行提供者（CPU） |
| `env.useFSCache` / `env.useBrowserCache` | 缓存策略配置 |
| `env.remoteHost` | 自定义模型下载镜像源 |

**具体用途：**
- **本地嵌入模型**：在本地运行文本向量化模型，生成向量供 RAG 检索使用
- **Worker 线程运行**：在 Node.js Worker 线程中加载和推理，不阻塞主进程
- **模型缓存管理**：支持本地文件系统缓存，可配置缓存目录
- **可中断**：支持嵌入请求中止
- 模型文件首次使用时从 HuggingFace 下载（可配置镜像源）

**上游依赖（已下载）：**
- 无（onnxruntime 未单独下载，作为 transformers 的内部依赖）

**下游协作：**
- 与 **better-sqlite3 + sqlite-vec** 组成完整 RAG 链路：transformers 生成向量 → sqlite-vec 存储与检索
- 与 **@node-rs/jieba** 分词互补（jieba 用于传统词云分词，transformers 用于语义向量化）
- 万维读书扩展点：未来的 POS 细标注 / NER 角色识别

---

### ⭐ 3. d3（d3-scale）

- **仓库**：https://github.com/d3/d3
- **大小**：1.8 MB / 175 文件
- **语言**：JavaScript
- **彩读中的包**：`d3-scale` ^4.0.2（D3 的一个子模块，非全量 d3）
- **彩读中使用文件数**：1 个（词云组件）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `scaleLinear().domain().range()` | 线性比例尺（词频→字号映射） |
| `scaleOrdinal().domain().range()` | 序数比例尺（词→颜色映射） |

**具体用途：**
- 词频到字号的线性映射（词频越高，字号越大）
- 多套预设配色方案（通过 scaleOrdinal 实现词语 → 颜色映射）
- 彩读只使用了 d3-scale 子模块，没有引入完整的 d3

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 **d3-cloud** 配合：d3-cloud 计算布局位置，d3-scale 计算字号和颜色
- 数据来源：主进程 **@node-rs/jieba** 分词 + 词频统计

---

### ⭐ 4. d3-cloud

- **仓库**：https://github.com/jasondavies/d3-cloud
- **大小**：0.04 MB / 8 文件
- **语言**：JavaScript
- **彩读中的包**：`d3-cloud` ^1.2.7
- **彩读中使用文件数**：1 个（词云组件）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `cloud().words(words).size([w,h]).font(font).fontSize(fn).rotate(fn).on("end", callback)` | 创建词云布局并计算每个词的位置/大小/角度 |

**具体用途：**
- AI 词云的布局计算引擎
- 支持自定义字体、角度布局模式、配色方案
- 只负责布局计算，渲染由 Canvas 2D 完成

**上游依赖（已下载）：**
- **d3-scale** — 提供字号和颜色的比例尺计算

**下游协作：**
- 数据来源：主进程 **@node-rs/jieba** 分词 + 词频统计
- 渲染层：Canvas 2D 绘制（d3-cloud 负责布局计算）
- 两者共同构成彩读的词云功能

---

### ⭐ 5. markmap

- **仓库**：https://github.com/markmap/markmap
- **大小**：0.5 MB / 130 文件
- **语言**：TypeScript
- **彩读中的包**：`markmap-lib` ^0.18.3、`markmap-view` ^0.18.3（拆分为多个子包）
- **彩读中使用文件数**：1 个（思维导图组件）+ 1 个 AI 工具定义

**核心 API（彩读实际调用）：**

| API | 所属包 | 用途 |
|-----|--------|------|
| `new Transformer()` | markmap-lib | 创建 Markdown → 导图数据转换器 |
| `transformer.transform(markdown)` | markmap-lib | 将 Markdown 转换为导图树结构 |
| `Markmap.create(svg, options, data)` | markmap-view | 在 SVG 中渲染思维导图 |
| `markmap.setData(root)` | markmap-view | 更新导图数据 |
| `markmap.fit(maxScale)` | markmap-view | 自适应缩放 |
| `walkTree(node, callback)` | markmap-common | 遍历导图树 |

**具体用途：**
- AI 生成的思维导图可视化（知识图、章节概括、人物关系等）
- 支持侧栏预览（缩略图）和全屏交互
- 支持节点展开/折叠、缩放平移
- 主题样式适配（深浅色模式）

**上游依赖（已下载）：**
- 无（自包含 SVG 渲染）

**下游协作：**
- 数据来源：AI 助手生成 Markdown 格式的导图内容
- 三子包分工：markmap-common（工具函数）、markmap-lib（Markdown 解析）、markmap-view（SVG 渲染）

---

### ⭐ 6. sortablejs

- **仓库**：https://github.com/SortableJS/Sortable
- **大小**：1.2 MB / 69 文件
- **语言**：JavaScript
- **彩读中的包**：`sortablejs` ^1.15.6
- **彩读中使用文件数**：2 个（两个组合式函数）

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `Sortable.create(el, options)` | 创建可排序实例 |
| `sortable.destroy()` | 销毁实例 |
| `sortable.option("disabled", bool)` | 动态启用/禁用 |
| `onStart` / `onEnd` 事件 | 拖拽开始/结束回调 |
| `handle` 选项 | 指定拖动手柄 |
| `filter` 选项 | 指定不可拖动的元素 |
| `animation` 选项 | 动画时长 |

**具体用途：**
- **通用列表排序**：书源列表、设置项等表格行拖拽重排
- **角色卡网格排序**：角色卡片网格拖拽重排，带 3D 卡片翻面交互、释放动画
- 支持手柄拖动、过滤元素、动态启用/禁用

**上游依赖（已下载）：**
- 无

**下游协作：**
- 与 Vue 3 组合式 API 集成（useSortableReorder, useCharacterRosterReorder）
- 角色卡场景与 3D 翻面动画模块协作

---

### 7. wordcloud2.js

- **仓库**：https://github.com/timdream/wordcloud2.js
- **大小**：0.3 MB / 25 文件
- **语言**：JavaScript
- **与彩读关系**：同类参考

**核心特性：**
- HTML5 Canvas 词云生成
- 支持中文、各种形状（圆形、心形、星形等）
- 纯 Canvas 实现，无需依赖其他库

**与彩读的对比：**
- 彩读用 d3-cloud（布局计算）+ 自建 Canvas 渲染
- wordcloud2.js 是一体式方案，功能更丰富但定制性稍差

---

## 05 - 数学公式（2 个）

### ⭐ 1. KaTeX

- **仓库**：https://github.com/KaTeX/KaTeX
- **大小**：28.3 MB / 721 文件
- **语言**：JavaScript
- **彩读中的包**：`katex` ^0.16.21
- **彩读中使用方式**：通过 `marked-katex-extension` 间接使用 + 直接引入 CSS

**核心 API（彩读实际调用）：**

| API | 用途 |
|-----|------|
| `markedKatex({ throwOnError: false })` | 配置 KaTeX 扩展并挂载到 marked |

**具体用途：**
- 渲染 AI 助手中的数学公式
- 支持行内公式 `$…$` 和块级公式 `$$…$$`
- 公式错误时静默降级（throwOnError: false），不影响整体渲染
- CSS 在 AiMarkdown.vue 组件中全局引入

**上游依赖（已下载）：**
- **marked** — 通过 marked-katex-extension 集成
- **marked-katex-extension** — 桥接 marked 和 katex 的扩展

**下游协作：**
- 通过 **marked-katex-extension** 与 **marked** 深度集成
- 服务于 AI Markdown 渲染链路

---

### ⭐ 2. marked-katex-extension

- **仓库**：https://github.com/UziTech/marked-katex-extension
- **大小**：1.5 MB / 25 文件
- **语言**：JavaScript
- **彩读中的包**：`marked-katex-extension` ^5.1.4
- **彩读中使用方式**：通过 `marked.use()` 挂载

**具体用途：**
- marked 的 KaTeX 扩展，让 Markdown 支持数学公式
- 识别行内 `$…$` 和块级 `$$…$$` 公式语法
- 将公式渲染委托给 katex 执行

**上游依赖（已下载）：**
- **marked** — 扩展的宿主
- **katex** — 实际的公式渲染引擎

**下游协作：**
- 桥接 marked 和 katex，组成完整的 Markdown 数学公式渲染链路

---

## 核心功能链路图

### 书源引擎链路

```
HTTP 请求 → iconv-lite 解码 → cheerio / xpath / jsonpath-plus 解析 → 文本提取
                  ↑                    ↑           ↑
              jschardet           @xmldom/xmldom
            (编码检测)            (DOM 构建)
```

**涉及项目（6 个）：** iconv-lite、jschardet、cheerio、@xmldom/xmldom、xpath、jsonpath-plus

---

### AI RAG 链路

```
文本 → @node-rs/jieba 分词 → better-sqlite3 缓存
                              ↓
文本 → @huggingface/transformers 向量化 → sqlite-vec 向量检索 → RAG 上下文
                                          ↑
                                    better-sqlite3
                                    (数据库基础)
```

**涉及项目（4 个）：** @node-rs/jieba、@huggingface/transformers、better-sqlite3、sqlite-vec

---

### 电子书解析链路

```
EPUB → jszip 解压 → XHTML/资源提取 → Markdown 转换 → monaco-editor 渲染
PDF  → pdfjs-dist → 文本/图片提取  → Markdown 转换 → monaco-editor 渲染
MOBI → pako 解压  → 文本提取       → Markdown 转换 → monaco-editor 渲染
```

**涉及项目（4 个）：** jszip、pdfjs-dist、pako、monaco-editor

---

### 词典格式链路

```
MDX → mdict-js → 词条查询
Slob / DictZip / BGL → pako 解压 → 词条解析
```

**涉及项目（2 个）：** mdict-js (js-mdict)、pako

---

### 可视化链路

```
文本 → @node-rs/jieba 分词 → 词频统计 → d3-cloud + d3-scale → 词云
Markdown → markmap-lib 解析 → markmap-view → 思维导图
```

**涉及项目（3 个）：** @node-rs/jieba、d3-cloud、d3-scale、markmap

---

### 万维读书 Omni 链路（新增）

```
章节文本 → @node-rs/jieba 词性标注 → omni 映射矩阵 → Monaco decorations → 8 维视觉效果
              ↑
          better-sqlite3
          (分词缓存)
```

**涉及项目（2 个）：** @node-rs/jieba、monaco-editor

---

### Markdown + 数学公式链路

```
Markdown 文本 → marked 解析 → katex (via marked-katex-extension) → 公式渲染 → HTML
```

**涉及项目（3 个）：** marked、katex、marked-katex-extension

---

## 模块协作矩阵

| 中心模块 | 直接协作的依赖（已下载） | 核心关系 |
|---------|----------------------|---------|
| **better-sqlite3** | sqlite-vec, @node-rs/jieba, @huggingface/transformers | 数据库底座，向量/分词/对话都存在这里 |
| **monaco-editor** | marked, katex, js-beautify, @node-rs/jieba(omni) | 阅读器核心，所有文本渲染的基础设施 |
| **iconv-lite** | jschardet, opencc, cheerio, xpath, jsonpath-plus | 编码解码是书源引擎的第一步 |
| **cheerio** | @xmldom/xmldom, xpath, jsonpath-plus, iconv-lite | 书源解析三引擎的主力（CSS 选择器） |
| **marked** | katex (via marked-katex-extension) | Markdown 渲染的核心 |
| **@node-rs/jieba** | better-sqlite3, d3-cloud, monaco-editor(omni) | 分词能力服务于词云、RAG、Omni 三个场景 |
| **sqlite-vec** | better-sqlite3, @huggingface/transformers | 向量检索的核心，依赖 better-sqlite3 加载 |
| **@huggingface/transformers** | better-sqlite3, sqlite-vec | 本地 AI 向量化，服务于 RAG |
| **pako** | mdict-js(间接), jszip(互补) | 解压服务于多种词典和电子书格式 |
| **jszip** | @xmldom/xmldom, xpath, monaco-editor | ZIP 解压服务于 EPUB/FB2/导出功能 |

---

## 06 - 框架与构建（10 个）

> Electron 桌面框架、Vue 前端框架、Vite 构建工具及相关插件

### ⭐ 1. electron

- **仓库**：https://github.com/electron/electron
- **大小**：31.7 MB / 3094 文件
- **语言**：C++ + JavaScript
- **彩读中的包**：`electron` 35.4.0
- **作用**：桌面应用框架，使用 Chromium + Node.js 构建跨平台桌面应用
- **在彩读中的地位**：整个应用的运行时底座，主进程/渲染进程/预加载脚本的分层架构都基于 Electron
- **相关模块**：`src/main/`（主进程）、`src/preload/`（预加载）、`src/renderer/`（渲染进程）

---

### ⭐ 2. @electron/rebuild

- **仓库**：https://github.com/electron/rebuild
- **大小**：11.7 MB / 97 文件
- **语言**：TypeScript
- **彩读中的包**：`@electron/rebuild` ^4.0.4
- **作用**：Electron 原生模块重编译工具，将 Node.js 原生模块重新编译为 Electron 兼容版本
- **在彩读中的使用**：postinstall 和 build 阶段自动执行，为 better-sqlite3 和 opencc 编译 Electron 版本
- **调用方式**：`electron-rebuild -f -w better-sqlite3,opencc`

---

### ⭐ 3. TypeScript

- **仓库**：https://github.com/microsoft/TypeScript
- **大小**：213.3 MB / 66749 文件
- **语言**：TypeScript
- **彩读中的包**：`typescript` ^5.8.2
- **作用**：TypeScript 语言编译器，将 TS 代码编译为 JavaScript
- **在彩读中的使用**：vue-tsc 的底层编译器，提供类型检查和代码编译能力
- **地位**：整个项目类型安全的基础

---

### ⭐ 4. vue（vue-core）

- **仓库**：https://github.com/vuejs/core
- **大小**：6.3 MB / 702 文件
- **语言**：TypeScript
- **彩读中的包**：`vue` ^3.5.31
- **作用**：Vue 3 响应式前端框架
- **在彩读中的地位**：渲染进程 UI 的核心框架，所有组件（阅读器、侧栏、设置页等）都基于 Vue 3 组合式 API
- **特点**：Composition API、响应式系统、虚拟 DOM

---

### ⭐ 5. vite

- **仓库**：https://github.com/vitejs/vite
- **大小**：16.8 MB / 2837 文件
- **语言**：TypeScript
- **彩读中的包**：`vite` ^6.2.3
- **作用**：下一代前端构建工具，基于 ESM 原生模块
- **在彩读中的使用**：渲染进程的开发服务器和生产构建
- **特点**：极速 HMR、Rollup 打包、插件生态

---

### ⭐ 6. @vitejs/plugin-vue

- **仓库**：https://github.com/vitejs/vite-plugin-vue
- **大小**：1.0 MB / 290 文件
- **语言**：TypeScript
- **彩读中的包**：`@vitejs/plugin-vue` ^5.2.3
- **作用**：Vite 的 Vue 单文件组件（SFC）支持插件
- **在彩读中的使用**：处理 .vue 文件的编译，包括 template/script/style 解析

---

### ⭐ 7. vue-tsc（vue-language-tools）

- **仓库**：https://github.com/vuejs/language-tools
- **大小**：2.3 MB / 1009 文件
- **语言**：TypeScript
- **彩读中的包**：`vue-tsc` ^2.2.8
- **作用**：Vue 3 TypeScript 类型检查工具（基于 Volar）
- **在彩读中的使用**：`npm run typecheck` 命令，对 Vue 组件进行类型检查
- **子包**：包含 vue-tsc、@vue/language-server、@vue/typescript-plugin 等

---

### ⭐ 8. electron-builder

- **仓库**：https://github.com/electron-userland/electron-builder
- **大小**：18.4 MB / 1327 文件
- **语言**：TypeScript (monorepo)
- **彩读中的包**：`electron-builder` ^26.0.12
- **作用**：Electron 应用打包和发布工具
- **在彩读中的使用**：打包 Windows/macOS/Linux 安装包，支持自动更新
- **monorepo 包含**：electron-builder、electron-updater、builder-util 等
- **子包位置**：`packages/electron-builder/`、`packages/electron-updater/`

---

### ⭐ 9. electron-vite

- **仓库**：https://github.com/alex8088/electron-vite
- **大小**：0.2 MB / 51 文件
- **语言**：TypeScript
- **彩读中的包**：`electron-vite` ^3.0.0
- **作用**：Electron 专用的 Vite 构建工具，同时处理主进程/预加载/渲染进程
- **在彩读中的使用**：统一构建配置，支持热重载和多目标打包

---

### ⭐ 10. vite-plugin-monaco-editor

- **仓库**：https://github.com/vdesjs/vite-plugin-monaco-editor
- **大小**：12.5 MB / 29 文件
- **语言**：TypeScript
- **彩读中的包**：`vite-plugin-monaco-editor` ^1.1.0
- **作用**：Vite 的 Monaco Editor 插件，自动处理 Monaco 的 Web Worker 和语言文件打包
- **在彩读中的使用**：将 Monaco 的 worker 文件和语言服务正确打包到构建产物
- **备注**：彩读中有 patch 修复此插件的问题（patch-vite-plugin-monaco-rmdir.mjs）

---

## 07 - 网络与协议（3 个）

### ⭐ 1. ws

- **仓库**：https://github.com/websockets/ws
- **大小**：0.5 MB / 64 文件
- **语言**：JavaScript
- **彩读中的包**：`ws` ^8.18.1
- **作用**：WebSocket 客户端/服务器实现（Node.js 端）
- **在彩读中的使用**：书源引擎的 WebSocket 支持，用于实时通信类书源
- **特点**：高性能、纯 JS 实现、符合标准

---

### ⭐ 2. tough-cookie

- **仓库**：https://github.com/salesforce/tough-cookie
- **大小**：0.8 MB / 246 文件
- **语言**：JavaScript
- **彩读中的包**：`tough-cookie` ^5.1.2
- **作用**：RFC 6265 标准的 Cookie 管理库
- **在彩读中的使用**：书源引擎的 Cookie 管理（cookieManager.ts）
- **协作依赖**：与 **tldts** 配合，按 eTLD+1 归档 Cookie

---

### ⭐ 3. proxy-agents（含 socks-proxy-agent）

- **仓库**：https://github.com/TooTallNate/proxy-agents
- **大小**：0.9 MB / 203 文件
- **语言**：TypeScript (monorepo)
- **彩读中的包**：`socks-proxy-agent` ^8.0.5
- **作用**：SOCKS 代理客户端，也包含 HTTP/HTTPS/PAC 等多种代理实现
- **在彩读中的使用**：书源网络请求的代理支持
- **monorepo 包含**：socks-proxy-agent、https-proxy-agent、http-proxy-agent、pac-proxy-agent 等

---

## 08 - 多媒体处理（3 个）

### ⭐ 1. sharp

- **仓库**：https://github.com/lovell/sharp
- **大小**：48.4 MB / 798 文件
- **语言**：C + JavaScript（基于 libvips 的原生模块）
- **彩读中的包**：`sharp` ^0.34.5
- **作用**：高性能图片处理库（调整大小、裁剪、格式转换等）
- **在彩读中的使用**：书籍封面处理、图片压缩、格式转换
- **特点**：基于 libvips，性能远超纯 JS 方案
- **备注**：彩读中有 patch 处理嵌套 sharp 的 stub 问题（patch-nested-sharp-stub.mjs）

---

### ⭐ 2. heic-convert

- **仓库**：https://github.com/catdad-experiments/heic-convert
- **大小**：0.02 MB / 19 文件
- **语言**：JavaScript
- **彩读中的包**：`heic-convert` ^2.2.1
- **作用**：HEIC/HEIF 图片格式转换（苹果的高效图片格式）
- **在彩读中的使用**：支持苹果设备拍摄的 HEIC 格式图片导入和显示

---

### ⭐ 3. @caitun/speex

- **仓库**：https://github.com/caitunai/speex
- **大小**：0.7 MB / 116 文件
- **语言**：C + JavaScript（WebAssembly）
- **彩读中的包**：`@caitun/speex` ^1.0.0
- **作用**：Speex 语音编解码器的 WebAssembly 实现
- **在彩读中的使用**：音频相关功能，支持 Speex 格式的语音播放
- **特点**：纯 WASM 实现，无需原生依赖

---

## 09 - 其他工具（1 个）

### ⭐ 1. font-list

- **仓库**：https://github.com/oldj/node-font-list
- **大小**：0.1 MB / 25 文件
- **语言**：JavaScript + 原生脚本
- **彩读中的包**：`font-list` ^2.0.2
- **作用**：获取系统已安装字体列表（跨平台）
- **在彩读中的使用**：阅读器字体选择器，让用户选择系统字体作为阅读字体
- **支持平台**：Windows、macOS、Linux

---

## 补充说明

### 依赖覆盖完整性

彩读 package.json 中共有 **12 个 dependencies + 30 个 devDependencies = 42 个包**。

其中 **33 个非 @types 包已全部下载**，未下载的仅有 **9 个 `@types/*` 类型定义包**（纯声明文件，无源码价值）：

| 未下载的 @types 包 | 对应项目 |
|-----------------|---------|
| @types/better-sqlite3 | better-sqlite3 |
| @types/d3-cloud | d3-cloud |
| @types/d3-scale | d3-scale |
| @types/js-beautify | js-beautify |
| @types/node | Node.js 内置 |
| @types/pako | pako |
| @types/sortablejs | sortablejs |
| @types/ws | ws |
| @types/electron | electron（未在 package.json 显式列出） |

### monorepo 说明

以下包属于 monorepo 的子包，已通过主仓库一并下载：

| npm 包名 | 所在主仓库 | 子包位置 |
|---------|-----------|---------|
| @node-rs/jieba | node-rs | packages/jieba/ |
| electron-updater | electron-builder | packages/electron-updater/ |
| markmap-lib | markmap | packages/markmap-lib/ |
| markmap-view | markmap | packages/markmap-view/ |
| socks-proxy-agent | proxy-agents | packages/socks-proxy-agent/ |
| d3-scale | d3 | packages/d3-scale/ |

### 关于版本

- 所有仓库均为 `--depth 1` 浅克隆，只包含最新版本代码
- 如需特定版本，可进入对应目录执行 `git checkout <tag>`

### 关于许可证

各项目许可证不同，使用时请遵守各自的开源协议：

| 项目 | 许可证 |
|------|--------|
| jieba / jieba-rs / node-rs | MIT |
| OpenCC | Apache-2.0 |
| THULAC / pkuseg / SnowNLP | MIT |
| iconv-lite / js-beautify / jschardet | MIT |
| better-sqlite3 / sqlite-vec | MIT |
| marked / cheerio / xmldom / xpath | MIT |
| pdf.js | Apache-2.0 |
| jszip | MIT 或 GPLv3（双许可） |
| pako | MIT |
| monaco-editor | MIT |
| transformers.js | Apache-2.0 |
| d3 / d3-cloud | BSD-3-Clause |
| markmap | MIT |
| sortablejs | MIT |
| KaTeX / marked-katex-extension | MIT |
| js-mdict | AGPL-3.0（**注意商用限制**） |
| jsonpath-plus | MIT |
| tldts | MIT |
