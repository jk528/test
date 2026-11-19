# -*- coding: utf-8 -*-
"""按 v2.3 §7.5 修复四书词族表占位行/变体引号行。行数守恒、原位替换、逐字可核。"""
import glob, os, re, sys

ROOT = os.getcwd()
SPLIT = {
    "三国演义": "三国演义/三国演义_拆分",
    "红楼梦": "红楼梦/红楼梦_拆分",
    "西游记": "西游记/《西游记》_拆分",
    "水浒传": "水浒传/水浒传_拆分",
}

def norm(s):
    return re.sub(r"[\s，。、；：？！「」『』""''\"'（）()《》〈〉…·—\-－,.;:?!□〇○×＊*～〔〕【】«»‹›„．]", "", s)

# 语料缓存：章号前缀 -> 归一全文
_cache = {}
def corpus(book, prefix):
    key = (book, prefix)
    if key not in _cache:
        fs = glob.glob(os.path.join(ROOT, SPLIT[book], prefix + "*.txt"))
        _cache[key] = norm(open(fs[0], encoding="utf-8", errors="replace").read()) if fs else ""
    return _cache[key]

def qok(quote, book, prefix):
    """取「…」内容，整段归一命中或按标点切分逐段命中（>=2 字）。"""
    m = re.search(r"「(.+?)」", quote)
    if not m:
        return False
    inner = norm(m.group(1))
    c = corpus(book, prefix)
    if not c:
        return False
    if inner in c:
        return True
    segs = [norm(x) for x in re.split(r"[。；？！，、\n\s\u3000]+", m.group(1))]
    segs = [s for s in segs if len(s) >= 2]
    return len(segs) > 0 and all(s in c for s in segs)

# 每项：(书, 章文件, 行号, 旧整行, 新第1列, 新第2列, 新第3列, 新第4列)
# 新列=None 表示保持原列不变
FIX = [
    # ===== 三国演义 5 行 =====
    ("三国演义", "三国演义/名词列锦章节/009_第九回.md", 271,
     "| 飞熊军三千 | 第九回·守郿坞 | „领飞熊军三千守郿坞」 | C16 |",
     None, None, "「领飞熊军三千守郿坞」", None),
    ("三国演义", "三国演义/名词列锦章节/035_第三十五回.md", 400,
     "| 景升 | 第35回·谒刘表 | 见称谓字号表 | — |",
     None, "第35回·谒刘表", "「久闻刘景升善善恶恶，特往谒之」", "C24"),
    ("三国演义", "三国演义/名词列锦章节/035_第三十五回.md", 570,
     "| 十倍 | 第35回·无 | （本回\"胜吾十倍者\"见原文，补列） | — |",
     None, "第35回·水镜语", "「自有胜吾十倍者来助公」", "—"),
    ("三国演义", "三国演义/名词列锦章节/059_第五十九回.md", 215,
     "| 铁骑 | 第五十九回·段19 | 无 | — |",
     None, None, "「麾两翼铁骑」", "C10"),
    ("三国演义", "三国演义/名词列锦章节/059_第五十九回.md", 372,
     "| 英雄 | 第五十九回·段23 | 无 | — |",
     "兵之变化", "第五十九回·段23", "「兵之变化，固非一道也」", "—"),
    # ===== 红楼梦 1 行 =====
    ("红楼梦", "红楼梦/名词列锦章节/120_第120章.md", 693,
     "| 石头记 | 第120章·段落28 | 《石头记》 | C55 |",
     None, None, "「便要将这抄录的《石头记》给他看看」", None),
    # ===== 西游记 18 行 =====
    ("西游记", "西游记/名词列锦章节/008_第八回.md", 573,
     "| 南赡部洲 | 第8回·口舌凶场 | （承第一回正字；此处原文作\"南赠\"） | — |",
     None, None, "「但那南赠部洲者，贪淫乐祸，多杀多争」", "C23"),
    ("西游记", "西游记/名词列锦章节/008_第八回.md", 679,
     "| 福 | 第8回·福诗 | 六\"福\"字铺排 | C18 |",
     None, None, "「福圣光耀性尊前，福纳弥深远更绵」", None),
    ("西游记", "西游记/名词列锦章节/008_第八回.md", 680,
     "| 禄 | 第8回·禄诗 | 六\"禄\"字铺排 | C19 |",
     None, None, "「禄重如山彩凤鸣，禄随时泰视长庚」", None),
    ("西游记", "西游记/名词列锦章节/008_第八回.md", 681,
     "| 寿 | 第8回·寿诗 | 六\"寿\"字铺排 | C20 |",
     None, None, "「寿星献彩对如来．寿域光华自此开」", None),
    ("西游记", "西游记/名词列锦章节/025_第二十五回.md", 376,
     "| 楞严经 | 第25回·八戒语 | 《楞严经》 | C13 |",
     None, None, "「我只听得佛教中有卷《楞严经》」", None),
    ("西游记", "西游记/名词列锦章节/025_第二十五回.md", 377,
     "| 法华经 | 第25回·八戒语 | 《法华经》 | C13 |",
     None, None, "「我只听得佛教中有卷《楞严经》、《法华经》」", None),
    ("西游记", "西游记/名词列锦章节/025_第二十五回.md", 378,
     "| 孔雀经 | 第25回·八戒语 | 《孔雀经》 | C13 |",
     None, None, "「我只听得佛教中有卷《楞严经》、《法华经》、《孔雀经》」", None),
    ("西游记", "西游记/名词列锦章节/025_第二十五回.md", 379,
     "| 观音经 | 第25回·八戒语 | 《观音经》 | C13 |",
     None, None, "「我只听得佛教中有卷《楞严经》、《法华经》、《孔雀经》、《观音经》」", None),
    ("西游记", "西游记/名词列锦章节/025_第二十五回.md", 380,
     "| 金刚经 | 第25回·八戒语 | 《金刚经》 | C13 |",
     None, None, "「我只听得佛教中有卷《楞严经》、《法华经》、《孔雀经》、《观音经》、《金刚经》」", None),
    ("西游记", "西游记/名词列锦章节/067_第六十七回.md", 425,
     "| 两三合? 不录 | — | — | — |",
     "一顿饭", "第67回·八戒语", "「哄他一顿饭吃了」", "—"),
    ("西游记", "西游记/名词列锦章节/067_第六十七回.md", 548,
     "| 豺狼? 不录 | — | — | — |",
     "老猪魈", "第67回·变猪诗", "「未观今日老猪魈」", "—"),
    ("西游记", "西游记/名词列锦章节/068_第六十八回.md", 474,
     "| 肘? 不录 | — | — | — |",
     "锅灶", "第68回·会同馆", "「西房里有干净锅灶」", "—"),
    ("西游记", "西游记/名词列锦章节/069_第六十九回.md", 393,
     "| 二十四? 无 | — | — | — |",
     "半夜", "第69回·制药", "「至半夜，天街人静，万籁无声」", "—"),
    ("西游记", "西游记/名词列锦章节/072_第七十二回.md", 803,
     "| 外公 | 第72回·前回余 | （本回未出现，跨回线索） | — |",
     "姐姐", "第72回·濯垢泉", "「姐姐，我们洗了澡，来蒸那胖和尚吃去」", "—"),
    ("西游记", "西游记/名词列锦章节/078_第七十八回.md", 579,
     "| 御街 | 第78回·入朝 | （径奔朝中） | — |",
     "黄门官", "第78回·入朝", "「及到朝门外，见有黄门官」", "—"),
    ("西游记", "西游记/名词列锦章节/080_第八十回.md", 603,
     "| 衣裳 | 第80回·荒寺 | （参前回布袜衣裳） | — |",
     "半壁灯光", "第80回·荒寺", "「又只见半壁灯光明后院」", "—"),
    ("西游记", "西游记/名词列锦章节/080_第八十回.md", 649,
     "| 淅淅 | 第80回·妖风 | （顺风嘤嘤） | — |",
     "嘤嘤", "第80回·松林", "「忽听得嘤嘤的叫声」", "—"),
    ("西游记", "西游记/名词列锦章节/085_第八十五回.md", 321,
     "| 獐（？） | 第八十五回·妖洞口 | — | [待考] |",
     "小妖", "第八十五回·妖洞口", "「又见那左右手下有三四十个小妖摆列」", "[待考]"),
]

def cells(line):
    p = line.split('|')
    return [x.strip() for x in p[1:-1]]

def main(apply):
    # 按文件分组
    byfile = {}
    for it in FIX:
        byfile.setdefault(it[1], []).append(it)
    total_ok = True
    for path, items in byfile.items():
        fp = os.path.join(ROOT, path)
        with open(fp, encoding="utf-8") as fh:
            lines = fh.read().split('\n')
        before = len(lines)
        changes = []
        for (book, _, ln, old, c1, c2, c3, c4) in items:
            cur = lines[ln-1]
            if cur != old:
                print(f"[原串不命中] {os.path.basename(path)}:{ln}\n  期望: {old!r}\n  实际: {cur!r}")
                total_ok = False; continue
            cs = cells(old)
            assert len(cs) == 4, (path, ln, cs)
            new = [c1 if c1 is not None else cs[0],
                   c2 if c2 is not None else cs[1],
                   c3 if c3 is not None else cs[2],
                   c4 if c4 is not None else cs[3]]
            newline = "| " + " | ".join(new) + " |"
            # 第三列必须规范引文
            if not (new[2].startswith('「') and new[2].endswith('」')):
                print(f"[第三列非规范引文] {os.path.basename(path)}:{ln} -> {new[2]!r}")
                total_ok = False
            # 引文逐字可核
            prefix = re.match(r'(\d{3})_', os.path.basename(path)).group(1)
            if not qok(new[2], book, prefix):
                print(f"[引文不可核] {os.path.basename(path)}:{ln} -> {new[2]!r}")
                total_ok = False
            changes.append((ln, newline))
        # 行数守恒
        assert len(lines) == before
        if apply and total_ok:
            for ln, newline in changes:
                lines[ln-1] = newline
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write('\n'.join(lines))
            assert len(open(fp, encoding="utf-8").read().split('\n')) == before
        print(f"{'[写入]' if apply else '[预检]'} {os.path.basename(path)}: {len(changes)} 行, 行数 {before} 守恒")
    print("\n预检结果：" + ("全部通过 ✅" if total_ok else "存在问题 ❌（未写入）"))
    return total_ok

if __name__ == "__main__":
    apply = "--apply" in sys.argv
    ok = main(False)
    if apply and ok:
        print("\n===== 开始写入 =====")
        main(True)
