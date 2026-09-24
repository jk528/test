# test1.xlsm VBA 项目功能分析

> 源文件：VBComponents From (test1.xlsm) 260807171641
> 分析日期：2026-08-07
> 文件总数：约 80 个（.bas / .frm / .cls / .txt）

---

## 一、项目概述

这是一个基于 Excel VBA 的**中文文本阅读与分析工具**，核心工作流为：

```
导入 TXT/Word/Excel 文件 → 文本写入"数据源"工作表
  → 正则识别章节目录 → 目录列补全
  → 点击目录跳转定位 → 字符级上色高亮
  → 字典查询/字频统计/图表生成
```

项目通过 **SheetManager** 将工作表分为 6 大类（开发/阅读/分析/打字/常识/其他），用 `xlSheetVeryHidden` 实现页面隔离，通过自定义 **Ribbon 菜单** 按功能域分发操作。

---

## 二、核心工作表结构

| 工作表 | 用途 |
|--------|------|
| **数据源** | 核心：A 列=文本内容，B 列=章节目录，C 列=正则模式 |
| **目录** | 章节列表（A5 起）+ 查询词频率矩阵（横向追加列） |
| **目录2** | 双筛选查询的导航入口 |
| **排序** | 正则匹配结果的三视图输出 |
| **查询** | 字典查询输入（B3）+ 结果输出（A6/C6 起） |
| **重复字** | 重复字定位结果 |

---

## 三、功能模块详解

### 3.1 文件导入（READ_TXTTOEXCEL.bas — 51KB）

**主入口**：`ComprehensiveDataImport`，编排 5 步流程：选文件 → 检测类型 → 选处理方式 → 选导入方式 → 执行导入。

#### 支持的文件类型

| 类型 | 检测方式 | 导入方式 |
|------|---------|---------|
| Excel (.xls/.xlsx) | 扩展名 | ADODB `SELECT * FROM [sheet$]` 查询 → 二维数组批量写入 |
| Word (.doc/.docx) | 扩展名 | Word 对象模型读取 `Range.Text` → 清洗 → 写入 |
| TXT | 扩展名 | 二进制读字节 → 编码检测 → 按编码读取 → 清洗 → 写入 |

#### TXT 导入核心流程

```
1. ReadFileBytes     — Open For Binary 一次性读取全部字节
2. DetectEncoding    — BOM 头检测 + 字节模式启发式
                        FF FE → UTF-16LE
                        FE FF → UTF-16BE
                        EF BB BF → UTF-8 BOM
                        无 BOM → 扫描前100字节判断 UTF-8 多字节序列 vs ANSI
3. 按编码读取文本     — ANSI: Open For Input + Line Input
                        UTF-8: ADODB.Stream (Charset=utf-8)
                        Unicode: FileSystemObject.OpenTextFile(-1)
4. 文本处理（3种模式）— 模式1: 保留空格，标点→|  (正则 [^\u4e00-\u9fa5a-zA-Z0-9 \u3000])
                        模式2: 不保留标点      (正则 [^\u4e00-\u9fa5a-zA-Z0-9])
                        模式3: 原样保留
5. ConvertTextTo2DArray — 模式1/2 按 | 分割，模式3 按行分割 → N×1 二维数组
6. 批量写入           — Range.Resize(N,1).Value = dataArray
7. FormatSheet        — 列宽200、字号26、自动换行、浅蓝背景
```

#### 4 种导入方式

1. 当前工作表 A1 起
2. 新建工作表
3. 新建 Excel 文件
4. 指定单元格

---

### 3.2 内容上色（READ_上色.bas — 10.5KB）

**这是项目的核心特色功能，采用字符级着色。**

#### 两种着色粒度

| 粒度 | 方法 | 用途 |
|------|------|------|
| **字符级** | `cell.Characters(start, length).Font.Color = RGB(...)` | 高亮特定词语 |
| **单元格级** | `cell.Interior.Color = RGB(...)` | 整行/整格标记 |

#### 字符级上色实现逻辑

```
1. 用 InStr(pos, txt, searchText, vbTextCompare) 定位关键词位置
2. cell.Characters(startPos, textLength).Font.Color = RGB(...) 给子串着色
3. While pos > 0 循环：InStr(pos + Len, ...) 找下一个出现位置
4. 按 Select Case mm 循环切换 4 色：
     mm=0 → 红 RGB(255,0,0)
     mm=1 → 绿 RGB(0,255,0)
     mm=2 → 蓝 RGB(0,0,255)
     mm=3 → 青 RGB(0,255,255)
```

#### 主要上色函数

| 函数 | 说明 |
|------|------|
| `Color_ONE_TO_SS` | 单个固定词，在 Selection 中循环上 4 色 |
| `Color_SS_TO_SS` | 多词数组，每单元格独立循环上色 |
| `Color_SS_TO_SS_2` | 用户选词，所有单元格视为整体，每词只首次上色 + 章节统计 |
| `Color_SS_TO_SS_22` | 同上但单格多次上色，统计章节字数 |
| `ColorCellsByMultipleTextsOnce` | 多词匹配 → 整格底色绿色（找到即退出） |
| `ColorCellsByMultipleTextsMultipleTimes` | 多词匹配 → 整格底色绿色（不退出） |

> **关键点**：`Range.Characters(Start, Length).Font.Color` 是 Excel VBA 中唯一能给单元格内部分字符着色的方式。上色统计结果用 `Scripting.Dictionary` 按章节累计，写入"目录"表横向追加列。

---

### 3.3 章节目录识别与补全（READ_正则查询替换目录.bas — 16KB）

#### 步骤 1：预设章节正则（Ribbon C21/C22）

| 按钮 | 正则 | 匹配示例 |
|------|------|---------|
| C21 | `^第[零一二三四五六七八九十百千万亿0-9]{1,}(章\|回)(\| \|　).*` | 第一章 xxx、第3回 yyy |
| C22 | `^第.*第[零一二三四五六七八九十百千万亿0-9]{1,}(章\|回).*` | 第二卷第三章 xxx |

#### 步骤 2：正则匹配提取目录（`正则查询优化`，Ribbon C5）

```
1. 从 C2:Cn 读取多个正则，用 Join(..., "|") 合并为"或"模式
2. 创建 VBScript.RegExp，Global=True
3. 遍历 A 列每行文本：
   - .Replace(text, "xxx") → 替换后文本写入 I 列
   - .Execute(text) → 匹配项存入 matchDict（词频）+ duplicateMatchDict（保留重复）
   - 每行匹配项用 | 拼接写入 J 列
4. J 列 TextToColumns 按 | 分列
5. 输出到"排序"工作表（三视图：按顺序 / 按频率 / 按顺序去频率）
```

#### 步骤 3：目录列补全（`正则后辅助目录优化`，Ribbon C6）

```
从 J 列读取目录数据 → 遍历每行：
  非空 → 记为 lastValidDir，存入有效目录数组
  为空 → 用 lastValidDir 填充
结果写入 B 列（数据源目录列）+ "目录"表 A5 起
```

#### 正则替换（`正则替换优化`，Ribbon C13）

```
从 C:D 列读取"查找→替换"对照表 → 构建字典
A 列所有文本用 vbCr 拼成大字符串 → 逐个正则 .Replace 批量替换
Split 拆回数组 → 输出到 I 列 + "替换后文本"工作表
```

---

### 3.4 目录跳转（D_CatalogJump.bas + Sheet6 + Sheet8）

全局开关 `htcz`（Ribbon C23 复选框）控制是否启用点击跳转。

#### 路径 A：从"目录"表跳转（Sheet6 事件）

```
点击 A 列（行≥5）
  → InitializeCatalogJump
  → GetCatalogItems()：目录表 A5 项 ↔ 数据源 A 列精确匹配（LCase 比较）
  → 单匹配：激活数据源 + Cells(行号,1).Select
  → 多匹配：存全局变量 → 显示 UserForm4 供选择

点击 B 列
  → OptimizedSearch：数据源 A:B 列 Like "*词条*" 模糊搜索
  → 结果写入"目录2"表 + ColorizeMatches 上色（红绿蓝青 4 色循环）
```

#### 路径 B：从"目录2"表跳转（Sheet8 事件）

```
点击 B 列（行≥2）
  → DoubleFilterSearch：双筛选
     第一筛：数据源 B 列目录 = 选中格偏移的目录值
     第二筛：数据源 A 列文本 Like "*词条*"
  → 单匹配：跳转数据源
  → 多匹配：存全局变量 → 显示 UserForm3
```

#### 快捷键查找（查找一件套合集.bas）

| 快捷键 | 功能 |
|--------|------|
| Ctrl+A | `查找`：在数据源 A 列 Find 当前单元格值，跳转 + 记录来源 |
| Ctrl+D | `下查`：FindNext |
| Ctrl+S | `上查`：FindPrevious |
| Ctrl+Z | `返回`：回到来源表，计算停留秒数 |

---

### 3.5 字典查询与字频统计

#### 字典查询（READ_字典查询.bas）

```
"查询"表 B3 输入词条 → ExecuteSearch：
  读数据源 A2:B 末行到二维数组
  Like "*" & searchTerm & "*" 模糊匹配
  Scripting.Dictionary 按 B 列章节累计命中次数
  → 结果写"查询"表 A6，频率写 C6
  → UpdateBackendData：频率对齐到"目录"表章节列表，横向追加列
  → 形成"查询词 × 章节"频率矩阵
```

#### 字频统计（Read_最新字频.bas / READ_字频音.bas）

```
Word 读全文 → 正则 [^\u4e00-\u9fa5] 过滤非中文 → 逐字 Mid 进字典
  → 按频率分组（同频率字用 | 连接）
  → rex2：对每个字在数据源中用正则统计各章节出现次数
  → 写入"目录"表新列，顶部写"字数/合计/频率/总空"统计
  → mProcess 进度条显示进度
```

#### 重复字定位（READ_最新字频2.bas）

```
字频统计 → 对每个字找出现>1次的语句
  → d3 字典：key="行号|字|语句"，value=分类
  → 结果写入"重复字"表
```

---

### 3.6 EPUB 转 TXT（FC_EPUB_TO_TXT.bas）

```
1. 选择 .epub 文件 → 重命名为 .zip
2. 调用 WinRAR (x -ep) 解压
3. 等待（0.7秒/MB，最小3秒）
4. 递归遍历所有 HTML/XHTML 文件
5. HTML 清洗（extracttextfromhtml）：
   - 提取 <title>/<blockquote> 内容
   - 删除所有 HTML 标签
   - 替换 HTML 实体（&nbsp; &quot; 等）
   - 正则保留中文/英文/数字/标点，其余替换为 |
   - 合并连续 |，转为换行符
6. 输出 TXT（格式：第N章___内容）
7. 恢复 .zip 为 .epub，删除临时文件夹
```

---

### 3.7 数据聚合与图表（READ_聚合生成折线堆叠图.bas）

```
用户输入：数据范围 + MOD值（目标列数≤255）+ 聚合规则字符串
规则格式：长度,间距|长度,间距...（如 20,1|50,2）
  → 20,1 = 生成20列，每列1个原始列（不聚合）
  → 50,2 = 生成50列，每列2个原始列求和

AggregateDataWithArrays：按规则对每行数据分组求和
→ 新工作表输出 + 创建 xlLineStacked 折线堆叠图
→ X轴="目录"，Y轴="词量"
```

---

### 3.8 工作表管理（SheetManager.bas — 24KB）

| 分类 | 包含页面 |
|------|---------|
| 开发 | 首页、通知、变量管理器、版本、测试、开发者工具 |
| **阅读** | **数据源、查询、排序、目录、重复字、目录2** |
| 分析 | 排序、目录、对应目录详细、词频、重复字、标红 |
| 打字 | 打字页面、打字数据库、码字数据统计 |
| 常识 | 五行、正则、图例 |
| 其他 | — |

**核心逻辑**：`ShowCategory` 先全部显示，再将不属于当前分类的设为 `xlSheetVeryHidden`（用户无法手动取消隐藏）。`InitializeSheet` 为每个页面定制表头、冻结窗格、按钮。

---

### 3.9 自定义 Ribbon 菜单（DLL_自定义ribbon.bas）

| 回调组 | 控件 ID | 功能 |
|--------|---------|------|
| AA | b1–b7 | 组合排列工具（三角、排列组合、分词等） |
| BB | A1–A12 | 分类页面切换 + 目录窗体 |
| **CC** | **C1–C28** | **核心功能** |
| DDD | C23 | htcz 开关（后台查询） |
| Filter | — | 多项筛选/指定筛选/反向筛选 |

**CC 组核心功能**：

| ID | 功能 |
|----|------|
| C1 | 综合数据导入 |
| C2–C4 | 还原操作（排序/目录/初始化） |
| **C5** | **正则查询优化（目录提取）** |
| **C6** | **正则后辅助目录优化（目录补全）** |
| C7 | 正则查询优化2（第二套查询） |
| C8–C12 | 字频分析与着色 |
| C13 | 正则替换优化 |
| C14–C15 | 导出 TXT / Word |
| C16–C17 | 拼音显示 / EPUB 转 TXT |
| C18–C20 | A 列统计（字典排序/连续计数/出现次数） |
| C21–C22 | 预设章节正则 |
| C24–C28 | 批量查询/格式化/文件信息/重命名 |

---

### 3.10 其他模块

| 模块 | 功能 |
|------|------|
| **UserForm1.frm** | 主交互窗体：键盘监听 + 实时查询 + 标点补全 + 数字键选择（打字/输入法测试） |
| **凑数.frm** | 组合求和工具：在数值集合中找加和等于目标值的组合（财务对账） |
| **目录.frm** | 工作表导航窗体：ListBox 列出所有表名，点击跳转 |
| **ProgressBar.cls** | 通用进度条类（开源库，动态构建窗体控件） |
| **MouseOverControl.cls** | 鼠标滚轮控制类（开源库，解决 VBA ListBox 不支持滚轮） |
| **StringBuffer.cls** | 字符串缓冲类（开源库，Mid$ 语句优化拼接性能） |
| **F_001获取全部代码.bas** | VBA 代码自省工具：读取自身 VBProject 输出到表格 |
| **D_批量重命名文件夹中的文件.bas** | 递归扫描文件夹 + 复制重命名 |
| **FC_拼音.bas** | 拼音生成（142KB，大字典） |
| **ThisWorkbook.txt** | 工作簿事件：到期自毁机制（2036-10-01）+ 快捷键注册 |

---

## 四、模块间调用关系总览

```
ThisWorkbook.Open
  ├─ 注册快捷键 Ctrl+A/D/S/Z → 查找一件套合集.查找/下查/上查/返回
  ├─ ShowReadingCategory → SheetManager.ShowCategory("阅读")
  └─ 选中"数据源"工作表

Ribbon CC 组
  ├─ C1  → READ_TXTTOEXCEL.ComprehensiveDataImport（导入文件）
  ├─ C5  → READ_正则查询替换目录.正则查询优化（提取目录→J列）
  ├─ C6  → READ_正则查询替换目录.正则后辅助目录优化（补全→B列+目录表）
  ├─ C13 → READ_正则查询替换目录.正则替换优化
  ├─ C8  → Read_最新字频.to___字频音333（字频统计）
  ├─ C12 → READ_最新字频2.to_字频音__重复字（重复字定位）
  └─ C23 → 设置 htcz 开关

Sheet6(目录) SelectionChange [htcz=True]
  ├─ 点A列 → D_CatalogJump → 跳转数据源 / UserForm4
  └─ 点B列 → OptimizedSearch → ColorizeMatches 上色

Sheet8(目录2) SelectionChange [htcz=True]
  └─ 点B列 → DoubleFilterSearch → 跳转数据源 / UserForm3

READ_上色 (Ribbon 或手动调用)
  └─ Characters(start,len).Font.Color → 字符级高亮 + 章节统计→目录表

数据流核心：
  文件 → 数据源A列(文本) → [C5正则] → J列(章节) → [C6补全] → B列(目录)+目录表
       → [点击跳转] → 回到数据源对应行
       → [上色] → Characters.Font.Color 高亮
       → [字典查询] → 频率矩阵→目录表横向追加
```

---

## 五、与 ColorTxt 的功能对照

| ColorTxt 功能 | test1.xlsm 对应实现 | 实现程度 |
|--------------|---------------------|---------|
| 本地文件阅读（TXT） | READ_TXTTOEXCEL.bas：编码检测+多编码读取 | ✅ 完整实现 |
| 电子书格式转换（EPUB） | FC_EPUB_TO_TXT.bas：WinRAR解压+HTML清洗 | ⚠️ 仅 EPUB，依赖 WinRAR |
| 内容上色 | READ_上色.bas：Characters.Font.Color | ⚠️ 字符级可行，性能差 |
| 章节识别 | READ_正则查询替换目录.bas：正则匹配 | ✅ 完整实现 |
| 划线标注 | 无直接对应 | ❌ 未实现 |
| 简繁互转 | 无 | ❌ 未实现 |
| 书签与阅读进度 | 快捷键查找+返回（查找一件套合集.bas） | ⚠️ 简化版 |
| 语音朗读 | 无 | ❌ 未实现 |
| AI 阅读助手 | 无 | ❌ 未实现 |
| 书源找书 | 无 | ❌ 未实现 |
| 主题切换 | SheetManager 分类页面切换 | ⚠️ 页面级，非配色级 |
| 摸鱼快捷键 | 无 | ❌ 未实现 |
| 字频统计 | Read_最新字频.bas + READ_字频音.bas | ✅ 完整实现（ColorTxt 无此功能） |
| 数据聚合图表 | READ_聚合生成折线堆叠图.bas | ✅ 完整实现（ColorTxt 无此功能） |
| 目录跳转 | D_CatalogJump + Sheet6/Sheet8 事件 | ✅ 完整实现 |

---

## 六、关键技术点总结

1. **TXT 导入**：二进制读字节 → BOM/字节模式检测编码 → ADODB.Stream(UTF-8) / Line Input(ANSI) / FSO(Unicode) 分别读取 → 正则清洗标点 → Split 转 N×1 二维数组 → `Range.Resize.Value` 批量写入

2. **字符级上色**：`cell.Characters(startPos, textLength).Font.Color = RGB(...)` 配合 `InStr` 循环定位所有出现位置，4 色循环切换。这是 Excel VBA 中唯一能给单元格内部分字符着色的方式

3. **目录识别**：多正则合并为"或"模式 → `VBScript.RegExp` 全局匹配 → 匹配项存字典(词频+保留重复) → 向下填充补全目录列

4. **目录跳转**：两条路径——目录表精确匹配跳转 + 目录2表双筛选(目录+词条)模糊匹配跳转，均由 `htcz` 全局开关控制

5. **字典查询**：`Like` 模糊匹配 + `Scripting.Dictionary` 按章节累计频率 → "查询词 × 章节"频率矩阵横向追加到目录表

6. **开源库引用**：ProgressBar、MouseOverControl、StringBuffer 三个类均来自 [cristianbuse](https://github.com/cristianbuse) 的 GitHub 开源项目（MIT 协议）
