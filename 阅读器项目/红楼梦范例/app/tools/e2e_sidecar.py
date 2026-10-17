#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过真实 stdio NDJSON 协议端到端验证 sidecar（M1~M4.5 全 29 个方法契约）。

重点：
- stdout 必须只有 NDJSON（任何日志混入都会让 Rust 侧解析失败）
- 新增/修复的方法：index_status / upsert_emotions / maintenance
- 情感持久化往返：写库 → 读库，字级 word_spans 不丢
- 标注 CRUD 往返
- M4 全景分析：回灌 120 章报告 → 事件/人物/伏笔/关系的数量与锚点自洽
"""
import json
import os
import subprocess
import sys

class _Tee:
    """终端不回显 stdout 时，把报告同时落盘（app/.temp/e2e_sidecar_report.txt）。"""

    def __init__(self, path, inner):
        self.f = open(path, "w", encoding="utf-8")
        self.inner = inner

    def write(self, s):
        self.f.write(s)
        try:
            self.inner.write(s)
        except Exception:
            pass

    def flush(self):
        self.f.flush()


APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout = _Tee(os.path.join(APP, ".temp", "e2e_sidecar_report.txt"), sys.stdout)
SIDE = os.path.join(APP, "sidecar", "honglou_sidecar.py")
PY = os.path.join(os.environ["USERPROFILE"], ".venvs", "honglou", "Scripts", "python.exe")
BOOK = os.path.abspath(os.path.join(APP, "..", "红楼梦.txt"))

proc = subprocess.Popen(
    [PY, SIDE],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    text=True, encoding="utf-8", bufsize=1,
)

_rid = [0]
errors = []
nonjson = []


def call(method, params=None):
    _rid[0] += 1
    rid = _rid[0]
    proc.stdin.write(json.dumps({"id": rid, "method": method,
                                 "params": params or {}}) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError(f"{method}: sidecar 无响应（进程可能已退出）")
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        nonjson.append((method, line[:200]))
        raise RuntimeError(f"{method}: stdout 混入非 JSON 内容 -> {line[:120]!r}")
    if "error" in r:
        return {"__error__": r["error"]}
    return r.get("result")


def check(name, cond, detail=""):
    mark = "✅" if cond else "❌"
    if not cond:
        errors.append(f"{name}: {detail}")
    print(f"  {mark} {name}" + (f"  {detail}" if detail else ""))
    return cond


print("=" * 70)
print("一、基础与协议")
print("=" * 70)
r = call("ping")
check("ping", r["version"] == "0.6.0-m4.6", f"version={r['version']} python={r['python']}")

r = call("chapter_outline", {"path": BOOK})
check("chapter_outline", r["chapter_count"] == 120 and r["total_lines"] == 3367,
      f"{r['chapter_count']} 章 / {r['total_lines']} 行")

r = call("db_status")
check("db_status", r["vec_ready"] and r["llm_configured"],
      f"tables={len(r['tables'])} vec={r['vec_ready']} llm={r['llm_configured']}")

r = call("no_such_method")
check("未知方法返回 -32601", r.get("__error__", {}).get("code") == -32601)

print()
print("=" * 70)
print("二、情感分析（M2 引擎）")
print("=" * 70)
r = call("analyze_sentiment", {"text": "今日非常开心快乐。\n宝玉十分悲伤恐惧痛苦。"})
ps = r["paragraphs"]
check("段落级七类", ps[0]["dutir_top"] == "乐" and ps[1]["dutir_top"] == "哀",
      f"top={ps[0]['dutir_top']}/{ps[1]['dutir_top']} pol={ps[0]['polarity']}/{ps[1]['polarity']}")
check("字级 word_spans 非空", len(ps[1]["word_spans"]) >= 2,
      f"{len(ps[1]['word_spans'])} 个: {[w['word'] for w in ps[1]['word_spans']]}")

r = call("analyze_chapters", {"text": open(BOOK, encoding="utf-8").read(),
                              "chapters": json.loads(json.dumps(
                                  call("chapter_outline", {"path": BOOK})["chapters"]))})
ce = r["chapter_emotions"]
check("批量章节情绪", len(ce) == 120, f"{len(ce)} 章，第1章={ce[0]['dutir_top']}")

print()
print("=" * 70)
print("三、主库：书目与章节")
print("=" * 70)
text = open(BOOK, encoding="utf-8").read()
r = call("save_book", {"title": "红楼梦", "source_path": BOOK, "text": text})
bid = r["book_id"]
check("save_book（内容哈希 book_id）", r["chapters"] == 120,
      f"book_id={bid} chapters={r['chapters']} lines={r['total_lines']}")

r = call("get_book", {"book_id": bid})
check("get_book", r["book"] is not None and len(r["chapters"]) == 120,
      f"title={r['book']['title']} chapters={len(r['chapters'])}")

print()
print("=" * 70)
print("四、情感持久化往返（本次修复重点）")
print("=" * 70)
TID = bid + "-e2e-tmp"  # 独立测试书：不碰真实预处理数据
rows = [
    {"line_start": 100, "line_end": 100, "dutir_top": "哀", "polarity": -0.5,
     "intensity": 0.2, "weights": {"哀": 3},
     "word_spans": [{"start": 4, "end": 6, "emotion": "哀", "word": "悲伤"}]},
    {"line_start": 101, "line_end": 101, "dutir_top": "乐", "polarity": 1.0,
     "intensity": 0.3, "weights": {"乐": 2}, "word_spans": []},
]
r = call("upsert_emotions", {"book_id": TID, "chapter_idx": 0, "rows": rows})
check("upsert_emotions 写入", r["saved"] == 2, f"saved={r['saved']}")

# 幂等：再写一次同样的行，不应变成 4 行
call("upsert_emotions", {"book_id": TID, "chapter_idx": 0, "rows": rows})
r = call("get_chapter_emotions", {"book_id": TID, "chapter_idx": 0})
got = {x["line_start"]: x for x in r["rows"]}
check("get_chapter_emotions 往返（幂等，2 行）", len(r["rows"]) == 2,
      f"rows={len(r['rows'])}")
check("weights 反序列化", got[100]["weights"] == {"哀": 3},
      str(got[100]["weights"]))
check("word_spans 未丢失（重启后可回放字级高亮）",
      len(got[100].get("word_spans") or []) == 1,
      str(got[100].get("word_spans")))
check("dutir_top/polarity 保真",
      got[100]["dutir_top"] == "哀" and abs(got[100]["polarity"] + 0.5) < 1e-6,
      f"{got[100]['dutir_top']} {got[100]['polarity']}")

# 增量语义：只补一行，不能冲掉已有的两行
call("upsert_emotions", {"book_id": TID, "chapter_idx": 0, "rows": [
    {"line_start": 102, "line_end": 102, "dutir_top": "怒", "polarity": -1.0,
     "intensity": 0.1, "weights": {"怒": 1}, "word_spans": []}]})
r = call("get_chapter_emotions", {"book_id": TID, "chapter_idx": 0})
check("增量写不冲掉先前批次（3 行）", len(r["rows"]) == 3, f"rows={len(r['rows'])}")
call("save_chapter_emotions", {"book_id": TID, "chapter_idx": 0, "rows": []})

print()
print("=" * 70)
print("五、标注 CRUD（书签迁移用）")
print("=" * 70)
r = call("upsert_annotation", {"book_id": bid, "kind": "bookmark", "chapter_idx": 0,
                               "line_start": 42, "line_end": 42, "text": "测试书签"})
aid = r["id"]
check("upsert_annotation 插入", isinstance(aid, int) and aid > 0, f"id={aid}")

r2 = call("upsert_annotation", {"book_id": bid, "kind": "bookmark", "chapter_idx": 0,
                                "line_start": 42, "line_end": 42, "text": "改过",
                                "note": "备注"})
check("同行同 kind 去重更新（id 不变）", r2["id"] == aid, f"{aid} -> {r2['id']}")

r = call("list_annotations", {"book_id": bid, "kind": "bookmark"})
check("list_annotations 跨会话可见（commit 生效）", len(r["annotations"]) == 1,
      f"{len(r['annotations'])} 条")

r = call("delete_annotation", {"id": aid})
r = call("list_annotations", {"book_id": bid, "kind": "bookmark"})
check("delete_annotation", len(r["annotations"]) == 0, f"剩余 {len(r['annotations'])} 条")

print()
print("=" * 70)
print("六、向量索引（幂等 + 孤儿清理）")
print("=" * 70)
r = call("index_status", {"book_id": bid})
check("index_status（已索引）", r["indexed"] and not r["need_rebuild"],
      f"chunks={r['chunks']} vectors={r['vectors']} need_rebuild={r['need_rebuild']}")

r = call("build_index", {"book_id": bid, "text": text,
                         "chapters": call("chapter_outline", {"path": BOOK})["chapters"]})
check("build_index 幂等跳过（不再每次开书重跑嵌入）", r["skipped"] is True,
      f"chunks={r['chunks']} embedded={r['embedded']} skipped={r['skipped']}")

r = call("maintenance")
check("maintenance 孤儿为 0", r["orphans_removed"] == 0,
      f"before={r['vectors_before']} removed={r['orphans_removed']} after={r['vectors_after']}")

print()
print("=" * 70)
print("七、检索（去重 + 满额召回）")
print("=" * 70)
for q in ["贾宝玉梦游太虚幻境", "王熙凤协理宁国府", "林黛玉初进贾府", "抄检大观园"]:
    r = call("search", {"query": q, "book_id": bid})
    hits = r["hits"]
    keys = [(h["chapter_idx"], h["line_start"]) for h in hits]
    check(f"search「{q}」", len(hits) == 6 and len(set(keys)) == 6,
          f"{len(hits)}/6 去重 {len(set(keys))}  首条 ch{hits[0]['chapter_idx']+1}")

print()
print("=" * 70)
print("八、LLM 问答")
print("=" * 70)
r = call("ask_ai", {"query": "贾宝玉是在第几回神游太虚幻境的？", "book_id": bid})
if "__error__" in r:
    check("ask_ai", False, f"错误：{r['__error__']['message'][:80]}")
else:
    check("ask_ai 返回答案与来源", bool(r["answer"]) and len(r["sources"]) > 0,
          f"答案 {len(r['answer'])} 字，来源 {len(r['sources'])} 条")
    print(f"     答案节选：{r['answer'][:100].replace(chr(10),' ')}")

print()
print("=" * 70)
print("十、M4 全景分析（回灌 120 章 V3.4 报告）")
print("=" * 70)
r = call("import_analysis", {"book_id": bid, "text": text})
if "__error__" in r:
    check("import_analysis", False, f"错误：{r['__error__']['message'][:90]}")
    ov = {}
else:
    check("import_analysis 回灌", r["events"] > 2000 and r["entities"] > 300
          and r["mentions"] > 20000 and r["foreshadows"] > 1000,
          f"事件 {r['events']} 人物 {r['entities']} 出场 {r['mentions']} "
          f"伏笔 {r['foreshadows']} 关系 {r['relations']}")
    check("120 章报告全部解析出事件", r["reports"] == 120
          and not r["reports_without_events"],
          f"报告 {r['reports']} 份，空章 {len(r['reports_without_events'])}")
    prec = r["anchor_precision"]
    check("锚点精度分布已统计", sum(prec.values()) == r["events"],
          f"quote={prec.get('quote')} cooccur={prec.get('cooccur')} "
          f"para={prec.get('para')}")
    ov = call("overview", {"book_id": bid})
    check("overview 覆盖全部 120 章",
          ov["chapters_with_events"] == 120 and ov["events"] == r["events"],
          f"章 {ov['chapters_with_events']} 事件 {ov['events']}")
    check("事件分级自洽（三档合计 = 总数）",
          sum(ov["events_by_level"].values()) == ov["events"],
          str(ov["events_by_level"]))
    check("情感倾向已归一为三类",
          set(ov["events_by_tone"]) <= {"正面", "负面", "中性", "其他"},
          str(ov["events_by_tone"]))

# 事件锚点必须落在本章范围内且单调不回退
ev = call("list_events", {"book_id": bid, "chapter_from": 0, "chapter_to": 0})["events"]
ch0 = call("get_book", {"book_id": bid})["chapters"][0]
mono = all(ev[i]["line_start"] <= ev[i + 1]["line_start"] for i in range(len(ev) - 1))
inrange = all(ch0["start_line"] <= e["line_start"] <= ch0["end_line"] for e in ev)
check("第 1 章事件锚点单调且在本章范围内", bool(ev) and mono and inrange,
      f"{len(ev)} 条，行 {ev[0]['line_start']}~{ev[-1]['line_start']}，"
      f"章范围 {ch0['start_line']}~{ch0['end_line']}")

r = call("list_events", {"book_id": bid, "level": "主线", "limit": 1})
check("按级别筛选事件", len(r["events"]) == 1 and r["events"][0]["level"] == "主线",
      f"uid={r['events'][0]['event_uid']}")

r = call("list_events", {"book_id": bid, "entity": "贾宝玉", "limit": 3})
check("按人物筛选事件", len(r["events"]) > 0,
      f"{[e['event_uid'] for e in r['events']]}")

ents = call("list_entities", {"book_id": bid, "limit": 6})["entities"]
check("人物榜按出场数排序", ents[0]["canonical"] == "贾宝玉" and len(ents) == 6,
      f"Top6 {[e['canonical'] for e in ents]}")
check("别名已归并（贾宝玉含宝玉等别名，且无重复实体）",
      "宝玉" in ents[0]["aliases"]
      and not any(e["canonical"] == "宝玉" for e in ents),
      f"aliases={ents[0]['aliases']}")

card = call("get_entity", {"book_id": bid, "canonical": "贾宝玉"})
check("角色卡：出场曲线 + 关系", len(card["curve"]) > 100 and len(card["relations"]) > 0,
      f"曲线 {len(card['curve'])} 章，关系 {len(card['relations'])} 条，"
      f"出场 {card['entity']['appear_count']}")

mm = call("list_mentions", {"book_id": bid, "chapter_idx": 0})["mentions"]
check("人物出场位置（字级偏移有效）", bool(mm)
      and all(m["char_start"] < m["char_end"] for m in mm),
      f"第 1 章 {len(mm)} 处，首条 {mm[0]['surface']}@{mm[0]['line_start']}"
      f":{mm[0]['char_start']}")

fs_all = call("list_foreshadows", {"book_id": bid})["foreshadows"]
fs_open = call("list_foreshadows", {"book_id": bid, "status": "open"})["foreshadows"]
check("伏笔清单与状态筛选", len(fs_all) > 1000 and 0 < len(fs_open) <= len(fs_all),
      f"全部 {len(fs_all)} 条，未呼应 {len(fs_open)} 条")

rels = call("list_relations", {"book_id": bid, "entity": "贾宝玉"})["relations"]
check("人物关系（报告关系表）", len(rels) > 0,
      f"贾宝玉 {len(rels)} 条，如 {rels[0]['entity_a']}-{rels[0]['relation']}-{rels[0]['entity_b']}")

print()
print("=" * 70)
print("十一、M4.5 全书预处理（把分析前置到开书时）")
print("=" * 70)
import time as _t  # noqa: E402

_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

# 全量调用（幂等：已备跳过、缺则补），把上一轮测试可能留下的缺口补齐
_r0 = call("prepare_book", {"book_id": bid, "text": text})
check("prepare_book 返回覆盖信息",
      _r0["coverage"]["chapters"] == 120,
      f"补缺 {_r0['chapters']} 章，coverage={_r0['coverage']}")

st = call("prepare_status", {"book_id": bid, "chapters_total": 120})
check("prepare_status 反映覆盖率",
      st["prepared_chapters"] == 120 and st["ready"] is True,
      f"已备 {st['prepared_chapters']}/120 章、{st['prepared_lines']} 段")

check("段落级情感已全量入库（全书非空行）", st["prepared_lines"] == 3366,
      f"{st['prepared_lines']} 段 / 全书 {len(_lines)} 行")

# 「前置」的意义就在这里：已备后再次调用必须秒回，而不是重算一遍
_t0 = _t.time()
_r = call("prepare_book", {"book_id": bid, "text": text,
                           "chapter_from": 0, "chapter_to": 9})
_dt = _t.time() - _t0
check("已备章节直接跳过（不重算）",
      _r.get("skipped") is True and _r["chapters"] == 0 and _dt < 2.0,
      f"skipped={_r.get('skipped')} chapters={_r['chapters']} 耗时 {_dt:.3f}s")

_ce = call("list_chapter_emotions", {"book_id": bid})["rows"]
check("章级情感齐备 120 章", len(_ce) == 120,
      f"{len(_ce)} 章，第 1 章 top={_ce[0]['dutir_top']} "
      f"pol={_ce[0]['polarity']} 词={_ce[0]['word_count']}")

# 核心等价性：库里的预处理结果必须等于实时计算（否则「读库」不成立）
_db = call("get_chapter_emotions", {"book_id": bid, "chapter_idx": 0})["rows"]
_ch0 = call("get_book", {"book_id": bid})["chapters"][0]
_seg = "\n".join(_lines[_ch0["start_line"]:_ch0["end_line"] + 1])
_live = call("analyze_sentiment", {"text": _seg})["paragraphs"]
_lmap = {_ch0["start_line"] + p["line_offset"]: p for p in _live}
_same = 0
_diff = 0
for _row in _db:
    _lp = _lmap.get(_row["line_start"])
    if _lp is None:
        continue
    if (_row["dutir_top"] == _lp["dutir_top"]
            and abs(_row["polarity"] - _lp["polarity"]) < 1e-6
            and len(_row["word_spans"]) == len(_lp["word_spans"])):
        _same += 1
    else:
        _diff += 1
check("预处理结果 == 实时计算（第 1 章逐行）", _diff == 0 and _same > 0,
      f"一致 {_same} 行 / 差异 {_diff} 行")

print()
print("=" * 70)
print("十二、M4.6 事件 5W1H 回填（报告 §三 新闻六要素表）")
print("=" * 70)
_r = call("import_analysis", {"book_id": bid, "text": text})
check("import_analysis 返回 5W1H 覆盖",
      "w5h1" in _r and _r["w5h1"] > 0,
      f"events={_r['events']} w5h1={_r.get('w5h1')}")
_ev1 = call("list_events", {"book_id": bid, "chapter_from": 0, "chapter_to": 0})["events"]
_with = [e for e in _ev1 if e.get("w5h1")]
check("第 1 章事件带 5W1H 明细", len(_with) > 0,
      f"{len(_ev1)} 条事件中 {len(_with)} 条带 5W1H")
_w = next((e["w5h1"] for e in _ev1 if e["event_uid"] == "E01-19"), None)
check("E01-19 赠银助考 六要素内容正确",
      bool(_w) and _w["when"] == "中秋夜" and _w["where"] == "甄士隐书房"
      and "赠" in _w["what"] and _w["why"] == "识雨村才学",
      f"w5h1={_w}")
_keys = {"title", "when", "where", "who", "what", "why", "how", "source"}
check("5W1H 字段结构统一（8 键）",
      bool(_with) and all(set(e["w5h1"]) == _keys for e in _with),
      f"样本键集={sorted(_with[0]['w5h1']) if _with else '无样本'}")

proc.stdin.close()
proc.wait(timeout=10)
err = proc.stderr.read()

print()
print("=" * 70)
print("九、stdout 纯净性（协议安全）")
print("=" * 70)
check("stdout 无任何非 JSON 行", len(nonjson) == 0,
      f"污染 {len(nonjson)} 处" if nonjson else "全部为合法 NDJSON 响应")
check("日志全部走 stderr", "[sidecar]" in err,
      f"stderr {len(err.splitlines())} 行")
print(f"     sidecar 退出码：{proc.returncode}")

print()
print("=" * 70)
print(f"结论：{'全部通过 ✅' if not errors else '存在失败 ❌'}")
for e in errors:
    print("   -", e)
print("=" * 70)
sys.exit(1 if errors else 0)
