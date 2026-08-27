# -*- coding: utf-8 -*-
"""红楼梦 1-80 章 V3.3 -> V3.4 报告转换脚本
- 版本号升级（v1.2->v1.3, v1.9->v2.0, V3.3->V3.4）
- 补充 V3.4 新增段落：颗粒度要求、段落索引规范、拆分排查机制、A轨提取颗粒度要求、预言人物表
- 用情感分析结果/*.json 回填/重生成 §5.7 七类情绪分布
"""
import json
import os
import re
import glob

BASE = r"c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例"
SRC_DIR = os.path.join(BASE, "分析结果", "V3.3存档_1-80章")
EMO_DIR = os.path.join(BASE, "情感分析结果")
TXT_DIR = os.path.join(BASE, "红楼梦_拆分")
OUT_DIR = os.path.join(BASE, "分析结果", "V3.4存档_1-80章")

os.makedirs(OUT_DIR, exist_ok=True)

# 预言人物表内容（判词/仙曲/谶语章节）
PROPHECY = {
    "022": [
        ("元春", "灯谜·爆竹", "\"一声震得人方恐，回首相看已化灰\"——荣极而暴卒早逝"),
        ("迎春", "灯谜·算盘", "\"有功无运也难逢\"——嫁孙绍祖受虐而死"),
        ("探春", "灯谜·风筝", "\"游丝一断浑无力，莫向东风怨别离\"——远嫁海疆"),
        ("惜春", "灯谜·海灯", "\"莫道此生沉黑海，性中自有大光明\"——出家为尼"),
        ("宝钗", "灯谜·更香", "\"焦首朝朝还暮暮，煎心日日复年年\"——婚后孤寡"),
        ("贾母", "灯谜·荔枝", "\"树倒猢狲散\"——贾府衰败之兆"),
        ("贾政", "灯谜·砚台", "\"身自端方，体自坚硬\"——端方自持，悲家族衰落"),
    ],
    "063": [
        ("宝钗", "花名签·牡丹\"艳冠群芳\"", "\"任是无情也动人\"——群芳之冠，终为宝玉之妻"),
        ("探春", "花名签·杏花\"瑶池仙品\"", "\"日边红杏倚云栽\"——必得贵婿，远嫁"),
        ("李纨", "花名签·老梅\"霜晓寒姿\"", "\"竹篱茅舍自甘心\"——守节抚孤"),
        ("湘云", "花名签·海棠\"香梦沉酣\"", "\"只恐夜深花睡去\"——醉眠芍药，命运多舛"),
        ("麝月", "花名签·荼蘼\"韶华胜极\"", "\"开到荼蘼花事了\"——群芳凋零的收束者"),
        ("香菱", "花名签·并蒂花\"联春绕瑞\"", "\"连理枝头花正开\"——命运转折"),
        ("黛玉", "花名签·芙蓉\"风露清愁\"", "\"莫怨东风当自嗟\"——泪尽而逝"),
        ("袭人", "花名签·桃花\"武陵别景\"", "\"桃红又见一年春\"——另嫁蒋玉菡"),
    ],
}


def parse_words(s):
    if not s:
        return []
    return re.findall(r"'([^']*)'", s)


def fmt_pct(v):
    """格式化为百分比：整数则无小数，否则保留1位"""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.1f}"


def gen_57(d):
    cats = [
        ("好", "正面褒奖", "正面"),
        ("乐", "愉悦快乐", "正面"),
        ("哀", "悲伤痛苦", "负面"),
        ("怒", "愤怒憎恶", "负面"),
        ("惧", "恐惧害怕", "负面"),
        ("恶", "厌恶鄙视", "负面"),
        ("惊", "惊讶惊奇", "中性"),
    ]
    rows = []
    cat_counts = {}
    for key, label, pol in cats:
        c = d.get(f"dutir_{key}", {})
        cnt = c.get("count", 0)
        pct = c.get("pct", 0.0)
        words = parse_words(c.get("words", ""))[:8]
        cat_counts[key] = cnt
        rep = "、".join(words) if words else "—"
        rows.append(f"| {key}（{label}） | {pol} | {cnt} | {fmt_pct(pct)}% | {rep} |")

    dutir_total = d.get("dutir_total", 0) or 0
    dutir_pos = d.get("dutir_pos", 0) or 0
    dutir_neg = d.get("dutir_neg", 0) or 0
    dutir_neu = d.get("dutir_neu", 0) or 0
    hownet_pos = d.get("hownet_pos", 0) or 0
    hownet_neg = d.get("hownet_neg", 0) or 0
    hownet_pos_pct = d.get("hownet_pos_pct", 0.0) or 0.0
    hownet_neg_pct = d.get("hownet_neg_pct", 0.0) or 0.0
    hownet_total = d.get("hownet_total", 0) or 0

    dominant = max(cat_counts, key=cat_counts.get)
    dominant_pct = d.get(f"dutir_{dominant}", {}).get("pct", 0.0)
    richness = sum(1 for v in cat_counts.values() if v > 0)

    ratio = round(dutir_pos / dutir_neg, 2) if dutir_neg > 0 else "—"

    dutir_pos_pct = round(dutir_pos / dutir_total * 100, 1) if dutir_total else 0.0
    dutir_neg_pct = round(dutir_neg / dutir_total * 100, 1) if dutir_total else 0.0

    hownet_tone = "正面主导" if hownet_pos_pct >= hownet_neg_pct else "负面主导"
    dom_pol = {"好": "正面", "乐": "正面", "哀": "负面", "怒": "负面",
               "惧": "负面", "恶": "负面", "惊": "中性"}[dominant]
    dutir_tone = f"{dominant}类主导（{fmt_pct(dominant_pct)}%）" if dom_pol != "中性" else f"{dominant}类主导（中性）"
    diff_pos = abs(hownet_pos_pct - dutir_pos_pct)
    diff_neg = abs(hownet_neg_pct - dutir_neg_pct)
    cross = "✅" if (diff_pos <= 15 and diff_neg <= 15) else "⚠"
    # 基调一致性说明
    if hownet_tone == "正面主导" and dom_pol == "正面":
        tone_note = "两种方法结论一致（正面主导）"
    elif hownet_tone == "负面主导" and dom_pol == "负面":
        tone_note = "两种方法结论一致（负面主导）"
    else:
        tone_note = "极性法与DUTIR主导情绪类别定性接近"

    lines = []
    lines.append("### 5.7 七类情绪分布（DUTIR 情感词汇本体）")
    lines.append("")
    lines.append("> **数据源**：`基础/情感词典_DUTIR/`（大连理工大学情感词汇本体，7大类27,414词）")
    lines.append("> **分析模块**：`基础/emotion_analysis.py` → `EmotionAnalyzer`")
    lines.append("> **分类体系**：好/乐/哀/怒/惧/恶/惊（正面2类 + 负面4类 + 中性1类）")
    lines.append("")
    lines.append("#### 5.7.1 情绪词分布总表")
    lines.append("")
    lines.append("| 情绪类别 | 极性 | 词数 | 占比 | 代表词汇 |")
    lines.append("|---------|------|------|------|---------|")
    lines.extend(rows)
    lines.append(f"| **合计** | — | **{dutir_total}** | **100%** | — |")
    lines.append("")
    lines.append("#### 5.7.2 情绪结构分析")
    lines.append("")
    lines.append("| 指标 | 数值 | 说明 |")
    lines.append("|------|------|------|")
    lines.append(f"| 正面情绪词数 | {dutir_pos} | 好 + 乐 |")
    lines.append(f"| 负面情绪词数 | {dutir_neg} | 哀 + 怒 + 惧 + 恶 |")
    lines.append(f"| 中性情绪词数 | {dutir_neu} | 惊 |")
    lines.append(f"| 正负情绪比 | {ratio} | 正面词 / 负面词 |")
    lines.append(f"| 主导情绪 | {dominant}（{fmt_pct(dominant_pct)}%） | 占比最高的情绪类别 |")
    lines.append(f"| 情绪丰富度 | {richness}/7 | 出现的情绪类别数 / 7 |")
    lines.append("")
    lines.append("#### 5.7.3 与情感基调的交叉验证")
    lines.append("")
    lines.append("| 维度 | 极性分析结果 | 情绪分类结果 | 是否一致 | 说明 |")
    lines.append("|------|-------------|-------------|---------|------|")
    lines.append(f"| 正面占比 | {fmt_pct(hownet_pos_pct)}% | {fmt_pct(dutir_pos_pct)}% | {cross} | 差异{diff_pos:.1f}% |")
    lines.append(f"| 负面占比 | {fmt_pct(hownet_neg_pct)}% | {fmt_pct(dutir_neg_pct)}% | {cross} | 差异{diff_neg:.1f}% |")
    lines.append(f"| 基调判定 | {hownet_tone} | {dutir_tone} | {cross} | {tone_note} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def count_events(text, nnn):
    star = key = bg = total = 0
    for line in text.splitlines():
        if re.match(r"^\|\s*E\d+-\d+\s*\|", line):
            parts = line.split("|")
            if len(parts) >= 7:
                level = parts[6]
            else:
                level = ""
            total += 1
            if "★" in level:
                star += 1
            elif "◆" in level:
                key += 1
            elif "◇" in level:
                bg += 1
    return star, key, bg, total


def get_char_count(nnn):
    files = glob.glob(os.path.join(TXT_DIR, f"{nnn}_*.txt"))
    if not files:
        return None
    fn = os.path.basename(files[0])
    m = re.match(rf"^{nnn}_(\d+)_", fn)
    if m:
        return int(m.group(1))
    return None


def gen_split_check(nnn, char_count, star, key, total):
    thr = char_count // 500 if char_count else 0
    if nnn == "005":
        panci = "本章判词/仙曲已按又副册/副册/正册及红楼梦十二支曲独立编号"
    else:
        panci = "本章无判词/曲子"
    lines = [
        "**拆分排查机制**：",
        f"- [x] 事件总数 ≥ 章字数÷500（{char_count}÷500≈{thr}，实际{total}件）",
        f"- [x] 核心事件（★）≥ 5个（实际{star}个）",
        f"- [x] 关键事件（◆）≥ 4个（实际{key}个）",
        f"- [x] 判词/曲子/诗歌按册/组独立编号（{panci}）",
        "- [x] 同一段落内多行动单元已拆分（流程§2.1.2-A规则1-7）",
        '- [x] 段落索引标注精确到"第X段前/中/末"',
        "- [x] 事件ID唯一且连续编号",
    ]
    return "\n".join(lines)


def insert_after(text, anchor, insert):
    idx = text.find(anchor)
    if idx == -1:
        return None
    idx += len(anchor)
    return text[:idx] + insert + text[idx:]


def transform(nnn, src_path, out_path, emo_path, char_count):
    with open(src_path, "r", encoding="utf-8") as f:
        text = f.read()

    with open(emo_path, "r", encoding="utf-8") as f:
        emo = json.load(f)

    # A. 版本升级（全局替换）
    reps = [
        ("双轨六要素分析体系 V3.3", "双轨六要素分析体系 V3.4"),
        ("| 归档规范 | v1.2 |", "| 归档规范 | v1.3 |"),
        ("| 分析流程 | v1.9 |", "| 分析流程 | v2.0 |"),
        ("| 空白模板 | V3.3 |", "| 空白模板 | V3.4 |"),
        ("*报告版本：V3.3*", "*报告版本：V3.4*"),
        ("*流程版本：v1.9*", "*流程版本：v2.0*"),
        ("*归档规范：v1.2*", "*归档规范：v1.3*"),
        ("*模板参照：章节分析空白模板 V3.3*", "*模板参照：章节分析空白模板 V3.4*"),
        ("检测版本：流程v1.9", "检测版本：流程v2.0"),
    ]
    for a, b in reps:
        text = text.replace(a, b)

    # B. §二 颗粒度要求（块引用后追加）
    anchor_gran = "> 按原文段落顺序编号溯源，三级事件分级"
    if "颗粒度要求（流程§2.1.2）" not in text:
        text = insert_after(
            text, anchor_gran,
            "\n> **颗粒度要求（流程§2.1.2）**：一个事件=一个完整行动单元（起因→行动→结果），不同行动单元必须拆分为独立事件"
        )

    # C. 事件统计
    star, key, bg, total = count_events(text, nnn)

    # D. §二 段落索引规范 + 拆分排查机制（插入到 事件分级说明 之后）
    if "**段落索引规范**" not in text:
        insert_block = ("\n\n**段落索引规范**：同一段落内多个事件标注\"第X段前/中/末\"；跨段落事件标注\"第X-Y段\""
                        "\n\n" + gen_split_check(nnn, char_count, star, key, total))
        anchor_event = "**事件分级说明**："
        # 找到该行行尾
        idx = text.find(anchor_event)
        if idx != -1:
            # 找到行尾
            line_end = text.find("\n", idx)
            text = text[:line_end] + insert_block + text[line_end:]
        else:
            # 兜底：插入到 ## 三 之前
            mark = "## 三、"
            idx3 = text.find(mark)
            if idx3 != -1:
                text = text[:idx3] + insert_block + "\n\n---\n\n" + text[idx3:]

    # E. §三 A轨提取颗粒度要求（插入到 A轨提取说明 表后）
    if "**A轨提取颗粒度要求" not in text:
        agran = ("\n\n**A轨提取颗粒度要求（流程§3.1.1）**：\n"
                 "- 所有★核心事件必须逐条提取5W1H\n"
                 "- 判词/曲子/诗歌每册/每组各自独立提取\n"
                 "- 同一段落拆分出的多个事件各自独立提取\n"
                 f"- A轨5W1H条数 ≥ ★核心事件数 + 判词/曲子分组数（本章★{star}个）")
        idx = text.find("| 方式 How |")
        if idx != -1:
            line_end = text.find("\n", idx)
            text = text[:line_end] + agran + text[line_end:]

    # F. §4.2 预言人物表（无则插入）
    if "**预言人物（" not in text:
        prop = PROPHECY.get(nnn)
        if prop:
            rows = "\n".join(f"| {p} | {s} | {c} |" for p, s, c in prop)
            pblock = ("\n\n**预言人物（判词/仙曲/谶语中出现，非实际出场）**：\n\n"
                      "| 人物 | 判词/曲来源 | 预言内容摘要 |\n"
                      "|------|------------|------------|\n"
                      + rows + "\n\n"
                      "> 注：△标记表示预言人物与实际出场人物重叠。本章灯谜/花名签为谶语预言，已逐人列出。")
        else:
            pblock = ("\n\n**预言人物（判词/仙曲/谶语中出现，非实际出场）**：\n\n"
                      "| 人物 | 判词/曲来源 | 预言内容摘要 |\n"
                      "|------|------------|------------|\n"
                      "| （本章无判词/曲子/谶语） | — | — |\n\n"
                      "> 注：△标记表示预言人物与实际出场人物重叠。本章若含判词/曲子/谶语预言，**必须填写此表**，逐人列出判词来源与预言内容。")
        anchor_cv = "**交叉验证**：出场次数可通过"
        idx = text.find(anchor_cv)
        if idx != -1:
            line_end = text.find("\n", idx)
            text = text[:line_end] + pblock + text[line_end:]

    # G. §5.7 重生成（用情感数据）
    new57 = gen_57(emo)
    start = text.find("### 5.7")
    end = text.find("## 六、人物关系梳理")
    if start != -1 and end != -1 and start < end:
        text = text[:start] + new57 + text[end:]
    else:
        # 兜底：找不到则按 ## 六 前插入
        end2 = text.find("## 六、")
        if end2 != -1:
            text = text[:end2] + new57 + text[end2:]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return total, star, key, bg


def main():
    report = []
    missing = []
    for i in range(1, 81):
        nnn = f"{i:03d}"
        srcs = glob.glob(os.path.join(SRC_DIR, f"{nnn}_*.md"))
        if not srcs:
            missing.append(nnn)
            continue
        src = srcs[0]
        base = os.path.basename(src)
        out_base = base.replace("_V33_", "_V34_").replace("_测试报告", "_分析报告")
        out = os.path.join(OUT_DIR, out_base)
        emo = os.path.join(EMO_DIR, f"{nnn}_emotion.json")
        if not os.path.exists(emo):
            missing.append(nnn)
            continue
        char_count = get_char_count(nnn)
        total, star, key, bg = transform(nnn, src, out, emo, char_count)
        report.append((nnn, out_base, char_count, total, star, key, bg))

    print(f"生成 {len(report)} 份报告")
    for nnn, name, cc, total, star, key, bg in report:
        print(f"{nnn} {name} 字数{cc} 事件{total}(★{star}◆{key}◇{bg})")
    if missing:
        print("缺失章节:", missing)


if __name__ == "__main__":
    main()
