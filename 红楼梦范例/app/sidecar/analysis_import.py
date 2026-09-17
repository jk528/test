#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 分析产物导入器 —— 把既有的 120 章 V3.4 分析报告「回灌」进 SQLite 主库。

设计要点（与 V1.0 一体化方案的「统一锚点模型」一致）：

  锚点 = (book_id, chapter_idx, line_start, line_end, char_start?, char_end?)
  **物理行号是唯一权威**。红楼梦.txt 的物理行与「红楼梦_拆分/」的自然段
  1:1 对齐（实测第 1 章 67 行 = 67 段），因此行号可直接对应到正文位置。

  但报告里的「段落索引」（第 N 段）与物理行**不是同一口径**（报告的段号把
  诗行/标题的计数方式不同，实测第 1 章报告最大段号 37，而物理行 67），
  所以**不能直接换算**。本模块采用三级锚定，并在 anchor_precision 里
  如实标注精度，杜绝「看起来精确其实错位」：

    1. quote    —— 事件摘要里的引号原文，在章内经精确字符串匹配命中 → 精确
    2. cooccur  —— 取报告段号估计行附近，含参与人物最多的行 → 近似
    3. para     —— 仅用报告段号估计（章首 + 段号 - 1） → 最粗
  最后做一次**单调修复**（事件按段号顺序递增，锚点不得回退），
  保证时间线在正文里是顺序的。

数据源：
  - 分析结果/**/NNN_*V34*.md  —— 事件接入清单 / 人物关系梳理 / 伏笔与线索追踪
  - 分析结果/v34_extract_v2.json —— 章级统计 + char_list + foreshadows
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────── 表头（120 份报告实测完全一致，勿随意放宽） ───────────────────

HDR_EVENT = "事件ID | 段落索引 | 事件摘要 | 涉及人物 | 情感倾向 | 事件级别 | 溯源状态"
HDR_RELATION = "角色A | 关系 | 角色B | 本章互动"
HDR_FORESHADOW = "章回 | 线索内容 | 类型 | 状态"

SECTION_EVENT = "二、事件接入清单"
SECTION_RELATION = "六、人物关系梳理"
SECTION_FORESHADOW = "伏笔与线索追踪"

# 事件级别：★核心（推动主线）｜◆关键（人物出场/关系建立）｜◇背景（环境/次要情节）
LEVEL_MAP = {"★": "主线", "◆": "支线", "◇": "细节"}

# 引号：报告里中英文引号混用，统一识别
QUOTE_PAIRS = [("\u201c", "\u201d"), ("\u300c", "\u300d"), ('"', '"'), ("\u2018", "\u2019")]

# 核心人物的别名表（保守表：只收录**确定无歧义**的称谓；
# 「二爷」「太太」「娘娘」这类会大面积误伤，刻意不收）
ALIAS_SEED: Dict[str, List[str]] = {
    "贾宝玉": ["宝玉", "宝二爷", "怡红公子", "绛洞花王"],
    "林黛玉": ["黛玉", "颦儿", "颦卿", "林妹妹", "潇湘妃子", "林姑娘"],
    "薛宝钗": ["宝钗", "宝姐姐", "蘅芜君", "宝姑娘"],
    "王熙凤": ["凤姐", "凤姐儿", "琏二奶奶", "凤辣子"],
    "贾母": ["史太君", "老太太", "老祖宗"],
    "贾政": ["政老爷", "存周"],
    "贾赦": ["赦老爷"],
    "贾琏": ["琏二爷"],
    "贾探春": ["探春", "三姑娘", "蕉下客"],
    "贾迎春": ["迎春", "二姑娘"],
    "贾惜春": ["惜春", "四姑娘", "藕榭"],
    "史湘云": ["湘云", "枕霞旧友", "云妹妹"],
    "贾元春": ["元春", "元妃"],
    "李纨": ["宫裁", "稻香老农"],
    "秦可卿": ["可卿", "兼美"],
    "妙玉": [],
    "袭人": ["花袭人"],
    "晴雯": [],
    "平儿": [],
    "紫鹃": [],
    "鸳鸯": [],
    "香菱": ["英莲", "甄英莲", "秋菱"],
    "刘姥姥": ["刘老老", "姥姥"],
    "贾雨村": ["雨村", "贾化", "时飞"],
    "甄士隐": ["士隐"],
    "薛蟠": ["呆霸王", "薛文龙"],
    "贾珍": [],
    "贾蓉": [],
    "贾环": [],
    "尤氏": [],
    "王夫人": [],
    "邢夫人": [],
    "贾巧姐": ["巧姐", "巧姐儿"],
}


# ─────────────────────────── 报告定位与表格解析 ───────────────────────────

def find_reports(analysis_dir: str) -> Dict[int, str]:
    """返回 {章号(1-based): 报告路径}。同名冲突时优先顶层目录。"""
    out: Dict[int, str] = {}
    for root, _dirs, files in os.walk(analysis_dir):
        for fn in files:
            if "V34" not in fn or not fn.endswith(".md"):
                continue
            m = re.match(r"^(\d{3})_", fn)
            if not m:
                continue
            no = int(m.group(1))
            path = os.path.join(root, fn)
            # 顶层（路径层级更浅）优先，避免归档目录覆盖最新版
            if no not in out or path.count(os.sep) < out[no].count(os.sep):
                out[no] = path
    return out


def _table_rows(block: str, header: str) -> List[List[str]]:
    """从 markdown 表格块中取数据行（跳过表头与分隔线）。"""
    rows: List[List[str]] = []
    seen_header = False
    for line in block.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        joined = " | ".join(cells)
        if joined == header:
            seen_header = True
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if seen_header:
            rows.append(cells)
    return rows


def _section(text: str, start_title: str, end_title: Optional[str]) -> str:
    i = text.find(start_title)
    if i < 0:
        return ""
    j = text.find(end_title, i) if end_title else -1
    return text[i:j if j > 0 else len(text)]


def _digits(s: str) -> Optional[int]:
    """从「第7段中」「第1-2段」里取出起始段号。"""
    m = re.search(r"第\s*(\d+)\s*段", s or "")
    return int(m.group(1)) if m else None


def parse_report(path: str) -> Dict[str, Any]:
    """解析单章报告：事件 / 人物关系 / 伏笔。"""
    text = open(path, encoding="utf-8", errors="replace").read()

    events = []
    for cells in _table_rows(_section(text, SECTION_EVENT, "## 三、"), HDR_EVENT):
        if len(cells) < 6:
            continue
        events.append({
            "uid": cells[0],
            "para_raw": cells[1],
            "para_idx": _digits(cells[1]),
            "summary": cells[2],
            "participants": [p for p in re.split(r"[/、,，]", cells[3]) if p.strip()],
            "tone": normalize_tone(cells[4]),
            "level": LEVEL_MAP.get(cells[5].strip()[:1], "细节"),
        })

    relations = []
    for cells in _table_rows(_section(text, SECTION_RELATION, "## 七、"),
                             HDR_RELATION):
        if len(cells) < 4 or cells[0] in ("角色A", "章回"):
            continue
        relations.append({"a": cells[0], "relation": cells[1],
                          "b": cells[2], "evidence": cells[3]})

    foreshadows = []
    block = _section(text, SECTION_FORESHADOW, "\n---")
    for cells in _table_rows(block, HDR_FORESHADOW):
        if len(cells) < 4:
            continue
        status_raw = cells[3]
        foreshadows.append({
            "content": cells[1],
            "kind": cells[2],
            "status": "closed" if "已呼应" in status_raw else "open",
            "status_raw": status_raw,
        })
    return {"events": events, "relations": relations, "foreshadows": foreshadows}


# ─────────────────────────────── 锚点计算 ───────────────────────────────

def _quotes(text: str, min_len: int = 3) -> List[str]:
    """抽取文本中的引号内容（用于正文精确锚定），按长度降序。"""
    found: List[str] = []
    for a, b in QUOTE_PAIRS:
        if a == b:
            for m in re.finditer(re.escape(a) + r"([^" + re.escape(a) + r"]{2,40})" + re.escape(b), text):
                found.append(m.group(1).strip())
        else:
            for m in re.finditer(re.escape(a) + r"([^" + re.escape(b) + r"]{2,40})" + re.escape(b), text):
                found.append(m.group(1).strip())
    found.sort(key=len, reverse=True)
    return [q for q in found if len(q) >= min_len]


class ChapterAnchorResolver:
    """把「报告里的段落/引文」落到**物理行号**上。

    章节范围由 chapters 表给出（start_line/end_line 均含端、0 基物理行）。
    """

    def __init__(self, lines: List[str], chapters: List[Dict[str, Any]]):
        self.lines = lines
        self.chapters = chapters

    def chapter_range(self, chapter_idx: int) -> Tuple[int, int]:
        for c in self.chapters:
            if int(c["idx"]) == chapter_idx:
                return int(c["start_line"]), int(c["end_line"])
        return 0, len(self.lines) - 1

    def chapter_text(self, chapter_idx: int) -> str:
        s, e = self.chapter_range(chapter_idx)
        return "\n".join(self.lines[s:e + 1])

    @staticmethod
    def _offset_to_line(chapter_text: str, start_line: int, off: int) -> int:
        return start_line + chapter_text.count("\n", 0, off)

    def by_quote(self, chapter_idx: int, summary: str,
                 min_len: int = 3) -> Optional[Tuple[int, int, int]]:
        """用摘要中的引文精确锚定 → (line, char_start, char_end)。"""
        ctext = self.chapter_text(chapter_idx)
        s, _e = self.chapter_range(chapter_idx)
        for q in _quotes(summary, min_len):
            off = ctext.find(q)
            if off >= 0:
                line = self._offset_to_line(ctext, s, off)
                col = off - (ctext.rfind("\n", 0, off) + 1)
                return line, col, col + len(q)
        return None

    def by_para_and_cast(self, chapter_idx: int, para_idx: Optional[int],
                         participants: List[str],
                         surface_of: Dict[str, str]) -> Tuple[int, str]:
        """段号估计 + 参与人物共现校验 → (line, precision)。"""
        s, e = self.chapter_range(chapter_idx)
        if not para_idx:
            return s, "para"
        est = min(max(s + para_idx - 1, s), e)
        surfaces = [surface_of[p] for p in participants if p in surface_of]
        if not surfaces:
            return est, "para"
        best_line, best_score = None, 0
        for line in range(max(s, est - 15), min(e, est + 15) + 1):
            body = self.lines[line]
            hit = sum(1 for sf in surfaces if sf and sf in body)
            if hit > best_score:
                best_line, best_score = line, hit
        if best_line is None or best_score == 0:
            return est, "para"
        return best_line, "cooccur"

    def scan_surfaces(self, chapter_idx: int, surfaces: List[str]
                      ) -> List[Dict[str, Any]]:
        """在章内扫描一组称谓，返回出现位置（最长匹配优先，避免子串重复计数）。"""
        s, e = self.chapter_range(chapter_idx)
        ordered = sorted(set(x for x in surfaces if x), key=len, reverse=True)
        out: List[Dict[str, Any]] = []
        for line in range(s, e + 1):
            body = self.lines[line]
            if not body:
                continue
            taken: List[Tuple[int, int]] = []
            for sf in ordered:
                start = 0
                while True:
                    i = body.find(sf, start)
                    if i < 0:
                        break
                    j = i + len(sf)
                    if not any(i < b and a < j for a, b in taken):
                        taken.append((i, j))
                        out.append({"line": line, "char_start": i,
                                    "char_end": j, "surface": sf})
                    start = i + 1
        return out


# ─────────────────────────── 人物表的构建 ───────────────────────────

def _alias_to_canon() -> Dict[str, str]:
    return {a: c for c, al in ALIAS_SEED.items() for a in al}


def _usable_name(name: str) -> bool:
    """人物名表里有谱系人名与「作者（虚构叙述者）」这类非人物条目，先筛掉。"""
    if not name or len(name) > 6:
        return False
    if any(ch in name for ch in "（）()·、/：:　 \u3000"):
        return False
    if not any("\u4e00" <= ch <= "\u9fff" for ch in name):
        return False
    return True


def build_alias_map(character_names: List[str]) -> Dict[str, List[str]]:
    """把别名种子 + 人物名表合成 {canonical: [别名…]}。

    **必须做别名归并**：`基础/红楼梦人物名.txt` 里「宝玉」「黛玉」「凤姐」
    「雨村」等**本身就作为独立条目存在**，若不归并，正文扫描会把同一人
    拆成两个实体（实测「贾宝玉」4072 次 + 「宝玉」3966 次重复计数）。
    规则：凡是别名种子中某人的别名，一律收回该规范名下，不再单列。
    """
    rev = _alias_to_canon()
    out: Dict[str, List[str]] = {c: list(dict.fromkeys(al)) for c, al in ALIAS_SEED.items()}
    for name in character_names:
        if not _usable_name(name):
            continue
        if name in rev:            # 是别人的别名 → 不单列
            continue
        out.setdefault(name, [])
    return out


def normalize_tone(raw: str) -> str:
    """报告的情感倾向写法高度自由（实测 56 种），归一到三类。"""
    t = (raw or "").strip()
    if t.startswith("正面"):
        return "正面"
    if t.startswith("负面"):
        return "负面"
    if t.startswith("中性"):
        return "中性"
    return "其他"


def surface_owner_map(alias_map: Dict[str, List[str]]) -> Dict[str, str]:
    """{称谓: canonical}，用于「参与人物 → 正文带语」的反查。

    含**别名 → 规范名**的映射：报告「涉及人物」列偶尔也会写别名（如「凤姐」），
    归并后同样能定位到正文。
    """
    out: Dict[str, str] = {}
    for canon, aliases in alias_map.items():
        out[canon] = canon
        for a in aliases:
            out.setdefault(a, canon)
    return out


# ─────────────────────────────── 主流程 ───────────────────────────────

def import_analysis(store, book_id: str, text: str, chapters: List[Dict[str, Any]],
                    analysis_dir: str) -> Dict[str, Any]:
    """把 120 章 V3.4 报告导入 events / entities / entity_mentions /
    foreshadows / entity_relations。**整书替换**，可重复执行（幂等）。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    reports = find_reports(analysis_dir)
    resolver = ChapterAnchorResolver(lines, chapters)

    # 章号（1-based，取自文件名）→ chapter_idx（0-based）
    no_to_idx = {int(c.get("no", i + 1)): i for i, c in enumerate(chapters)}
    # 章节表若没有 no 字段，退化为顺序对应
    if all("no" not in c for c in chapters):
        no_to_idx = {i + 1: i for i in range(len(chapters))}

    extract: Dict[int, Dict[str, Any]] = {}
    jpath = os.path.join(analysis_dir, "v34_extract_v2.json")
    if os.path.isfile(jpath):
        for item in json.load(open(jpath, encoding="utf-8")):
            extract[int(item["no"])] = item

    # ① 人物规范名：报告人物名表 + 抽取 JSON 的 char_list + 事件参与者
    canon_pool: List[str] = []
    base_names = _load_character_names(analysis_dir)
    canon_pool.extend(base_names)
    for item in extract.values():
        for ch in item.get("char_list", []) or []:
            if ch.get("name"):
                canon_pool.append(ch["name"])
    alias_map = build_alias_map(list(dict.fromkeys(canon_pool)))
    owner = surface_owner_map(alias_map)

    # ② 逐章解析事件 / 关系 / 伏笔（先落到行号）
    events: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    foreshadows: List[Dict[str, Any]] = []
    stats_prec = {"quote": 0, "cooccur": 0, "para": 0}
    missing: List[int] = []

    for no in sorted(reports):
        ci = no_to_idx.get(no)
        if ci is None:
            continue
        rep = parse_report(reports[no])
        if not rep["events"]:
            missing.append(no)
        # 单调修复：同章内事件锚点不得回退
        last = -1
        for ev in rep["events"]:
            q = resolver.by_quote(ci, ev["summary"])
            if q:
                line, cs, ce = q
                prec = "quote"
            else:
                line, prec = resolver.by_para_and_cast(
                    ci, ev["para_idx"], ev["participants"], owner)
                cs = ce = None
            if line < last:
                line = last
            last = line
            stats_prec[prec] += 1
            events.append({
                "uid": ev["uid"], "chapter_idx": ci, "line_start": line,
                "line_end": line, "summary": ev["summary"], "tone": ev["tone"],
                "level": ev["level"], "participants": ev["participants"],
                "char_start": cs, "char_end": ce, "precision": prec,
                "para_raw": ev["para_raw"],
            })
        for rel in rep["relations"]:
            relations.append({"chapter_idx": ci, **rel})
        for fs in rep["foreshadows"]:
            f_line, f_prec = _locate_foreshadow(resolver, ci, fs["content"], owner)
            foreshadows.append({
                "chapter_idx": ci, "line": f_line, "precision": f_prec, **fs,
            })

    # ③ 人物出场：正文扫描（精确锚点，逐个称谓）
    entity_rows: List[Dict[str, Any]] = []
    mention_rows: List[Dict[str, Any]] = []
    for canon, aliases in alias_map.items():
        surfaces = [canon] + [a for a in aliases if a != canon]
        mentions: List[Dict[str, Any]] = []
        for ci in range(len(chapters)):
            for hit in resolver.scan_surfaces(ci, surfaces):
                mentions.append({"chapter_idx": ci, **hit})
        if not mentions:
            entity_rows.append({"canonical": canon, "aliases": aliases,
                                "first_chapter": None, "appear_count": 0,
                                "mentions": []})
            continue
        first_ch = min(m["chapter_idx"] for m in mentions)
        entity_rows.append({"canonical": canon, "aliases": aliases,
                            "first_chapter": first_ch,
                            "appear_count": len(mentions),
                            "mentions": mentions})
    # 只保留至少出现 1 次的人物（362 名表里多数是谱系人名，正文不出现）
    entity_rows = [e for e in entity_rows if e["appear_count"] > 0]
    entity_rows.sort(key=lambda e: (-e["appear_count"], e["canonical"]))
    name_to_id = {e["canonical"]: i + 1 for i, e in enumerate(entity_rows)}
    for e in entity_rows:
        eid = name_to_id[e["canonical"]]
        e["entity_id"] = eid
        for m in e["mentions"]:
            mention_rows.append({"entity_id": eid, **m})

    # ④ 抽取 JSON 的伏笔补入（带「预计回收章节」，用于起↔收跳转）
    for no, item in sorted(extract.items()):
        ci = no_to_idx.get(no)
        if ci is None:
            continue
        rows = item.get("foreshadows") or []
        for row in rows:
            if not isinstance(row, list) or len(row) < 3:
                continue
            if row[0] == "伏笔内容":
                continue
            content, kind, payoff = row[0], row[1], row[2]
            if any(f["content"] == content and f["chapter_idx"] == ci
                   for f in foreshadows):
                continue
            line, prec = _locate_foreshadow(resolver, ci, content, owner)
            foreshadows.append({
                "chapter_idx": ci, "line": line, "precision": prec,
                "content": content, "kind": kind, "status": "open",
                "status_raw": f"预计回收：{payoff}", "payoff_chapter": _payoff_no(payoff),
            })

    result = _write_all(store, book_id, events, entity_rows, mention_rows,
                        foreshadows, relations, no_to_idx)
    result.update({
        "reports": len(reports),
        "reports_without_events": missing,
        "anchor_precision": stats_prec,
        "precision_pct": {
            k: (round(v * 100.0 / max(sum(stats_prec.values()), 1), 1))
            for k, v in stats_prec.items()},
        "analysis_dir": analysis_dir,
    })
    return result


def _load_character_names(analysis_dir: str) -> List[str]:
    """从项目 `基础/红楼梦人物名.txt` 读人物名表（分析目录的兄弟目录）。"""
    root = os.path.dirname(os.path.abspath(analysis_dir))
    p = os.path.join(root, "基础", "红楼梦人物名.txt")
    if not os.path.isfile(p):
        return []
    return [l.strip().lstrip("\ufeff") for l in open(p, encoding="utf-8",
                                                     errors="replace")
            if l.strip()]


def _locate_foreshadow(resolver: ChapterAnchorResolver, ci: int, content: str,
                       owner: Dict[str, str]) -> Tuple[int, str]:
    # 伏笔线索多为「绛珠"还泪"之约」这类 2 字引文，故阈值放宽到 2
    q = resolver.by_quote(ci, content, min_len=2)
    if q:
        return q[0], "quote"
    s, _e = resolver.chapter_range(ci)
    return s, "chapter"


def _payoff_no(payoff: str) -> Optional[int]:
    """「第3-98章」→ 98（取区间末端，代表最晚回收点）；「第120章」→ 120。"""
    nums = [int(x) for x in re.findall(r"\d+", payoff or "")]
    return nums[-1] if nums else None


def _write_all(store, book_id: str, events, entity_rows, mention_rows,
               foreshadows, relations, no_to_idx) -> Dict[str, Any]:
    """整书替换写入（先清后插，import 可重复执行）。"""
    c = store.conn
    c.execute("DELETE FROM events WHERE book_id=?", (book_id,))
    c.execute("DELETE FROM entity_mentions WHERE book_id=?", (book_id,))
    c.execute("DELETE FROM entities WHERE book_id=?", (book_id,))
    c.execute("DELETE FROM foreshadows WHERE book_id=?", (book_id,))
    c.execute("DELETE FROM entity_relations WHERE book_id=?", (book_id,))

    for ev in events:
        c.execute(
            "INSERT INTO events(book_id, level, chapter_idx, line_start, "
            "line_end, summary, w5h1_json, participants_json, event_uid, tone, "
            "anchor_precision, char_start, char_end, para_raw) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (book_id, ev["level"], ev["chapter_idx"], ev["line_start"],
             ev["line_end"], ev["summary"], None,
             json.dumps(ev["participants"], ensure_ascii=False), ev["uid"],
             ev["tone"], ev["precision"], ev["char_start"], ev["char_end"],
             ev["para_raw"]))
    for e in entity_rows:
        eid = e["entity_id"]
        c.execute(
            "INSERT INTO entities(id, book_id, canonical, aliases_json, "
            "first_chapter, appear_count, profile_md, portrait_path) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (eid, book_id, e["canonical"],
             json.dumps(e["aliases"], ensure_ascii=False), e["first_chapter"],
             e["appear_count"], None, None))
    for m in mention_rows:
        c.execute(
            "INSERT INTO entity_mentions(entity_id, book_id, chapter_idx, "
            "line_start, char_start, char_end, surface) VALUES(?,?,?,?,?,?,?)",
            (m["entity_id"], book_id, m["chapter_idx"], m["line"], 
             m["char_start"], m["char_end"], m["surface"]))
    for f in foreshadows:
        c.execute(
            "INSERT INTO foreshadows(book_id, setup_chapter, setup_line, "
            "payoff_chapter, payoff_line, note, status, content, kind, "
            "anchor_precision, setup_char_start, setup_char_end, payoff_raw) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (book_id, f["chapter_idx"], f["line"],
             (no_to_idx.get(f.get("payoff_chapter"), None)
              if f.get("payoff_chapter") else None),
             None, f.get("status_raw"), f["status"], f["content"], f["kind"],
             f["precision"], None, None, f.get("status_raw")))
    for r in relations:
        c.execute(
            "INSERT INTO entity_relations(book_id, chapter_idx, entity_a, "
            "entity_b, relation, evidence) VALUES(?,?,?,?,?,?)",
            (book_id, r["chapter_idx"], r["a"], r["b"], r["relation"],
             r["evidence"]))
    c.commit()
    return {
        "events": len(events), "entities": len(entity_rows),
        "mentions": len(mention_rows), "foreshadows": len(foreshadows),
        "relations": len(relations),
    }
