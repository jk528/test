# 红楼梦章节分析脚本工具使用说明

## 概述

本文件夹包含《红楼梦》双轨六要素分析体系的全部自动化脚本，用于章节分析报告的生成、验证、升级、修复、人物档案维护和归档索引管理。

**当前版本**：V3.4 / 流程 v2.0
**分析框架**：新闻六要素（A轨）+ 叙事六要素（B轨）+ 七类情绪分析（DUTIR+Hownet 双轨）+ 冲突动机/叙事手法/情感趋势
**情绪分析模块**：`基础/emotion_analysis.py`（EmotionAnalyzer + SentimentAnalyzer）
**配套文档**：`skill/V3.4分析任务说明书.md`（逐章生成任务规范）、`skill/章节内容分析流程.md`（流程 v2.0）、`skill/章节分析归档规范.md`（归档 v1.3）

---

## 目录结构

脚本按功能分类到 6 个子文件夹：

```
脚本工具/
├── 分析生成类/              # 生成报告、批量情绪分析的核心脚本
│   ├── generate_ch01_v32_v3.py    # 第1章V3.2报告生成（测试用）
│   ├── analyze_ch19.py            # 第19章情绪分析
│   ├── batch_emotion_analysis.py  # 单章情绪分析引擎（供批量脚本调用）
│   ├── batch_emotion_1_18.py      # 1-18章批量情绪分析
│   ├── batch_all_emotions.py      # 1-120章全量批量情绪分析
│   ├── batch_emotions_81_120.py   # 81-120章批量情绪分析
│   └── run_emotion_ch21.py        # 第21章情绪分析（单章）
│
├── 验证检查类/              # 验证报告结构和数据完整性
│   ├── verify_v32.py              # 基础结构验证（大章节/子章节数）
│   ├── deep_verify.py             # 深度验证（版本/数据/内容完整性）
│   ├── verify_alignment.py        # 格式对齐验证
│   └── check_dicts.py             # 情感词典完备性检查（DUTIR+Hownet）
│
├── 升级迁移类/              # 版本升级和格式迁移
│   ├── upgrade_v32_v2.py          # 1-18章 V3.1→V3.2 升级
│   ├── upgrade_ch19_v32.py        # 第19章 V3.2 升级
│   ├── full_upgrade_reports.py    # 全量报告升级
│   ├── batch_upgrade_reports.py   # 批量升级
│   ├── update_index_v32_v2.py     # 归档索引 V3.2 更新
│   └── v34_convert.py             # V3.3→V3.4 全量转换（80章，版本升级+新增段落+§5.7回填）
│
├── 修复维护类/              # 修复问题和维护数据
│   ├── fix_headers.py             # 修复标题和头部信息块
│   ├── fix_person_order.py        # 修复人物出场顺序
│   └── fix_section6.py            # 修复§六情感基调演变趋势数据
│
├── 人物档案类/              # 人物出场档案相关
│   ├── extract_all_persons.py     # 提取全部出场人物
│   ├── rebuild_person_archive.py  # 重建人物出场档案
│   ├── analyze_persons.py         # 人物出场分析 v1（新出场/去重）
│   └── analyze_persons_v2.py      # 人物出场分析 v2（别名检测/统计）
│
├── 索引归档类/              # 归档索引生成与维护
│   ├── optimize_index.py          # 优化归档索引结构
│   ├── process_tasks.py           # 批量处理任务（JSON分词转TXT等）
│   ├── update_index_v33.py        # 生成 V3.3 归档索引数据
│   ├── extract_v33_data.py        # 从 V3.3 报告提取数据
│   ├── extract_index_data.py      # 提取21-80章情感数据（供索引更新）
│   ├── extract_detailed_index.py  # 从21-80章MD提取逐章详细数据
│   ├── generate_index_rows.py     # 生成逐章累计统计行
│   ├── comprehensive_index_update.py # 综合提取缺失数据
│   ├── apply_index_updates.py     # 应用所有索引更新
│   ├── extract_81_120_index.py    # 提取81-120章数据更新索引
│   ├── probe_parse.py             # V3.4 报告格式探测（调试用）
│   ├── extract_v34.py             # 从 V3.4 报告提取数据 v1（已废弃，仅供参考）
│   ├── extract_v34_v2.py          # 从 V3.4 报告提取数据 v2（当前使用，容错增强）
│   └── gen_index.py               # 生成 V3.4 归档索引（7大部分完整索引）
│
└── README.md                # 本文件
```

---

## 一、分析生成类

### 1. batch_emotion_analysis.py
**功能**：单章情绪分析引擎。读取指定章节的分词 JSON，输出 DUTIR 七类情绪分布 + Hownet 正负极性 + 高频词汇。供批量脚本通过 `subprocess` 调用。
- 输入：`红楼梦_分词结果/{章号三位}.json`
- 输出：控制台打印情绪统计（DUTIR 七类 / Hownet 正负 / Top30 高频词）
- 用法：`python batch_emotion_analysis.py 021`

### 2. batch_emotion_1_18.py
**功能**：批量分析 1-18 章的七类情绪（DUTIR+Hownet 双轨）
- 输出：`分析结果/情绪分析数据/ch01-18_emotion_analysis.json`
- 用法：`python batch_emotion_1_18.py`

### 3. batch_emotions_81_120.py
**功能**：批量运行 81-120 章情绪分析，逐章解析结果并保存 JSON
- 输出：`情感分析结果/{章号三位}_emotion.json`（跳过已存在）
- 用法：`python batch_emotions_81_120.py`

### 4. batch_all_emotions.py
**功能**：批量运行 1-120 章全量情绪分析（跳过已存在）
- 输出：`情感分析结果/{章号三位}_emotion.json`
- 用法：`python batch_all_emotions.py`

### 5. run_emotion_ch21.py
**功能**：第 21 章情绪分析（单章，读 021.json）
- 用法：`python run_emotion_ch21.py`

### 6. analyze_ch19.py
**功能**：第 19 章情感分析（三维统计 + 七类情绪），输出到 `分析结果/ch19_emotion_data.json`
- 用法：`python analyze_ch19.py`

### 7. generate_ch01_v32_v3.py
**功能**：按 V3.2 模板完整生成第 1 章分析报告（测试用）
- 输出：`分析结果/001_甄士隐梦幻识通灵_双轨六要素分析报告.md`
- 用法：`python generate_ch01_v32_v3.py`

---

## 二、验证检查类

### 1. verify_v32.py
**功能**：基础结构验证。检查报告的：大章节数、子章节数、§4.3/§4.4/§5.3/§5.7 是否存在、V3.2 版本号
- 用法：`python verify_v32.py`

### 2. deep_verify.py
**功能**：深度验证。检查 §5 子章节顺序、版本号三处一致性、数据占位符数量、完整性检测项数量、§4.3/§4.4 是否为空
- 用法：`python deep_verify.py`

### 3. verify_alignment.py
**功能**：全面验证报告格式是否对齐最新模板（检查所有 ##/### 章节结构）
- 用法：`python verify_alignment.py`

### 4. check_dicts.py
**功能**：检查情感词典完备性 —— DUTIR 7 类情绪词 + Hownet 正负极性词 + 辅助词表规模
- 口径说明：正面/负面情感词取自 Hownet pos.txt/neg.txt；7 类情绪词取自 DUTIR；同义词.txt/反义词.txt 为「同义词词林/反义词对表」，非情感词典，仅报告规模
- 用法：`python check_dicts.py`

---

## 三、升级迁移类

### 1. upgrade_v32_v2.py
**功能**：将 1-18 章报告从 V3.1 升级到 V3.2（新增 §4.3/§4.4/§5.3、重排 §5 编号、更新版本号）
- 用法：`python upgrade_v32_v2.py`

### 2. upgrade_ch19_v32.py
**功能**：将第 19 章从 V3.1 升级到 V3.2
- 用法：`python upgrade_ch19_v32.py`

### 3. full_upgrade_reports.py
**功能**：全量报告升级（含 1-18 章完整升级流程）
- 用法：`python full_upgrade_reports.py`

### 4. batch_upgrade_reports.py
**功能**：批量升级报告
- 用法：`python batch_upgrade_reports.py`

### 5. update_index_v32_v2.py
**功能**：更新归档索引表到 V3.2（新增冲突数/叙事维度/情感分段 3 列）
- 用法：`python update_index_v32_v2.py`

### 6. v34_convert.py
**功能**：V3.3 → V3.4 全量报告转换脚本（80章批量升级）
- 升级内容：版本号替换（V3.3→V3.4 / v1.9→v2.0 / v1.2→v1.3）
- 新增段落：颗粒度要求、段落索引规范、拆分排查机制、A轨提取颗粒度要求、预言人物表
- §5.7 重写：用 `情感分析结果/{章号}_emotion.json` 数据完整重写七类情绪分布（5.7.1/5.7.2/5.7.3）
- 输入：`分析结果/V3.3存档_1-80章/` + `情感分析结果/`
- 输出：`分析结果/V3.4存档_1-80章/`
- 特殊处理：第5/22/63章预言人物表有预定义内容
- 用法：`python v34_convert.py`

---

## 四、修复维护类

### 1. fix_headers.py
**功能**：修复 1-18 章丢失的标题和头部信息块
- 用法：`python fix_headers.py`

### 2. fix_person_order.py
**功能**：修复归档索引中人物出场档案的章号顺序（按首次出场章号从小到大）
- 用法：`python fix_person_order.py`

### 3. fix_section6.py
**功能**：修复 §六 情感基调演变趋势数据，使用 §一 索引表的正确数据
- 用法：`python fix_section6.py`

---

## 五、人物档案类

### 1. extract_all_persons.py
**功能**：从各章报告 §7.1/§4.2 人物占位符中提取全部出场人物
- 用法：`python extract_all_persons.py`

### 2. rebuild_person_archive.py
**功能**：用完整人物数据重建归档索引的人物出场档案表
- 用法：`python rebuild_person_archive.py`

### 3. analyze_persons.py
**功能**：人物出场分析 v1 —— 从提取数据中计算每章新出场人物、首次出场章号映射
- 输入：提取的章节数据 JSON
- 输出：人物首次出场映射、每章新人物列表
- 用法：`python analyze_persons.py`

### 4. analyze_persons_v2.py
**功能**：人物出场分析 v2 —— 增加别名检测、名称去重、出场频次统计
- 在 v1 基础上补充别名归并和人物频次排序
- 用法：`python analyze_persons_v2.py`

---

## 六、索引归档类

### 1. optimize_index.py
**功能**：优化归档索引结构（新增板块、目录导航、基调演变趋势）
- 用法：`python optimize_index.py`

### 2. process_tasks.py
**功能**：批量处理任务（JSON 分词文件转 TXT、更新归档索引）
- 用法：`python process_tasks.py`

### 3. update_index_v33.py
**功能**：合并提取的多章数据，生成 V3.3 归档索引数据（index_rows / stats_rows / trend_rows / emo_rows）
- 输入：`分析结果/v33_extracted_data.json`、`分析结果/情绪分析数据/*.json`
- 输出：`分析结果/v33_index_data.json`
- 用法：`python update_index_v33.py`

### 4. extract_v33_data.py
**功能**：从 V3.3 报告逐章提取字数/事件/人物/情感统计，输出 `分析结果/v33_extracted_data.json`
- 用法：`python extract_v33_data.py`

### 5. extract_index_data.py
**功能**：提取 21-80 章情感分析数据 + 报告元数据，输出 `情感分析结果/index_summary.json`
- 用法：`python extract_index_data.py`

### 6. extract_detailed_index.py
**功能**：从 21-80 章 MD 报告提取逐章详细数据（字数/事件/人物/冲突/伏笔/情感），输出 `情感分析结果/detailed_index.json`
- 用法：`python extract_detailed_index.py`

### 7. generate_index_rows.py
**功能**：基于 detailed_index.json 生成逐章累计统计行 + 新出场人物列 + 人物出场档案条目
- 用法：`python generate_index_rows.py`

### 8. comprehensive_index_update.py
**功能**：综合提取脚本，从 21-80 章报告提取所有缺失数据，生成归档索引更新内容
- 用法：`python comprehensive_index_update.py`

### 9. apply_index_updates.py
**功能**：读取归档索引文件，应用所有提取结果更新（§一/§二/§三/§四/§六 各表），生成完整新索引
- 用法：`python apply_index_updates.py`

### 10. extract_81_120_index.py
**功能**：从 81-120 章 V3.4 报告提取详细数据（字数/事件/人物/伏笔/冲突/情绪），生成索引行、累计统计行、趋势行
- 用法：`python extract_81_120_index.py`

### 11. probe_parse.py
**功能**：V3.4 报告格式探测脚本（调试用）
- 逐章探测 §5.1/§5.7/事件表/人物表等字段的格式差异
- 用于定位提取失败的章节，辅助 extract 脚本调试
- 用法：`python probe_parse.py`

### 12. extract_v34.py
**功能**：从 V3.4 报告提取数据 v1（**已废弃，仅供参考**）
- 第一版提取脚本，存在"约"字解析、正则分组索引等 bug
- 请使用 `extract_v34_v2.py` 替代
- 用法：`python extract_v34.py`

### 13. extract_v34_v2.py
**功能**：从 V3.4 报告提取数据 v2（**当前使用版本**）
- 提取字段：字数、事件数(★/◆/◇)、人物数、冲突数、情感分段、情感基调、三维统计(§5.1)、DUTIR七类情绪(§5.7)、Hownet极性、伏笔线索数
- 容错增强：约数/小数/缺失值均有 fallback，不会因单章异常中断
- 输入：`分析结果/V3.4存档_1-80章/`（80份 MD 报告）
- 输出：`分析结果/v34_extract_v2.json`
- 用法：`python extract_v34_v2.py`

### 14. gen_index.py
**功能**：生成 V3.4 归档索引（7 大部分完整索引文件）
- 依据：`章节分析归档规范 v1.3` + `章节内容分析流程 v2.0 §10.2`
- 7 大部分：§一归档索引表 / §二人物出场档案 / §三逐章累计统计 / §四伏笔线索追踪 / §五七类情绪分析汇总 / §六情感基调演变趋势 / §七全局统计摘要
- 内置功能：情感基调 14→6 类归一化、人物别名归并（ALIAS 字典）、主导情绪格式化、数据源分离（§5.1 三维统计 vs §5.7 DUTIR）
- 输入：`分析结果/v34_extract_v2.json`（提取数据）
- 输出：`分析结果/_归档索引_V3.4.md`
- 用法：`python gen_index.py`

---

## 使用流程

### 新增一章分析的标准流程

```
1. 准备原文和分词数据
   └─ 原文放入 红楼梦_拆分/ 文件夹
   └─ 分词数据放入 红楼梦_分词结果/ 文件夹

2. 情绪分析
   └─ 运行 batch_emotion_analysis.py {章号} （单章，或批量脚本）

3. 生成/升级报告
   └─ 使用对应版本的生成/升级脚本

4. 验证报告
   └─ 运行 verify_v32.py （基础验证）
   └─ 运行 deep_verify.py （深度验证）
   └─ 运行 verify_alignment.py （格式对齐）

5. 更新归档索引
   └─ 运行 extract_* 脚本提取数据
   └─ 运行 apply_index_updates.py / update_index_v33.py 更新索引

6. 存档
   └─ 复制到对应版本存档文件夹
```

### 版本升级流程

```
1. 先备份当前版本（复制到存档文件夹）
2. 运行升级脚本（upgrade_*.py）
3. 运行验证脚本（verify_v32.py + deep_verify.py）
4. 抽查几章确认内容正确
5. 更新归档索引
6. 创建新版本存档
```

---

## 依赖说明

### Python 版本
- Python 3.8+

### 依赖库
- 标准库：os, re, json, glob, collections, subprocess
- 无第三方库依赖（情绪分析使用本地 `基础/emotion_analysis.py`，DUTIR + Hownet 双词典体系）

### 基础资源（必备）
```
基础/
├── 同义词.txt          # 同义词词林扩展版（词表，非情感词典）
├── 反义词.txt          # 反义词对表（非情感词典）
├── 否定词.txt          # 否定词列表
├── 递进词.txt          # 递进/程度副词
├── 停用词.txt          # 主停用词表
├── 红楼梦人物名.txt     # 全书人物名列表
├── 红楼梦分词词典.txt    # 专用分词词典
├── emotion_analysis.py  # 情绪分析模块（EmotionAnalyzer + SentimentAnalyzer）
├── 情感词典_DUTIR/      # DUTIR 7大类情绪词典（27,414词）
├── 情感词典_Hownet/     # Hownet 极性词典（19,472词）
└── 停用词库/            # 停用词库（4个表）
```

> **词典规模口径说明**：「27,414词」「19,472词」为官方标称规模（文件非空行数）；`emotion_analysis.py` 用 `set()` 去重后实际匹配词数为 DUTIR 27,389 词、Hownet 正负极性（pos+neg）17,690 词，报告统计以此为准。

### 数据文件
```
红楼梦_拆分/            # 120章原文（按章拆分）
红楼梦_分词结果/        # 120章分词数据（JSON格式）
红楼梦_分词结果_txt/    # 120章分词数据（TXT格式）
分析结果/               # 分析报告输出目录
├── 001_..._分析报告.md
├── ...
├── _归档索引.md / _归档索引_V3.3.md / _归档索引_V3.4.md
├── v34_extract_v1.json   # V3.4 提取数据 v1（废弃）
├── v34_extract_v2.json   # V3.4 提取数据 v2（当前使用，gen_index.py 输入）
├── 人物档案_第1-19章.json
├── 情绪分析数据/
├── V3.0存档_1-18章/  V3.2存档_1-19章/  V3.3存档_1-80章/
├── V3.4存档_1-80章/
└── v33_extracted_data.json / v33_index_data.json
情感分析结果/           # 逐章情绪分析 JSON（{章号}_emotion.json 等）
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V3.0 | 2026-08-25 | 初始版本，双轨六要素基础框架 |
| V3.1 | 2026-08-26 | 新增七类情绪分析（DUTIR+Hownet 双轨） |
| V3.2 | 2026-08-26 | 加回冲突动机分析、叙事手法、情感趋势分析 |
| V3.3 | 2026-08-26 | 归档索引细化（逐章统计、人物档案、伏笔线索） |
| V3.4 | 2026-08-26 | 事件颗粒度细化、字段格式统一、词典规模口径说明；新增 v34_convert.py / extract_v34_v2.py / gen_index.py 等 V3.4 专项脚本 |

---

## 注意事项

1. **运行路径**：部分脚本内置绝对路径（硬编码），移动位置不影响运行；使用相对路径（`os.path.join(base, '..', '..')`）的脚本依赖 `脚本工具/{分类}/` 两级目录结构，**请勿将脚本移到其他层级**
2. **编码问题**：所有脚本均内置编码 fallback 链（utf-8 → gbk → gb18030）
3. **数据口径**：情感词三维统计采用人工校准口径；词典规模区分「官方标称」与「去重后实际匹配」两种口径
4. **字段格式规范**：约数占比用 `~整数%`，精确占比用 `X.X%`，事件度量用「件」，主导情绪用 `情绪字(占比%)`，人物度量用「人」
5. **存档习惯**：每次大版本升级前先备份，确认无误后再覆盖
6. **验证优先**：任何修改后务必运行验证脚本确保结构完整
7. **V3.4 索引生成推荐流程**：`extract_v34_v2.py` → `gen_index.py`（两步完成，无需其他脚本）

---

*文档版本：V3.4.1*
*更新日期：2026-08-27*