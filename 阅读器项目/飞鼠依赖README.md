# FlyingMouse Format 飞鼠格式 全部依赖项目库

> FlyingMouse Format（飞鼠格式）项目中引用的所有上游开源项目
> 基底项目：FlyingMouse Format v0.7.10（Electron 43 + Express 本地服务）
> 项目仓库：https://github.com/LaoFeng-mouse/flyingmouse-format
> 整理日期：2026-09-29
> 总计：**23 个源码项目 + 4 个数据包，约 463 MB**
> 分类：9 大类
> 分析方法：基于 package.json 全量依赖提取 + GitHub 仓库溯源

---

## 项目简介

FlyingMouse Format（飞鼠格式）是 Windows 桌面离线文件格式转换工具，支持图片/文档/表格/PPT/PDF/音视频/WPS/电子书等多种格式互转。内置 FFmpeg、LibreOffice、Poppler、Tesseract 等引擎。

**技术栈**：Electron 43 + Express 本地服务 + 原生鼠鼠 UI

---

## 依赖覆盖完整性

package.json 中共有 **26 个 dependencies + 2 个 devDependencies = 28 个包**。

| 状态 | 数量 | 说明 |
|------|------|------|
| ✅ 已下载源码 | **23 个** | 有公开 GitHub 仓库的项目 |
| 📦 数据包（未下载） | 3 个 | @tesseract.js-data/chi_sim / eng / tha（训练数据，非源码） |
| 🔒 无公开仓库 | 1 个 | @miconvert/ofd-to-pdf（npm 包，未找到公开 GitHub） |
| @types 类型定义 | 0 个 | 本项目无 @types 依赖 |

---

## 目录

- [01 - 文档解析](#01---文档解析6-个)
- [02 - 文档生成](#02---文档生成3-个)
- [03 - 格式转换](#03---格式转换3-个)
- [04 - OCR 与识别](#04---ocr-与识别13-个)
- [05 - 图像处理](#05---图像处理1-个)
- [06 - 数学公式](#06---数学公式1-个)
- [07 - 压缩与归档](#07---压缩与归档2-个)
- [08 - 框架与服务](#08---框架与服务4-个)
- [09 - 工具库](#09---工具库3-个)
- [核心转换链路图](#核心转换链路图)
- [与彩读 ColorTxt 依赖对比](#与彩读-colortxt-依赖对比)
- [补充说明](#补充说明)

---

## 01 - 文档解析（6 个）

### ⭐ 1. pdf.js（pdfjs-dist）

- **仓库**：https://github.com/mozilla/pdf.js
- **大小**：149.9 MB / 2560 文件
- **语言**：JavaScript
- **项目中的包**：`pdfjs-dist` ^6.2.108
- **作用**：PDF 文本提取、页数检测、PDF 分类（原生 vs 扫描）
- **使用模块**：pdfjs.js、pdf-classifier.js、pdf-table-extractor.js
- **安全限制**：`isEvalSupported: false`，只从自身 node_modules 加载

---

### ⭐ 2. @lezer/markdown

- **仓库**：https://github.com/lezer-parser/markdown
- **大小**：0.23 MB / 20 文件
- **语言**：JavaScript
- **项目中的包**：`@lezer/markdown` 1.6.3
- **作用**：Markdown 语法解析器（Lezer 语法树系统）
- **使用模块**：markdown-document.js、markdown-asset-references.js
- **备注**：Lezer 是 CodeMirror 6 的语法解析系统

---

### ⭐ 3. csv-parse

- **仓库**：https://github.com/adaltas/node-csv
- **大小**：8.79 MB / 618 文件
- **语言**：JavaScript (monorepo)
- **项目中的包**：`csv-parse` 7.0.2
- **作用**：CSV 格式解析，严格模式，锁定版本避免原型污染问题
- **使用模块**：text-conversion.js
- **子包位置**：packages/csv-parse/

---

### ⭐ 4. js-yaml

- **仓库**：https://github.com/nodeca/js-yaml
- **大小**：7.82 MB / 131 文件
- **语言**：JavaScript
- **项目中的包**：`js-yaml` ^4.3.1
- **作用**：YAML 格式解析与序列化
- **使用场景**：配置文件、字幕格式（ASS/SSA）相关处理

---

### ⭐ 5. marked

- **仓库**：https://github.com/markedjs/marked
- **大小**：1.28 MB / 533 文件
- **语言**：JavaScript
- **项目中的包**：`marked` 9.1.6
- **作用**：Markdown 解析与渲染
- **使用模块**：markdown-document.js、text-conversion.js
- **注意**：版本为 9.x，比彩读用的 14.x 旧

---

### ⭐ 6. parse5

- **仓库**：https://github.com/inikulin/parse5
- **大小**：3.6 MB / 180 文件
- **语言**：TypeScript
- **项目中的包**：`parse5` 7.3.0
- **作用**：符合 HTML 标准的解析器
- **使用模块**：xml-json.js、turndown 配合（HTML→Markdown 前的 DOM 构建）
- **特点**：WHATWG HTML 规范兼容，容错性强

---

## 02 - 文档生成（3 个）

### ⭐ 1. docx

- **仓库**：https://github.com/dolanmiu/docx
- **大小**：20.49 MB / 1232 文件
- **语言**：TypeScript
- **项目中的包**：`docx` 9.5.1
- **作用**：生成 Word DOCX 文档
- **使用模块**：text-docx.js、pdf-office-docx.js
- **特点**：纯 JS 生成 DOCX，无需 Office

---

### ⭐ 2. exceljs

- **仓库**：https://github.com/exceljs/exceljs
- **大小**：17.24 MB / 546 文件
- **语言**：JavaScript
- **项目中的包**：`exceljs` ^4.4.0
- **作用**：生成 Excel XLSX 工作簿
- **使用模块**：pdf-office-xlsx.js、pdf-table-extractor.js
- **特点**：支持样式、图表、公式，流式写入

---

### ⭐ 3. pdf-lib

- **仓库**：https://github.com/Hopding/pdf-lib
- **大小**：83.28 MB / 759 文件
- **语言**：TypeScript
- **项目中的包**：`pdf-lib` ^1.17.1
- **作用**：PDF 文档创建与修改（合并、拆分、加页、嵌入字体等）
- **使用模块**：pdf.js、pdf-table.js、ofd-convert.js
- **特点**：纯 JS 实现，无需原生依赖，支持修改现有 PDF

---

## 03 - 格式转换（3 个）

### ⭐ 1. mammoth

- **仓库**：https://github.com/mwilliamson/mammoth.js
- **大小**：0.84 MB / 124 文件
- **语言**：JavaScript
- **项目中的包**：`mammoth` ^1.12.0
- **作用**：DOCX → HTML / Markdown 转换，专注于语义转换（保留标题/列表/粗体等语义）
- **使用模块**：office-convert.js、text-conversion.js
- **特点**：忽略 Word 中的排版细节，保留文档语义结构

---

### ⭐ 2. turndown

- **仓库**：https://github.com/mixmark-io/turndown
- **大小**：0.31 MB / 29 文件
- **语言**：JavaScript
- **项目中的包**：`turndown` ^7.2.4
- **作用**：HTML → Markdown 转换
- **使用模块**：text-conversion.js（统一 ATX 标题 + Fenced 代码块 helper）
- **特点**：可配置转换规则，支持自定义插件

---

### ⭐ 3. @miconvert/ofd-to-pdf（无公开 GitHub）

- **npm 包**：`@miconvert/ofd-to-pdf` ^0.2.3
- **作用**：OFD（国标 GB/T 33190）→ PDF 纯 JS 转换
- **使用模块**：ofd-convert.js
- **说明**：仅支持转 PDF，不走 LibreOffice 路径
- **状态**：未找到公开 GitHub 仓库，仅在 npm 发布
- **npm 地址**：https://www.npmjs.com/package/@miconvert/ofd-to-pdf

---

## 04 - OCR 与识别（1+3 个）

### ⭐ 1. tesseract.js

- **仓库**：https://github.com/naptha/tesseract.js
- **大小**：37.58 MB / 118 文件
- **语言**：JavaScript
- **项目中的包**：`tesseract.js` ^7.0.0
- **作用**：纯 JS OCR 光学字符识别（基于 Tesseract 引擎 + WebAssembly）
- **使用模块**：ocr.js、pdf-classifier.js、ocr-merge.js
- **特点**：支持多种语言，浏览器/Node.js 通用，WASM 加速
- **asarUnpack**：tesseract.js-core 原生模块需解压

---

### 📦 训练数据包（非源码，未下载）

| 包名 | 说明 |
|------|------|
| `@tesseract.js-data/chi_sim` | 中文简体训练数据 |
| `@tesseract.js-data/eng` | 英文训练数据 |
| `@tesseract.js-data/tha` | 泰文训练数据 |

> 这些是 Tesseract 的 traineddata 模型文件（.traineddata.gz），属于数据资源而非源码项目。安装时通过 npm 下载。

---

## 05 - 图像处理（1 个）

### ⭐ 1. sharp

- **仓库**：https://github.com/lovell/sharp
- **大小**：48.35 MB / 798 文件
- **语言**：C + JavaScript（基于 libvips 的原生模块）
- **项目中的包**：`sharp` ^0.35.3
- **作用**：高性能图片处理（格式转换、缩放、裁剪、合并、压缩）
- **使用模块**：image-conversion.js、image.js、design-export.js、bmp-input.js、bmp-output.js
- **特点**：基于 libvips，性能远超纯 JS 方案
- **asarUnpack**：sharp 原生模块需解压
- **注意**：版本 0.35.x，比彩读用的 0.34.x 新

---

## 06 - 数学公式（1 个）

### ⭐ 1. KaTeX

- **仓库**：https://github.com/KaTeX/KaTeX
- **大小**：28.29 MB / 721 文件
- **语言**：JavaScript
- **项目中的包**：`katex` 0.18.7
- **作用**：数学公式渲染（LaTeX 语法）
- **使用模块**：markdown-math.js
- **注意**：版本 0.18.x，比彩读用的 0.16.x 新

---

## 07 - 压缩与归档（2 个）

### ⭐ 1. yauzl

- **仓库**：https://github.com/thejoshwolfe/yauzl
- **大小**：1.12 MB / 104 文件
- **语言**：JavaScript
- **项目中的包**：`yauzl` ^2.10.0
- **作用**：ZIP 文件读取（流式、低内存占用）
- **使用模块**：zip-util.js、ebook.js
- **特点**：专为读取设计，支持随机访问，内存效率高

---

### ⭐ 2. yazl

- **仓库**：https://github.com/thejoshwolfe/yazl
- **大小**：0.08 MB / 9 文件
- **语言**：JavaScript
- **项目中的包**：`yazl` ^3.3.1
- **作用**：ZIP 文件生成（流式输出）
- **使用模块**：zip-util.js
- **特点**：与 yauzl 同作者，读写配套

---

## 08 - 框架与服务（4 个）

### ⭐ 1. electron

- **仓库**：https://github.com/electron/electron
- **大小**：31.72 MB / 3094 文件
- **语言**：C++ + JavaScript
- **项目中的包**：`electron` ^43.1.0
- **作用**：桌面应用框架（Chromium + Node.js）
- **使用方式**：主入口 electron-main.js，含安全加固（contextIsolation + sandbox）
- **注意**：版本 43.x，比彩读用的 35.x 新很多

---

### ⭐ 2. electron-builder

- **仓库**：https://github.com/electron-userland/electron-builder
- **大小**：18.36 MB / 1327 文件
- **语言**：TypeScript (monorepo)
- **项目中的包**：`electron-builder` ^26.15.3
- **作用**：Electron 应用打包（NSIS / APPX / DMG）
- **子包**：包含 electron-updater 等
- **打包格式**：Windows NSIS + APPX，macOS DMG

---

### ⭐ 3. express

- **仓库**：https://github.com/expressjs/express
- **大小**：0.71 MB / 214 文件
- **语言**：JavaScript
- **项目中的包**：`express` ^4.19.2
- **作用**：本地 HTTP 服务框架
- **使用模块**：server.js（转换服务、上传下载路由、能力检测）
- **架构**：Electron 主进程启动 Express 本地服务，渲染进程通过 HTTP 与服务通信

---

### ⭐ 4. multer

- **仓库**：https://github.com/expressjs/multer
- **大小**：2.54 MB / 75 文件
- **语言**：JavaScript
- **项目中的包**：`multer` ^2.0.2
- **作用**：Express 文件上传中间件（处理 multipart/form-data）
- **使用模块**：server.js（文件上传路由）
- **协作**：与 express 配合，处理用户上传的待转换文件

---

## 09 - 工具库（3 个）

### ⭐ 1. mime-types

- **仓库**：https://github.com/jshttp/mime-types
- **大小**：0.04 MB / 15 文件
- **语言**：JavaScript
- **项目中的包**：`mime-types` ^2.1.35
- **作用**：MIME 类型查询（根据扩展名获取 MIME type，或反向）
- **使用场景**：文件上传、下载、格式检测
- **数据来源**：基于 mime-db 数据库

---

### ⭐ 2. sanitize-filename

- **仓库**：https://github.com/parshap/node-sanitize-filename
- **大小**：0.24 MB / 14 文件
- **语言**：JavaScript
- **项目中的包**：`sanitize-filename` ^1.6.3
- **作用**：文件名清理，移除或替换非法字符
- **使用模块**：save-converted-result.js、zip-util.js
- **安全意义**：防止路径遍历攻击，确保输出文件名安全

---

### ⭐ 3. sql.js

- **仓库**：https://github.com/sql-js/sql.js
- **大小**：0.43 MB / 72 文件
- **语言**：C + JavaScript（SQLite 编译为 WebAssembly）
- **项目中的包**：`sql.js` ^1.14.1
- **作用**：纯 WASM SQLite 数据库，无需原生依赖
- **使用模块**：store-engine-cache.js、store-engine-worker.js
- **特点**：Store 版 Office 缓存引擎，浏览器兼容
- **asarUnpack**：WASM 二进制需解压

---

## 核心转换链路图

### 文档转换主链路

```
用户上传文件 → multer → express 服务
                           ↓
                    格式检测 (mime-types)
                           ↓
            ┌──────────┬──────────┬──────────┐
            ↓          ↓          ↓          ↓
        PDF处理    Office处理    图片处理    文本处理
        (pdf.js)  (LibreOffice)  (sharp)  (text-conversion)
            ↓          ↓          ↓          ↓
        pdf-lib   mammoth      格式转换    turndown
        (PDF操作)  (DOCX→HTML)  (缩放/裁剪)  (HTML→MD)
            ↓                     ↓
        docx/exceljs           OCR 回退
        (生成DOCX/XLSX)      (tesseract.js)
                                       ↓
                                输出文件 → sanitize-filename → 下载
```

### PDF 智能分类链路

```
PDF 输入
   ↓
pdf-classifier.js 分类
   ├── 原生文本 PDF → pdf.js 提取 → pdf-office-docx/exceljs 生成
   ├── 扫描 PDF → tesseract.js OCR → 文本输出（提示版式损失）
   └── 混合 PDF → docstructure 引擎 + OCR 回退
```

### Markdown 处理链路

```
HTML/Office → mammoth → HTML → turndown → Markdown
                                        ↑
                                 parse5 (DOM构建)
```

---

## 与彩读 ColorTxt 依赖对比

两个项目都是 Electron 桌面应用，但功能定位不同，依赖重叠度约 30%。

| 分类 | 共同依赖 | 彩读独有 | FlyingMouse 独有 |
|------|---------|---------|-----------------|
| **框架** | electron、electron-builder | vue、vite、TypeScript、monaco-editor | express、multer |
| **PDF** | pdfjs-dist | - | pdf-lib |
| **图片** | sharp | - | - |
| **Markdown** | marked、katex | markmap、d3-cloud、d3-scale | @lezer/markdown、turndown、mammoth |
| **HTML解析** | - | cheerio、@xmldom/xmldom、xpath | parse5 |
| **压缩** | - | jszip、pako | yauzl、yazl |
| **数据库** | - | better-sqlite3、sqlite-vec | sql.js |
| **OCR** | - | transformers.js (AI向量化) | tesseract.js (OCR) |
| **文档生成** | - | - | docx、exceljs |
| **其他** | - | @node-rs/jieba、opencc、iconv-lite、jszip | csv-parse、js-yaml、sanitize-filename、mime-types |

**关键差异**：
- 彩读是**阅读器**，核心是 Monaco 编辑器 + 分词标注 + RAG
- FlyingMouse 是**格式转换器**，核心是多格式解析 + 生成 + OCR
- 彩读偏**前端交互**（Vue + Monaco 深度定制）
- FlyingMouse 偏**服务端处理**（Express + 多引擎调用）

---

## 补充说明

### 外置引擎（非 npm 依赖）

FlyingMouse Format 打包时内置了多个原生二进制引擎，这些不是 npm 依赖，而是单独的二进制资源：

| 引擎 | 作用 | 位置 |
|------|------|------|
| FFmpeg | 音视频转换 | bin/ffmpeg/ |
| LibreOffice | Office 文档转换 | bin/libreoffice/ |
| Poppler | PDF 处理（转图片等） | bin/poppler/ |
| Tesseract (系统) | OCR 系统引擎 | bin/tessdata/ |
| Pandoc | 通用文档转换 | bin/pandoc/ |
| QPDF | PDF 结构化处理 | bin/qpdf/ |
| dcraw | RAW 图片处理 | bin/dcraw/ |
| docengine | 高级文档结构识别 | bin/docengine/ |
| docstructure | PDF 结构分析 | bin/docstructure/ |
| AVS3 | AVS3 音频解码 | bin/avs3/ |

这些引擎体积大（LibreOffice 数百 MB），且被 Git 忽略（`bin/` 目录除 avs3 外均在 .gitignore 中），不包含在源码仓库内。

### monorepo 说明

| npm 包名 | 所在主仓库 | 子包位置 |
|---------|-----------|---------|
| csv-parse | node-csv (csv-parse 仓库) | packages/csv-parse/ |
| electron-updater | electron-builder | packages/electron-updater/ |

### 关于版本

- 所有仓库均为 `--depth 1` 浅克隆，只包含最新版本代码
- 如需特定版本，可进入对应目录执行 `git checkout <tag>`

### 关于许可证

各项目许可证不同，使用时请遵守各自的开源协议：

| 项目 | 许可证 |
|------|--------|
| pdf.js | Apache-2.0 |
| @lezer/markdown | MIT |
| csv-parse | MIT |
| js-yaml | MIT |
| marked | MIT |
| parse5 | MIT |
| docx | MIT |
| exceljs | MIT |
| pdf-lib | MIT |
| mammoth | BSD-2-Clause |
| turndown | MIT |
| tesseract.js | Apache-2.0 |
| sharp | Apache-2.0 |
| KaTeX | MIT |
| yauzl / yazl | MIT |
| electron | MIT |
| electron-builder | MIT |
| express | MIT |
| multer | MIT |
| mime-types | MIT |
| sanitize-filename | WTFPL OR ISC |
| sql.js | MIT |
