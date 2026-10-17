# DavionWu2018/Sentiment_dictionary 资源详情

**仓库地址**：https://github.com/DavionWu2018/Sentiment_dictionary
**作者**：Davion Wu（南开大学）
**邮箱**：dwu@mail.nankai.edu.cn
**研究方向**：旅游管理、文本挖掘、事件研究、可持续旅游

---

## 一、仓库概览

[数据+代码] 经典的中文情感词典、情感分析停用词、程度副词、否定词表 + 中文金融情感词典（包括上市公司文本_正式和股吧社媒文本_非正式）。

## 二、文件结构

```
Sentiment_dictionary/
├── BosonNLP_sentiment_score/      # BosonNLP情感分值词典
├── Code_Davion/                    # Python示例代码（Jupyter）
├── 中文金融情感词典_姜富伟等(2020)/ # 姜富伟2020金融词典
├── 金融领域中文情绪词典_姚加权等(2021)/ # 姚加权2021金融词典
├── 程度副词/                       # 程度副词表
├── 否定词/                         # 否定词表
├── 停用词/                         # 停用词表
├── 股吧社媒金融情感词典_Davion/     # 作者自建股吧词典
├── README.md
├── data.xlsx                       # 示例数据
└── data_result.xlsx                # 示例结果
```

## 三、各资源详情

### 3.1 BosonNLP_sentiment_score

- **来源**：BosonNLP（玻森数据）
- **类型**：带情感分值的词典
- **特点**：基于大规模社交媒体数据构建，每个词有连续分值

### 3.2 中文金融情感词典_姜富伟等(2020)

- **来源**：姜富伟等（2020）
- **类型**：金融领域情感词典
- **适用文本**：上市公司正式文本（年报、公告等）
- **参考仓库**：https://github.com/MengLingchao/Chinese_financial_sentiment_dictionary

### 3.3 金融领域中文情绪词典_姚加权等(2021)

- **来源**：姚加权等（2021）
- **类型**：金融领域情绪词典
- **适用文本**：金融领域文本
- **参考仓库**：https://gitee.com/arlionn/SentimentDictionaries

### 3.4 股吧社媒金融情感词典_Davion

- **来源**：Davion Wu 自建
- **类型**：金融社交媒体情感词典
- **适用文本**：股吧、社媒等非正式金融文本
- **特点**：针对股吧等社交媒体语境构建

### 3.5 程度副词

- **类型**：程度副词 + 强度等级
- **用途**：情感强度加权计算
- **常见等级**：极高级、高级、比较级、稍低级

### 3.6 否定词

- **类型**：否定词列表
- **用途**：情感翻转计算
- **常见否定词**：不、没、无、非、否、未、别等

### 3.7 停用词

- **类型**：情感分析用停用词表
- **用途**：过滤无情感意义的虚词

### 3.8 Code_Davion

- **类型**：Python代码（Jupyter Notebook）
- **用途**：情感分析示例代码
- **使用方式**：在Jupyter中运行，注意文件路径

## 四、使用方法

1. 打开`Code_Davion`文件夹下的Python程序，在Jupyter中运行
2. 查看`data.xlsx`和`data_result.xlsx`示例文件
3. 将对应数据替换成待分析文本即可

## 五、引用的数据源

| 资源 | 链接 |
|------|------|
| 评论数据情感分析数据集 | http://www.datatang.com/data/11857 |
| jieba中文分词 | https://github.com/fxsjy/jieba |
| NLPIR汉语分词系统 | http://ictclas.nlpir.org/ |
| smallseg分词 | https://code.google.com/p/smallseg/ |
| yaha分词 | https://github.com/jannson/yaha |
| 现有情感词典汇总 | http://www.datatang.com/data/46922 |
| BosonNLP | http://bosonnlp.com/product |
| 情感分析用词语集（beta版） | http://www.keenage.com/html/c_bulletin_2007.htm |
| 台湾大学NTUSD | http://www.datatang.com/data/11837 |
| 程度副词及否定词表 | http://www.datatang.com/data/44198 |

## 六、特点

1. **领域针对性强**：专门收录金融领域情感词典（3种）
2. **配套完整**：词典 + 代码 + 示例数据 + 停用词 + 程度副词 + 否定词
3. **作者自建词典**：股吧社媒金融情感词典，针对非正式金融文本
4. **可运行代码**：提供Python/Jupyter示例，可直接上手

## 七、适用场景

- 金融文本情感分析（年报、公告、研报）
- 股吧/社交媒体金融文本情感分析
- 情感分析入门与实践
- 程度副词 + 否定词的情感强度计算

---

*整理日期：2026-08-26*
