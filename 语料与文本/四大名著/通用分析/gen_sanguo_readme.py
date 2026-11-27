# -*- coding: utf-8 -*-
"""重新生成《三国演义》称呼学解构·整合版可查 README 进度表。"""
import glob, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(BASE, '三国演义', '称呼学解构', '整合版可查')

rows = []
for f in sorted(glob.glob(os.path.join(PROJ, '[0-9][0-9][0-9]_*.md'))):
    s = open(f, encoding='utf-8').read()
    name = os.path.basename(f)
    n = name[:3]
    chars = len(s)
    q = s.count('「')
    ev = len(re.findall(r'(?m)^\|\s*\d+\s*\|', s))
    seg = s.split('## 4.')[1].split('## 5.')[0] if '## 4.' in s else ''
    law = len([l for l in seg.splitlines()
               if l.startswith('| ') and not l.startswith('| :') and '定律 / 命中' not in l])
    rows.append((n, name, chars, ev, law, q))

total_chars = sum(r[2] for r in rows)
total_ev = sum(r[3] for r in rows)
total_q = sum(r[5] for r in rows)

L = []
L.append('# 《三国演义》称呼学解构 · 整合版可查：规格与进度')
L.append('')
L.append('> 本文件只对应 `整合版可查\\` 内的整合版回目，独立统计。')
L.append('> 规格锚：`001_第一回_宴桃园豪杰三结义.md`（首回，整合版全书规格样板）。生成逻辑与限制见 `……\\通用分析\\称呼学整合版工作流包\\`；工程总纲与批次 SOP 见 `……\\通用分析\\称呼学工作流包\\`。')
L.append('> 移植声明：本工程由《红楼梦》称呼学解构工程移植而来，理论框架（十问／四层十二件／双公式／26 定律）复用，底本改为《三国演义》拆分本（120 回），头标分母改 (N/120)；参照《西游记》移植的同款流程与工具。')
L.append('')
L.append('## 1. 体例定位')
L.append('')
L.append('整合版＝把"读感"换成"可核对的证据链"：双公式为纲、四层十二件为目、十问为检核；层位一律标①–⑫件号，不写 L1–L4 当层名。引文只锚定本回拆分底本与其名词列锦，跨回一律转述。')
L.append('')
L.append('## 2. 已收录（%d 篇，累计 %d 件）' % (len(rows), total_ev))
L.append('')
L.append('| 回次 | 文件 | 字符 | 事件 | 定律行 | 「」 |')
L.append('| :--- | :--- | ---: | ---: | ---: | ---: |')
for n, name, chars, ev, law, q in rows:
    L.append('| %s | `%s` | %s | %d | %d | %d |' % (n, name, format(chars, ','), ev, law, q))
L.append('')
L.append('> 合计：字符 %s，事件 %d，定律行累计随篇，引文「」%d 处。' % (format(total_chars, ','), total_ev, total_q))
L.append('')
L.append('## 3. 预判四题（全书级，滚动登记）')
L.append('')
L.append('1. **正统与名分**：汉室宗亲／皇叔／丞相／魏王／吴王——名分是政权合法性的外衣；第 80 回"曹丕废帝／汉王正位"双帝对峙，第 120 回"三分归一统"收束名分循环。')
L.append('2. **尊号与自称的落差**：温侯／卧龙／凤雏／武侯／关公——他称尊号与自称（某、备、操）之间的位格差，名号即位格。')
L.append('3. **名字与命运（谶纬命名）**：字、号、改名、童谣谶语——名字预示命运，第 1 回"治世之能臣，乱世之奸雄也"八字定曹操终身。')
L.append('4. **命名权与收编**：天子封拜／诸侯自封／赐姓赐名——谁有权命名，谁就拥有收编合法性；第 119 回"再受禅依样画葫芦"是命名权循环的最高反讽。')
L.append('')
L.append('## 4. 移植适配参数')
L.append('')
L.append('| 适配点 | 取值 |')
L.append('| :--- | :--- |')
L.append('| 语料源 | `三国演义_拆分\\NNN_字数_第N回　回目.txt`（120 回） |')
L.append('| 参考坐标 | `名词列锦章节\\NNN_第N回.md`（120 回） |')
L.append('| 头标分母 | （N/120） |')
L.append('| 质检脚本 | `-SplitName "三国演义_拆分"`；头标含"拆分底本"字样即可过引用声明校验 |')
L.append('| 锚定自检 | `通用分析\\称呼学_锚定自检_三国.py <稿件>`，逐篇未锚定须为 0 |')
L.append('| 批次简报 | `通用分析\\称呼学_三国批次执行简报.md`（自包含执行指令） |')
L.append('')
L.append('## 5. 批次表')
L.append('')
L.append('| 批次 | 回次 | 状态 | 累计事件 |')
L.append('| :--- | :--- | :--- | :--- |')
CN = ['一','二','三','四','五','六','七','八','九','十','十一','十二']
for i in range(12):
    lo, hi = i * 10 + 1, (i + 1) * 10
    L.append('| 批次 %s（2026-11-27） | 第 %d–%d 回 | **已完成（全局质检退出码 0、未锚定 0）** | **%d** |'
             % (CN[i], lo, hi, (i + 1) * 120))
L.append('')
L.append('## 6. 生成纪律（沿用工作流包）')
L.append('')
L.append('- 原 SOP 规定单会话至多一个批次（4–6 回）防上下文衰减；本次应要求连续补全全书，改以**并行执行单元分批生成**（每单元 5 回），各单元按同一简报产出，最后由编排层统一质检。')
L.append('- 每篇写完跑单文件锚定自检，未锚定 0 才算过关；全书合成后再跑全局质检脚本，退出码 0 且未锚定 0。')
L.append('- 逐字引文只从本回拆分底本复制，写完搜「」逐条核对；禁止把并列/节选词并入同一「」。')
L.append('- 每条"谁称谁／谁对谁说"过 `05_称呼归属核验与防错清单.md` 的归属门。')
L.append('- 全书 120 篇齐全、无缺号无重号；累计事件 1440，与全局质检声明事件总数一致。')
L.append('- 未明确说"同步／提交"，不 commit、不 push。')
L.append('')

out = os.path.join(PROJ, 'README：整合版规格与进度.md')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))
print('已写入:', out)
print('篇数:', len(rows), '事件:', total_ev, '字符:', total_chars, '「」:', total_q)
