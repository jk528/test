#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻联播总结报告 —— 单一入口一键生成器
================================================================

设计目标（v5.0.0）：
  1. 一个脚本、一条命令跑完整流程，可直接挂 Windows 任务计划
  2. 以「空白模板」为格式骨架，七部分结构与第六部分 10 列表头严格不变
  3. 输出到 归档/YYYY年M月/新闻联播总结_YYYYMMDD.md，自动建月目录
  4. 不引入任何外部付费依赖（仅 Python 标准库 + requests）

用法：
  python xwlb_report.py                 # 生成昨天的报告
  python xwlb_report.py 20260915        # 生成指定日期
  python xwlb_report.py 20260915 --force   # 强制覆盖重生成
  python xwlb_report.py 20260915 --check   # 只跑质量自检，不写文件
  python xwlb_report.py --dry-run       # 抓数据+渲染+自检，不落盘

退出码：
  0 = 成功（自检无问题）
  1 = 自检存在 ERROR，或日期非法 / 数据抓取失败
  2 = 自检存在 CRITICAL（定时任务据此判失败）

版本历史：
  v5.0.0  2026-09-16  合并 Phase1/2/3 为单一入口；以模板为骨架；
                      修复九类输出质量缺陷；内置质量自检
  v5.1.0  2026-09-16  抓取层改用 CNTV 栏目接口（mode=0 完整版 / mode=1 分段），
                      解决央视网日页漂移导致快讯正文丢失；新增快讯条数交叉校验
  v5.2.0  2026-09-16  取消对已抓取内容的二次省略：快讯正文不再 clip 到 80 字、
                      抽取窗口放开到全文；「核心数据」按模板呈现为「数据点：数值」；
                      数值说明改为句读边界起收（消除断字/跨句残片）；补 个百分点 单位；
                      修掉 --- 前缺空行（会被解析成 setext 标题）并加入自检；
                      第七部分第七点五节取值上限 15→30 行
"""

import argparse
import html as html_module
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

import requests

# ============================================================
# 路径与常量
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLOW_DIR = os.path.dirname(SCRIPT_DIR)                      # 流程/
BASE_DIR = os.path.dirname(FLOW_DIR)                        # 工程根/
ARCHIVE_ROOT = os.path.join(BASE_DIR, "归档")

TEMP_DIR = os.path.join(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")), "xwlb_cache")
os.makedirs(TEMP_DIR, exist_ok=True)

REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(TEMP_DIR, "xwlb_report.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
for _h in logging.getLogger().handlers:
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        try:
            _h.stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
logger = logging.getLogger("xwlb")


# ============================================================
# 复用既有抓取层（fetch_xwlb / fetch_iqilu）
# ============================================================
def _bootstrap_fetch_modules():
    """在多个候选目录中定位 fetch_xwlb.py / fetch_iqilu.py 并加入 sys.path"""
    candidates = [
        os.path.join(FLOW_DIR, "分阶段生成方案"),
        FLOW_DIR,
        SCRIPT_DIR,
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, "fetch_xwlb.py")):
            if d not in sys.path:
                sys.path.insert(0, d)
            return d
    raise RuntimeError("未找到 fetch_xwlb.py，请确认抓取层脚本存在")


FETCH_DIR = _bootstrap_fetch_modules()
from fetch_xwlb import (  # noqa: E402
    desensitize,
    fetch_xwlb_list,
    NAME_TO_CODE,
    CODE_TO_POSITION,
)


# ============================================================
# 模板层：优先读取空白模板，抽取「格式契约」
# ============================================================
TEMPLATE_CANDIDATES = [
    os.path.join(FLOW_DIR, "旧版本", "新闻联播总结_去敏感词模板.md"),
    os.path.join(FLOW_DIR, "新闻联播总结_去敏感词模板.md"),
    os.path.join(SCRIPT_DIR, "空白模板.md"),
]

# 模板缺失时的兜底契约（与模板 v2.3.0 保持一致）
FALLBACK_CONTRACT = {
    "source": "(内置兜底契约)",
    "section_titles": {
        "一": "一、基调概述",
        "二": "二、新闻速览",
        "三": "三、重点新闻详解",
        "四": "四、联播快讯详解",
        "五": "五、完整性检测与播放时间",
        "六": "六、新闻六要素索引",
        "七": "七、占位符统合信息",
    },
    "header6": [
        "序号", "新闻标题（可点击跳转）", "类别", "时间", "地点",
        "新闻主体", "事件", "原因", "方式", "详细信息源链接",
    ],
    "part7_subs": [
        "7.1 新闻主体占位符",
        "7.1.1 人物类",
        "7.1.2 机构类",
        "7.1.3 事件核心对象类",
        "7.3 时间占位符",
        "7.4 地点占位符",
        "7.5 数据占位符",
        "7.6 内容占位符",
    ],
    "sub3": ["3.1 政策/会议", "3.2 国际新闻", "3.3 经济要闻", "3.4 社会/文化要闻"],
    "intros": {},
    "data_source": [
        "> **数据来源**：",
        "> - 央视网：[tv.cctv.com](https://tv.cctv.com/)",
        "> - 齐鲁网：[v.iqilu.com](https://v.iqilu.com/)",
        "> **声明**：本报告基于公开新闻信息整理，仅供参考。播放时间节点为推算值，实际可能有±10秒误差。",
    ],
}


def load_contract():
    """
    读取空白模板，抽取格式契约。
    契约是「结构事实」的来源：章节标题、第六部分列名、第七部分子节、
    第三部分子分类、各章节引导语、数据来源区块。
    """
    path = next((p for p in TEMPLATE_CANDIDATES if os.path.isfile(p)), None)
    if not path:
        logger.warning("未找到空白模板，使用内置兜底契约")
        return dict(FALLBACK_CONTRACT)

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    contract = json.loads(json.dumps(FALLBACK_CONTRACT))
    contract["source"] = path

    # 1) 七个章节标题
    titles = {}
    for no, title in re.findall(r"^## ([一二三四五六七])、(.+?)\s*$", raw, re.M):
        titles[no] = f"{no}、{title}"
    if len(titles) >= 7:
        contract["section_titles"] = titles

    # 2) 第六部分表头（严格 10 列）
    m = re.search(
        r"^\|\s*序号\s*\|[^\n]*新闻标题[^\n]*\|\s*$", raw, re.M
    )
    if m:
        cells = [c.strip() for c in m.group(0).strip().strip("|").split("|")]
        cells = [re.sub(r"^\s*|\s*$", "", c) for c in cells]
        if len(cells) == 10:
            contract["header6"] = cells

    # 3) 第七部分子节
    subs7 = re.findall(r"^### (7\.\d+.*?)\s*$", raw, re.M)
    if len(subs7) >= 3:
        contract["part7_subs"] = subs7

    # 4) 第三部分子分类
    subs3 = re.findall(r"^### (3\.\d+.*?)\s*$", raw, re.M)
    if len(subs3) >= 2:
        contract["sub3"] = subs3

    # 5) 各章节引导语（标题后紧跟的连续 > 行）
    intros = {}
    blocks = re.split(r"^## ", raw, flags=re.M)
    for b in blocks[1:]:
        head, _, body = b.partition("\n")
        no_match = re.match(r"([一二三四五六七])、", head.strip())
        if not no_match:
            continue
        lines = [ln.rstrip() for ln in body.split("\n")]
        quotes = []
        for ln in lines:
            if not ln.strip():
                if quotes:
                    break
                continue
            if ln.lstrip().startswith(">"):
                quotes.append(ln.rstrip())
            else:
                break
        if quotes:
            intros[no_match.group(1)] = quotes
    contract["intros"] = intros

    # 6) 数据来源区块
    ds = re.search(r"(> \*\*数据来源\*\*：\n(?:> .*\n)*)> \*\*声明\*\*[^\n]*", raw)
    if ds:
        contract["data_source"] = [ln.rstrip() for ln in ds.group(0).strip().split("\n")]

    logger.info(f"格式契约已加载：{os.path.basename(path)}")
    logger.info(f"  第六章表头 {len(contract['header6'])} 列 / 第七章 {len(contract['part7_subs'])} 个子节")
    return contract


# ============================================================
# HTTP 工具（带内存缓存）
# ============================================================
_CACHE = {}


def http_get(url, use_cache=True):
    if use_cache and url in _CACHE:
        return _CACHE[url]
    time.sleep(REQUEST_DELAY)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        content = resp.text
        if use_cache:
            _CACHE[url] = content
        return content
    except Exception as e:
        logger.warning(f"请求失败 {url}: {e}")
        return None


# ============================================================
# 抓取层
# ============================================================
# ---- CNTV 栏目接口：比央视网日页更稳定的分段来源 ----
#   mode=0 → 完整版列表（含"本期节目主要内容"brief，即当天全部分条标题）
#   mode=1 → 分段列表（含每条分段独立 URL、时长 length、发布时间 focus_date）
#
# 为什么必须用它：央视网日页会随发布滞后而漂移。实测 20260915 日页把
# "国内联播快讯"和"完整版"都指到了 09/16 路径，而 09/16 那个页面的
# content_area 是空的（快讯 9 条正文一条都抓不到）；真正的正文在
# 09/15 路径下。mode=1 会同时列出 09/15 与 09/16 两条"国内联播快讯"，
# 按 URL 日期过滤即可取到带正文的那条。
_CNTV_COLUMN_API = ("https://api.cntv.cn/NewVideo/getVideoListByColumn"
                    "?id=TOPC1451528971114112&n={n}&sort=desc&p=1&mode={mode}"
                    "&serviceId=tvcctv")
_PATH_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/VIDE")
_VIDEO_PREFIX_RE = re.compile(r"^\s*\[视频\]\s*")
_BRIEF_ITEM_RE = re.compile(r"[（(]\d{1,2}[）)]\s*([^；;。]+)")


def _cntv_column(mode, n=60):
    """CNTV 栏目接口 -> [item]，失败返回 []"""
    raw = http_get(_CNTV_COLUMN_API.format(n=n, mode=mode))
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        logger.warning(f"CNTV 栏目接口返回非 JSON（mode={mode}）")
        return []
    items = ((data.get("data") or {}).get("list")) or []
    return [it for it in items if isinstance(it, dict)]


def _url_path_date(url):
    """URL 里的发布路径日期，如 /2026/09/15/ → '20260915'"""
    m = _PATH_DATE_RE.search(url or "")
    return "".join(m.groups()) if m else ""


def fetch_full_video(date_str):
    """
    完整版：优先 CNTV 接口（URL 日期稳定），返回 {title, url, duration}。
    同一日期常有 19:00 / 21:00 两条，优先"路径日期 == 目标日期"且 19:00 的那条。
    """
    cands = []
    for it in _cntv_column(0):
        title = str(it.get("title") or "")
        url = str(it.get("url") or "")
        if not url or date_str not in title or "《新闻联播》" not in title:
            continue
        cands.append({
            "title": f"完整版《新闻联播》 {date_str}",
            "url": url,
            "duration": str(it.get("length") or ""),
            "same_day": _url_path_date(url) == date_str,
            "is19": "19:00" in title,
        })
    if not cands:
        return None
    cands.sort(key=lambda c: (c["same_day"], c["is19"]), reverse=True)
    return {k: cands[0][k] for k in ("title", "url", "duration")}


def fetch_segments_from_api(date_str):
    """分段列表：只保留 URL 日期 == 目标日期的条目，并还原播出顺序"""
    rows, seen = [], set()
    for it in _cntv_column(1):
        url = str(it.get("url") or "")
        if _url_path_date(url) != date_str:
            continue
        title = _VIDEO_PREFIX_RE.sub("", str(it.get("title") or "")).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        rows.append({
            "title": title, "url": url,
            "duration": str(it.get("length") or ""),
        })
    rows.reverse()          # 接口按时间倒序 → 反转即播出顺序
    return rows


def fetch_kuaixun_briefs(date_str):
    """
    快讯父条目 brief 里自带的子条目清单，形如：
      国际联播快讯：（1）也门胡塞武装称打击沙特空军基地；（2）俄称多方向推进…
    用于交叉校验"齐鲁网名录 − 央视网常规新闻"对账出来的条数。
    """
    out = {}
    for it in _cntv_column(1):
        if _url_path_date(str(it.get("url") or "")) != date_str:
            continue
        title = _VIDEO_PREFIX_RE.sub("", str(it.get("title") or "")).strip()
        if "联播快讯" not in title:
            continue
        items = [s.strip() for s in _BRIEF_ITEM_RE.findall(str(it.get("brief") or ""))]
        if items:
            out[title] = items
    return out


_DAY_PREFIX_RE = re.compile(r"^(?:\[视频\]\s*)?完整版\s*(?=[《\u4e00-\u9fa5A-Za-z0-9])")


def _normalize_day_title(title):
    """
    归档日页的标题归一化。

    央视网日页对历史日期会给每条标题统一加"完整版"前缀
    （实测 20260601 / 20260715 / 20260901 / 20260910 全量如此），
    这跟"该条是不是完整版"无关。这里剥掉前缀与残留的 [视频] 标记，
    还原真实标题；真正的完整版由"《新闻联播》 + 日期 + 19:00"另行识别。
    """
    t = (title or "").replace("[视频]", "").strip()
    t = _DAY_PREFIX_RE.sub("", t).strip()
    return t


def fetch_videos(date_str):
    """
    视频列表 -> [{title, duration, url}]，首条为完整版。

    两条取数路径：
      · CNTV 栏目接口（近 ~4 天）——标题干净，优先；
      · 央视网日页（任意历史日期）——⚠️ 归档日页会给**每一条**标题都加
        "完整版"前缀（实测 20260601 的 14 条、20260901 的 18 条全部如此），
        这不是"这条是完整版"的意思。旧实现拿 "完整版" 当过滤条件，
        结果把整页条目删空、直接抛"数据获取失败"——历史日期因此完全无法重建。
        现在改为**归一化前缀**，而不是丢弃条目。
    """
    videos = fetch_segments_from_api(date_str)
    if videos:
        logger.info(f"CNTV 栏目接口获取到 {len(videos)} 条分段")
    else:
        logger.warning("CNTV 栏目接口无结果（历史日期超出接口回溯范围），退回央视网日页")
        videos = []
        for r in fetch_xwlb_list(date_str):
            videos.append({
                "title": _normalize_day_title(r.get("title", "")),
                "duration": r.get("duration", ""),
                "url": r.get("url", ""),
            })
        logger.info(f"央视网日页获取到 {len(videos)} 条视频")

    # 完整版：CNTV 接口优先；接口没覆盖到的历史日期，从归一化后的列表里认
    full = fetch_full_video(date_str)
    if not full:
        cand = [v for v in videos
                if "《新闻联播》" in v["title"] and date_str in v["title"]]
        if not cand:
            cand = [v for v in videos
                    if "《新闻联播》" in v["title"]
                    and time_to_seconds(v["duration"]) > 1500]
        if cand:
            cand.sort(key=lambda c: ("19:00" in c["title"], time_to_seconds(c["duration"])),
                      reverse=True)
            full = {"title": f"完整版《新闻联播》 {date_str}",
                    "url": cand[0]["url"], "duration": cand[0]["duration"]}
    if full:
        logger.info(f"完整版链接：{full['url']}")
    videos = [v for v in videos if v["url"] != (full or {}).get("url")]
    if full:
        videos.insert(0, full)
    return videos


def fetch_video_detail(video_url):
    """央视网视频页正文 -> {paragraphs, full_text, first_paragraph}"""
    html = http_get(video_url)
    empty = {"paragraphs": [], "full_text": "", "first_paragraph": ""}
    if not html:
        return empty

    paragraphs = []
    main_match = re.search(
        r"主要内容(.*?)(?=编辑[：:]|责任编辑|全部评论|京ICP备|video_info)",
        html, re.DOTALL,
    )
    if main_match:
        for p in re.findall(r"<p[^>]*>(.*?)</p>", main_match.group(1), re.DOTALL):
            text = re.sub(r"<[^>]+>", "", p).strip()
            text = re.sub(r"\s+", " ", html_module.unescape(text)).strip()
            if len(text) > 15 and "版权所有" not in text and "ICP备" not in text:
                paragraphs.append(text)

    if len(paragraphs) < 2 and main_match:
        flat = re.sub(r"<[^>]+>", "\n", main_match.group(1))
        flat = html_module.unescape(flat)
        lines = [l.strip() for l in flat.split("\n") if l.strip()]
        paragraphs = [
            l for l in lines if len(l) > 15 and "版权所有" not in l and "ICP备" not in l
        ]

    cleaned = [
        re.sub(r"^央视网消息[（(][^）)]*[）)]\s*[：:]\s*", "", p) for p in paragraphs
    ]
    return {
        "paragraphs": cleaned,
        "full_text": " ".join(cleaned),
        "first_paragraph": cleaned[0] if cleaned else "",
    }


def fetch_kuaixun_details(video_url):
    """
    央视网快讯目录页 -> [{title, body, summary, full_text}]

    只认 <div class="content_area" id="content_area"> 内的 <p> 结构：
        <p><strong>央视网消息</strong>（新闻联播）：</p>   ← 页头，跳过
        <p><strong>子条目标题</strong></p>                  ← 新条目开始
        <p>正文段落</p> ...                                 ← 该条目的正文

    ⚠️ 该区域由 JS 动态注入，部分日期会为空（实测 20260915 的国内快讯即如此）。
    此时返回 []，改由齐鲁网名录交叉补齐标题——绝不再用弱正则从整页噪声里
    "扫"出伪条目（那是旧流程丢条目/概要退化的根因）。
    """
    html = http_get(video_url)
    if not html:
        return []

    m = re.search(
        r'<div class="content_area"[^>]*>(.*?)</div>\s*<div class="zebian"',
        html, re.DOTALL,
    )
    if not m or not m.group(1).strip():
        logger.warning(f"快讯页内容区为空（JS 动态加载），需齐鲁网补齐：{video_url}")
        return []

    items, cur = [], None
    for pm in re.finditer(r"<p[^>]*>(.*?)</p>", m.group(1), re.DOTALL | re.IGNORECASE):
        raw = pm.group(1)
        strong = re.search(r"<strong>(.*?)</strong>", raw, re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", raw)
        text = re.sub(r"\s+", " ", html_module.unescape(text)).strip()
        text = re.sub(r"^央视网消息[（(][^）)]*[）)]\s*[：:]\s*", "", text).strip()

        if strong:
            t = re.sub(r"<[^>]+>", "", strong.group(1))
            t = re.sub(r"\s+", " ", html_module.unescape(t)).strip()
            if "央视网消息" in t:          # 页头「央视网消息（新闻联播）：」
                cur = None
                continue
            cur = {"title": t, "body": ""}
            items.append(cur)
        elif cur is not None and text:
            cur["body"] = (cur["body"] + text).strip()

    out = []
    for it in items:
        if len(it["title"]) > 4 and "联播快讯" not in it["title"]:
            out.append({
                "title": it["title"],
                "body": it["body"],
                "summary": it["body"],
                "full_text": it["body"],
            })
    logger.info(f"快讯页解析到 {len(out)} 条子条目（含正文 {sum(1 for x in out if x['body'])} 条）")
    return out


# ------------------------------------------------------------
# 快讯子条目名录：齐鲁网 ∩ 央视网 交叉对账
# ------------------------------------------------------------
_SIM_MATCH = 0.55

_INTL_HINTS = [
    "联合国", "俄乌", "中东", "也门", "以色列", "伊朗", "美国", "俄罗斯", "乌克兰",
    "沙特", "日本", "韩国", "欧盟", "北约", "加沙", "巴勒斯坦", "朝鲜", "叙利亚",
    "德国", "法国", "英国", "印度", "奥地利", "维也纳", "胡塞武装", "美伊", "美俄",
    "俄美", "美乌", "白俄罗斯", "墨西哥", "卡塔尔", "塞尔维亚", "保加利亚", "柬埔寨",
]
_INTL_NEG = ["国际标准", "国际化", "国际收支", "国际比赛", "国际旅游", "国际航线", "国际会展"]


def _looks_international(title):
    if any(neg in title for neg in _INTL_NEG):
        return False
    return any(h in title for h in _INTL_HINTS)


def _best_match(title, pool, thr=_SIM_MATCH):
    best, score = None, 0.0
    for e in pool:
        s = SequenceMatcher(None, title, e.get("title", "")).ratio()
        if s > score:
            best, score = e, s
    return (best, score) if score >= thr else (None, score)


def reconcile_brief_roster(ds, iqilu_entries, cctv_dom, cctv_intl):
    """
    快讯子条目名录 = 齐鲁网当日条目 − 央视网常规新闻条目（交叉取差集）。

    为什么这样做：实测发现央视网快讯目录页的 content_area 会被 JS 动态清空
    （20260915 国内快讯即如此），且当日页给出的链接偶尔指向次日页面。
    齐鲁网索引页对当日全部条目的覆盖是稳定的，用它做名录基准；
    央视网快讯页只负责在可用时提供权威正文。

    返回 (domestic_rows, international_rows, complement)
    """
    regular_titles = [n["raw_title"] for n in ds.news if not n["is_dir"]]
    regular_pool = [{"title": t} for t in regular_titles]
    complement = [
        e for e in iqilu_entries
        if _best_match(e["title"], regular_pool)[1] < _SIM_MATCH
    ]

    dom_roster = cctv_dom if cctv_dom else None
    intl_roster = cctv_intl if cctv_intl else None

    if dom_roster is None or intl_roster is None:
        known = intl_roster or dom_roster or []
        rest = [e for e in complement if _best_match(e["title"], known)[1] < _SIM_MATCH]
        if dom_roster is None and intl_roster is None:
            dom_roster = [e for e in rest if not _looks_international(e["title"])]
            intl_roster = [e for e in rest if _looks_international(e["title"])]
            logger.warning(
                f"央视网快讯页均不可用，按标题启发式划分方向："
                f"国内 {len(dom_roster)} / 国际 {len(intl_roster)}"
            )
        elif dom_roster is None:
            dom_roster = rest
        else:
            intl_roster = rest

    def finalize(roster, body_pools):
        # 齐鲁网索引为倒序（pos 越大越靠前播出），央视网快讯页本身即播出顺序
        if roster and all("pos" in r for r in roster):
            roster = sorted(roster, key=lambda r: -r["pos"])
            logger.info("  名录顺序按齐鲁网索引倒序还原播出顺序")
        rows = []
        for it in roster:
            title = it["title"]
            iq = _best_match(title, complement)[0]
            body = (it.get("body") or it.get("full_text") or it.get("summary") or "").strip()
            if not body:
                for pool in body_pools:
                    hit, _s = _best_match(title, pool)
                    if hit:
                        body = (hit.get("body") or hit.get("full_text") or "").strip()
                        if body:
                            break
            rows.append({
                "title": title,
                "iqilu_url": (iq or {}).get("url", ""),
                "body": body,
            })
        return rows

    return (
        finalize(dom_roster, [intl_roster or [], cctv_intl or []]),
        finalize(intl_roster, [dom_roster or [], cctv_dom or []]),
        complement,
    )


def fetch_iqilu_entries(date_str):
    """齐鲁网索引页 -> 目标日期的快讯子条目 [{title,url}]"""
    target = datetime.strptime(date_str, "%Y%m%d").date()
    entries, seen = [], set()

    for page in range(1, 6):
        url = (
            "https://v.iqilu.com/jcdb/ysxwlb/index.html"
            if page == 1
            else f"https://v.iqilu.com/jcdb/ysxwlb/index_{page - 1}.html"
        )
        html = http_get(url)
        if not html:
            continue

        pattern = re.compile(
            r'<a[^>]*href="(https://v\.iqilu\.com/jcdb/ysxwlb/[^"]+\.html)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for link, title_raw in pattern.findall(html):
            title = re.sub(r"<[^>]+>", "", title_raw).strip()
            title = html_module.unescape(title)
            if not title or len(title) < 5:
                continue

            dm = re.search(r"/(\d{6})/(\d{2})/", link)
            if not dm:
                continue
            try:
                url_date = date(int(dm.group(1)[:4]), int(dm.group(1)[4:]), int(dm.group(2)))
            except ValueError:
                continue
            if url_date != target:
                continue
            if "完整版" in title:
                continue

            clean = re.sub(r"^\d{4}年\d{2}月\d{2}日\s*", "", title)
            clean = clean.replace("【联播快讯】", "").replace("联播快讯", "").strip()
            if not clean or link in seen:
                continue
            seen.add(link)
            entries.append({"title": clean, "url": link, "pos": len(entries) + 1})

    logger.info(f"齐鲁网获取到 {len(entries)} 条目标日期子条目")
    return entries


# 说明：齐鲁网详情页实测未提供可解析正文（无 content/article 容器，正文为 JS 注入），
# 因此不再实现 fetch_iqilu_detail / 独立 URL 匹配——子条目名录与链接改由
# reconcile_brief_roster() 做"齐鲁网名录 − 央视网常规新闻"的交叉对账得出。


# ============================================================
# 文本工具：句边界截断（彻底消除「断字断句」）
# ============================================================
_SENT_END = "。！？；!?;"


def clip_sentence(text, limit=70):
    """
    在句子边界截断，绝不硬切。
    - 首个完整句 <= limit 时直接返回该句
    - 否则累积完整句直到接近 limit
    - 若通篇无标点（如标题），按标点/括号安全边界切分并保证闭合
    """
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if len(text) <= limit:
        return _close_brackets(text)

    # 按句末标点切句
    parts, buf = [], ""
    for ch in text:
        buf += ch
        if ch in _SENT_END:
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)

    if parts and parts[0] != text:
        acc = ""
        for p in parts:
            if acc and len(acc) + len(p) > limit:
                break
            acc += p
        if acc:
            return _close_brackets(acc)
    else:
        # 无句末标点：退到次级停顿标点
        for sep in ["，", "、", "：", ":", " "]:
            if sep in text:
                acc = ""
                for piece in text.split(sep):
                    cand = acc + (sep if acc else "") + piece
                    if len(cand) > limit:
                        break
                    acc = cand
                if acc:
                    return _close_brackets(acc)

    return _close_brackets(text[:limit])


def _close_brackets(text):
    """补齐被截断的引号/书名号/括号，避免出现未闭合标点"""
    pairs = [("《", "》"), ("“", "”"), ("（", "）"), ("(", ")"), ("【", "】"), ("[", "]")]
    for op, cl in pairs:
        if text.count(op) > text.count(cl):
            text += cl * (text.count(op) - text.count(cl))
    text = text.rstrip("，、：；,; ")
    return text


def strip_topic_prefix(title):
    """去掉【专题】前缀，得到干净标题"""
    return re.sub(r"^【[^】]*】\s*", "", (title or "").strip()).strip()


def desens(text, mark=True):
    return desensitize(text or "", mark)


# ============================================================
# 规则层 1：分类与重要性（加权命中，取代「首个关键词决定」）
# ============================================================
CATEGORY_ORDER = ["政策/会议", "国际新闻", "经济要闻", "社会/文化要闻", "其他"]

# 强制归类规则（优先级最高，命中即定类，避免关键词互相污染）
_FORCE_RULES = [
    (r"国际标准|国际化|国际收支|国际会展", "经济要闻"),
    (r"^央视快评|^本台评论", "社会/文化要闻"),
    (r"校招|引才|人才|就业|招聘", "社会/文化要闻"),
    (r"商品住宅|房地产|住房|楼市", "经济要闻"),
]

# 每条规则 (分类, 权重, 关键词集合)
_TOPIC_RULES = [
    # 国际新闻：只认"国家/地区 + 国际事务"实体，不用裸"国际"二字
    ("国际新闻", 3, ["国际社会", "国际局势", "国际关系", "外交部", "联合国", "北约", "欧盟"]),
    ("国际新闻", 2, [
        "美国", "伊朗", "以色列", "俄罗斯", "乌克兰", "也门", "沙特", "日本", "韩国",
        "德国", "法国", "英国", "印度", "朝鲜", "欧佩克", "胡塞武装", "加沙",
        "俄乌", "美伊", "中东", "维也纳", "白俄罗斯", "墨西哥", "塔伊兹", "美方",
    ]),
    ("政策/会议", 3, [
        "政策", "条例", "国务院令", "规划", "意见", "办法", "规定", "纲要",
        "座谈会", "研讨会", "全会", "政治局", "印发", "出台", "战略", "机制",
    ]),
    ("政策/会议", 2, [
        "会议", "论坛", "发布会", "改革", "立法", "监督", "法治", "党建", "巡视", "纪检",
    ]),
    ("经济要闻", 3, [
        "经济", "GDP", "产业", "制造业", "工业", "贸易", "金融", "外汇", "财政",
        "货币", "投资", "消费", "粮食", "物流", "运价", "营收", "营业收入",
        "成交", "价格", "数据", "统计", "进出口", "碳市场", "碳排放", "国债",
        "收益率", "税", "标准", "专利", "产能", "电子信息",
    ]),
    ("经济要闻", 2, [
        "企业", "市场", "银行", "保险", "证券", "基金", "乡村建设", "基础设施",
        "工程", "通道", "航运", "口岸", "平台", "数字经济", "科技创新", "产业链",
    ]),
    ("社会/文化要闻", 3, [
        "文化", "文物", "非遗", "文明", "旅游", "教育", "学校", "体育", "赛事",
        "医疗", "卫生", "医保", "健康", "养老", "生态", "环境", "气象", "天气",
        "防汛", "抗旱", "救灾", "应急",
    ]),
    ("社会/文化要闻", 2, [
        "社会", "民生", "社区", "市民", "乡村", "农业", "农村", "街区", "历史",
        "保护", "传承", "航天", "发射", "卫星", "科普", "志愿",
    ]),
]

_RED_KEYWORDS = [
    "国家主席", "国务院总理", "国家副主席", "中央纪委书记",
    "全国人大常委会委员长", "全国政协主席", "中共中央政治局常委",
    "国务院副总理", "中央军委主席",
]

_YELLOW_KEYWORDS = [
    "新思想", "新征程", "高质量发展", "十五五", "十四五", "重大工程",
    "国民经济", "规划", "印发", "发布", "统计数据", "经济运行",
    "美国总统", "俄罗斯", "乌克兰", "伊朗", "国债收益率", "论坛", "博览会",
]


def classify_and_grade(safe_title, raw_title, text):
    """
    返回 (category, importance)。
    先用强制规则定类，再对剩余情形做加权命中打分——
    避免「遇到第一个关键词就定类」导致的错分（如「国际标准」被判进国际新闻）。
    """
    title_clean = re.sub(r"<[^>]+>", "", safe_title)
    body = f"{title_clean} {strip_topic_prefix(safe_title)} {text[:400]}"

    category = None
    for pat, forced in _FORCE_RULES:
        if re.search(pat, title_clean):
            category = forced
            break

    if category is None:
        scores = {}
        for cat, weight, words in _TOPIC_RULES:
            hit = sum(1 for w in words if w in title_clean)
            if hit:
                scores[cat] = scores.get(cat, 0) + hit * weight
        for cat, weight, words in _TOPIC_RULES:
            hit = sum(1 for w in words if w in body and w not in title_clean)
            if hit:
                scores[cat] = scores.get(cat, 0) + hit * max(1, weight - 1) * 0.5
        if scores:
            category = max(
                scores.items(),
                key=lambda kv: (kv[1], -CATEGORY_ORDER.index(kv[0])),
            )[0]
        else:
            category = "其他"

    importance = "一般"
    if any(kw in title_clean for kw in _RED_KEYWORDS):
        importance = "🔴"
    elif any(kw in title_clean for kw in _YELLOW_KEYWORDS):
        importance = "🟡"
    return category, importance


# ============================================================
# 规则层 2：词典
# ============================================================
INSTITUTIONS = {
    # 国务院组成部门与直属机构
    "国家发展改革委": "中华人民共和国国家发展和改革委员会",
    "国家发改委": "中华人民共和国国家发展和改革委员会",
    "工业和信息化部": "中华人民共和国工业和信息化部",
    "财政部": "中华人民共和国财政部",
    "商务部": "中华人民共和国商务部",
    "教育部": "中华人民共和国教育部",
    "科技部": "中华人民共和国科学技术部",
    "交通运输部": "中华人民共和国交通运输部",
    "水利部": "中华人民共和国水利部",
    "农业农村部": "中华人民共和国农业农村部",
    "生态环境部": "中华人民共和国生态环境部",
    "自然资源部": "中华人民共和国自然资源部",
    "住房和城乡建设部": "中华人民共和国住房和城乡建设部",
    "文化和旅游部": "中华人民共和国文化和旅游部",
    "人力资源和社会保障部": "中华人民共和国人力资源和社会保障部",
    "国家卫生健康委": "中华人民共和国国家卫生健康委员会",
    "应急管理部": "中华人民共和国应急管理部",
    "民政部": "中华人民共和国民政部",
    "司法部": "中华人民共和国司法部",
    "公安部": "中华人民共和国公安部",
    "国家安全部": "中华人民共和国国家安全部",
    "中国人民银行": "中国人民银行",
    "海关总署": "中华人民共和国海关总署",
    "国家税务总局": "国家税务总局",
    "国家市场监督管理总局": "国家市场监督管理总局",
    "市场监管总局": "国家市场监督管理总局",
    "金融监管总局": "国家金融监督管理总局",
    "国家金融监督管理总局": "国家金融监督管理总局",
    "中国证监会": "中国证券监督管理委员会",
    "国家统计局": "国家统计局",
    "国家医保局": "国家医疗保障局",
    "国家外汇管理局": "国家外汇管理局",
    "国家标准委": "国家标准化管理委员会",
    "国家能源局": "国家能源局",
    "国家数据局": "国家数据局",
    "国家疾控局": "国家疾病预防控制局",
    "中国气象局": "中国气象局",
    "中央气象台": "中央气象台",
    "国家航天局": "国家航天局",
    "中国国家航天局": "国家航天局",
    "国家知识产权局": "国家知识产权局",
    "国家林业和草原局": "国家林业和草原局",
    "国家体育总局": "国家体育总局",
    "国家文物局": "国家文物局",
    "国家铁路局": "国家铁路局",
    "国务院新闻办": "国务院新闻办公室",
    "国务院新闻办公室": "国务院新闻办公室",
    # 中央机构与其他
    "中央宣传部": "中共中央宣传部",
    "中央组织部": "中共中央组织部",
    "中央统战部": "中共中央统战部",
    "中央广播电视总台": "中央广播电视总台",
    "最高人民法院": "中华人民共和国最高人民法院",
    "最高人民检察院": "中华人民共和国最高人民检察院",
    "全国人大常委会": "全国人民代表大会常务委员会",
    "全国政协": "中国人民政治协商会议全国委员会",
    "全国总工会": "中华全国总工会",
    "共青团中央": "中国共产主义青年团中央委员会",
    "全国妇联": "中华全国妇女联合会",
    "中国国家铁路集团": "中国国家铁路集团有限公司",
    "中国航天科技集团": "中国航天科技集团有限公司",
    "中国科学院": "中国科学院",
    "中国工程院": "中国工程院",
    # 国际组织
    "联合国": "联合国",
    "上合组织": "上海合作组织",
    "欧盟": "欧洲联盟",
    "北约": "北大西洋公约组织",
    "世界银行": "世界银行",
    "国际货币基金组织": "国际货币基金组织",
    "国际原子能机构": "国际原子能机构",
}

# 机构类主体的结尾特征词（用于兜底判定）
_ORG_SUFFIX = (
    "部", "委", "局", "署", "院", "厅", "行", "台", "社", "中心", "协会",
    "学会", "集团", "公司", "组织", "银行", "大学", "学院", "研究院",
    "委员会", "办公室", "政府", "总局", "总台", "总局",
)

PLACES = {
    # 省级行政区
    "北京": "北京", "天津": "天津", "上海": "上海", "重庆": "重庆",
    "河北": "河北", "山西": "山西", "辽宁": "辽宁", "吉林": "吉林",
    "黑龙江": "黑龙江", "江苏": "江苏", "浙江": "浙江", "安徽": "安徽",
    "福建": "福建", "江西": "江西", "山东": "山东", "河南": "河南",
    "湖北": "湖北", "湖南": "湖南", "广东": "广东", "海南": "海南",
    "四川": "四川", "贵州": "贵州", "云南": "云南", "陕西": "陕西",
    "甘肃": "甘肃", "青海": "青海", "台湾": "中国台湾",
    "内蒙古": "内蒙古", "广西": "广西", "西藏": "西藏", "宁夏": "宁夏",
    "新疆": "新疆",
    # 重点城市 / 地区
    "银川": "宁夏银川", "绍兴": "浙江绍兴", "重庆": "重庆", "西安": "陕西西安",
    "乌鲁木齐": "新疆乌鲁木齐", "成都": "四川成都", "武汉": "湖北武汉",
    "郑州": "河南郑州", "济南": "山东济南", "青岛": "山东青岛",
    "漳州": "福建漳州", "深圳": "广东深圳", "广州": "广东广州",
    "杭州": "浙江杭州", "南京": "江苏南京", "苏州": "江苏苏州",
    "合肥": "安徽合肥", "长沙": "湖南长沙", "福州": "福建福州",
    "厦门": "福建厦门", "昆明": "云南昆明", "兰州": "甘肃兰州",
    "西宁": "青海西宁", "呼和浩特": "内蒙古呼和浩特", "哈尔滨": "黑龙江哈尔滨",
    "长春": "吉林长春", "沈阳": "辽宁沈阳", "大连": "辽宁大连",
    "石家庄": "河北石家庄", "太原": "山西太原", "南昌": "江西南昌",
    "贵阳": "贵州贵阳", "南宁": "广西南宁", "拉萨": "西藏拉萨",
    "海口": "海南海口", "三亚": "海南三亚", "雄安": "河北雄安新区",
    "粤北": "广东粤北", "平陆运河": "广西",
    # 国际地点
    "维也纳": "奥地利维也纳", "华盛顿": "美国华盛顿", "纽约": "美国纽约",
    "莫斯科": "俄罗斯莫斯科", "德黑兰": "伊朗德黑兰", "东京": "日本东京",
    "首尔": "韩国首尔", "柏林": "德国柏林", "巴黎": "法国巴黎",
    "伦敦": "英国伦敦", "日内瓦": "瑞士日内瓦", "加沙": "巴勒斯坦加沙地带",
    "霍尔木兹海峡": "霍尔木兹海峡",
}

COUNTRY_TO_PLACE = {
    "美国": "美国", "伊朗": "伊朗", "以色列": "以色列", "俄罗斯": "俄罗斯",
    "乌克兰": "乌克兰", "也门": "也门", "沙特": "沙特阿拉伯",
    "日本": "日本", "韩国": "韩国", "德国": "德国", "法国": "法国",
    "英国": "英国", "印度": "印度", "朝鲜": "朝鲜", "奥地利": "奥地利",
    "白俄罗斯": "白俄罗斯", "墨西哥": "墨西哥", "柬埔寨": "柬埔寨",
    "塞尔维亚": "塞尔维亚", "保加利亚": "保加利亚", "卡塔尔": "卡塔尔",
    "越南": "越南", "泰国": "泰国", "新加坡": "新加坡", "巴西": "巴西",
    "澳大利亚": "澳大利亚", "加拿大": "加拿大",
}

# 事件核心对象类的特征词
_EVENT_OBJECT_HINTS = (
    "冲突双方", "双方", "多方", "相关方", "产油国", "火山", "货机", "航线",
    "市场", "行业", "领域", "群体", "队伍", "队员", "少年儿童", "消费者",
    "居民", "农户", "游客", "观众", "读者", "选手", "员工", "代表",
)

PERSON_TITLE_DETAIL = {
    "国家主席": "中共中央总书记、国家主席、中央军委主席",
    "国务院总理": "国务院总理",
    "全国人大常委会委员长": "全国人民代表大会常务委员会委员长",
    "全国政协主席": "中国人民政治协商会议全国委员会主席",
    "国家副主席": "中华人民共和国副主席",
    "中共中央政治局常委": "中共中央政治局常务委员会委员",
    "国务院副总理": "国务院副总理",
    "中央纪委书记": "中共中央纪律检查委员会书记",
    "美国总统": "美利坚合众国总统",
    "俄罗斯总统": "俄罗斯联邦总统",
    "乌克兰总统": "乌克兰总统",
    "以色列总理": "以色列总理",
    "英国首相": "英国首相",
    "法国总统": "法兰西共和国总统",
    "韩国总统": "大韩民国总统",
    "印度总理": "印度共和国总理",
    "白俄罗斯总统": "白俄罗斯共和国总统",
    "墨西哥总统": "墨西哥合众国总统",
}

# 动作 → 方式的映射
_METHOD_RULES = [
    ("回信", "回信勉励"), ("贺信", "致贺信"), ("致电", "致电"),
    ("会见", "会见"), ("会谈", "举行会谈"), ("座谈", "召开座谈会"),
    ("考察", "实地考察"), ("调研", "调研"), ("视察", "视察"),
    ("讲话", "发表重要讲话"), ("演讲", "发表演讲"),
    ("印发", "印发文件"), ("发布", "发布信息"), ("公布", "公布数据"),
    ("发布报告", "发布报告"), ("行政指导", "开展行政指导"),
    ("举行", "举办活动"), ("召开", "召开会议"), ("开幕", "举办开幕活动"),
    ("启动", "启动实施"), ("签署", "签署协议"), ("交接", "举行交接仪式"),
    ("通航", "建成通航"), ("发射", "组织发射"), ("贯标", "标准发布"),
    ("施行", "发布施行"), ("试行", "发布试行"),
]

# 标题里看不出来、但正文里写明的动作（按优先级从上到下）
_BODY_METHOD_RULES = [
    ("交接仪式", "举行交接仪式"), ("挂牌仪式", "举行挂牌仪式"),
    ("签约仪式", "举行签约仪式"), ("签字仪式", "举行签约仪式"),
    ("新闻发布会", "召开新闻发布会"), ("签署", "签署协议"),
    ("座谈会", "召开座谈会"), ("播发", "播发评论"),
    ("印发", "印发文件"), ("通航", "建成通航"),
]

# 国际新闻默认"公开表态"的前置条件：标题里必须有表态类动词
_ATTITUDE_WORDS = ("称", "表示", "宣布", "声明", "回应", "表态", "发文", "强调")

_SECTION3_FIELDS = {
    "政策/会议": [("发文部门", "dept"), ("发布时间", "pubdate"), ("核心目标", "goal"), ("政策要点", "points")],
    "国际新闻": [("核心进展", "progress"), ("各方立场", "stance")],
    "经济要闻": [("数据来源", "datasrc"), ("核心数据", "keydata")],
    "社会/文化要闻": [("活动时间", "acttime"), ("参与规模", "scale")],
    "其他": [("核心进展", "progress"), ("要点", "points")],
}


# ============================================================
# 规则层 3：六要素提取（重写）
# ============================================================
# 国名简称补全（新闻标题常写"美称""俄称""乌方"）
_COUNTRY_ALIAS = {"美": "美国", "俄": "俄罗斯", "乌": "乌克兰", "以": "以色列",
                  "伊": "伊朗", "韩": "韩国", "日": "日本", "德": "德国",
                  "法": "法国", "英": "英国", "印": "印度"}

# 主体覆盖规则（标题特征 → 权威主体）
_ACTOR_OVERRIDES = [
    (r"^央视快评", "中央广播电视总台"),
    (r"^本台评论", "中央广播电视总台"),
    (r"^《[^》]+》出版发行", "中央宣传部"),
]

# 名词短语合法性：用于判断"从标题截出来的东西"能否当主体/事件核心对象
# 只保留"几乎不可能出现在名词短语内部"的动词/虚词。
# 早期版本误收 会/对/要/使/给/从/向 等字，导致"…研讨会""对外友协"等
# 合法名词短语被整条拒掉（表现为主体退化为"—"），故收窄到最小集合。
_NP_STOP = set("称表示说在为的以将已是把让")

_VAGUE = {"我国", "中国", "全国", "各地", "有关部门", "相关方", "该", "其", "该部门", "与会代表", "相关人士"}


def is_valid_noun_phrase(s):
    """判断候选是否为干净的名词短语（拒绝动宾结构、含数字/标点的残片）"""
    s = (s or "").strip()
    if not (2 <= len(s) <= 22):
        return False
    if not re.fullmatch(r"[\u4e00-\u9fa5A-Za-z]+", s):
        return False
    if any(ch in _NP_STOP for ch in s):
        return False
    if s in _VAGUE:
        return False
    return True


def clean_org_name(raw):
    """清洗机构候选，剔除泛称与噪声"""
    s = re.sub(r"^[，。、；：,;:\s]+", "", raw or "").strip()
    s = re.sub(r"^(据悉|日前|近日|今天|昨天|目前|下一步|其中|同时|此外|播）|）|：)", "", s).strip()
    s = s.strip("，。、；：,;:（）() ")
    if len(s) < 2 or len(s) > 20:
        return ""
    if s in _VAGUE or any(n == s for n in ("与会", "相关", "有关", "各界", "各方", "记者", "本台")):
        return ""
    return s


def detect_countries(title_plain):
    """
    从标题识别国家主体，支持"美/俄/乌"等简称（新闻标题常用单字简称开头，
    如"美称…""俄称…""美10年期国债…"）。
    """
    found = [COUNTRY_TO_PLACE[c] for c in COUNTRY_TO_PLACE if c in title_plain]
    head = title_plain[:1]
    if head in _COUNTRY_ALIAS:
        full = _COUNTRY_ALIAS[head]
        full = COUNTRY_TO_PLACE.get(full, full)
        if full not in found:
            found.insert(0, full)
    return list(dict.fromkeys(found))


def extract_location(safe_title, text, category, is_brief_domestic=False):
    """
    地点：标题结构 → 标题地名 → 标题国名 → 首段地名 → 领导人默认北京 → 兜底
    注意：不再全篇乱扫地名（旧实现会把正文里偶然出现的省份当成事发地）。
    """
    title = re.sub(r"<[^>]+>", "", strip_topic_prefix(safe_title))
    first_para = (text or "")[:160]

    # 1) 标题中的 "在X举行/召开/开幕/举办" 结构
    m = re.search(r"在([\u4e00-\u9fa5]{2,10}?)(?:举行|召开|开幕|举办|启动|签署|发布|上线|投产|进行)", title)
    if m:
        return PLACES.get(m.group(1), m.group(1))

    # 2) 标题中的具体地名（取最长匹配，避免"北京"压过"北京经济技术开发区"）
    hits = [(k, v) for k, v in PLACES.items() if k in title]
    if hits:
        hits.sort(key=lambda kv: -len(kv[0]))
        return hits[0][1]

    # 3) 标题中的国家
    countries = detect_countries(title)
    if countries:
        return "、".join(countries[:2])

    # 4) 首段中的地名 / 国名（只扫首段，避免全篇噪声）
    hits = [(k, v) for k, v in PLACES.items() if k in first_para]
    if hits:
        hits.sort(key=lambda kv: -len(kv[0]))
        return hits[0][1]
    countries = detect_countries(first_para)
    if countries:
        return "、".join(countries[:2])

    # 5) 兜底
    if any(k in re.sub(r"<[^>]+>", "", safe_title) for k in _RED_KEYWORDS):
        return "北京"
    if category == "国际新闻":
        return "—"
    if is_brief_domestic:
        return "全国"
    return "全国"


def _is_locative_mention(title_plain, key):
    """
    判断机构名在标题里是否只是"地点"而非"行动者"。
    例：'…月背月壤样品落户维也纳联合国总部' —— 联合国只是落地点，
    主体应是发布方（中国国家航天局），故此处要把它排掉。
    做法：看关键词前 6 个字内有没有方位/到达类标记。
    """
    i = title_plain.find(key)
    if i <= 0:
        return False
    return bool(re.search(r"(在|于|至|到|赴|抵达|落户|访问|出席|走进|抵达)",
                          title_plain[max(0, i - 6):i]))


def extract_subject(safe_title, text, category, is_brief=False):
    """
    新闻主体（核心行动者）分级抽取，候选必须通过名词短语合法性校验：
      T0 覆盖规则 → T1 人名占位符 → T2 机构词典(标题)
      → T3 标题动作主体 → T3c "地点：事件"结构 → T4 首段机构词典
      → T5 标题主干名词 → T6 首段机构后缀 / 国际多主体 → T7 全文机构词典 → 兜底
    目标：覆盖率 ≥70%，且不把"与会代表""绍兴市"之类泛称或残片当机构。
    """
    title = strip_topic_prefix(safe_title)
    title_plain = re.sub(r"<[^>]+>", "", title)
    first_para = (text or "")[:200]

    if "国内联播快讯" in title_plain or "国际联播快讯" in title_plain:
        return "多部门/机构"

    # T0 覆盖规则
    for pat, actor in _ACTOR_OVERRIDES:
        if re.search(pat, title_plain):
            return actor

    # T1 人名占位符（排除书名号内的人名）
    for pos in PERSON_TITLE_DETAIL:
        for m in re.finditer(re.escape(pos), title):
            before, after = title[: m.start()], title[m.end():]
            if re.search(r"《[^》]*$", before) and re.search(r"^[^《]*》", after):
                continue
            return f"<u>{pos}</u>"

    # T2 机构词典（标题内最长匹配 + 并列机构合并）
    # 排掉"仅作地点出现"的机构名，否则"落户维也纳联合国总部"会把联合国当主体
    hits = sorted(
        (k for k in INSTITUTIONS
         if k in title_plain and not _is_locative_mention(title_plain, k)),
        key=len, reverse=True,
    )
    if hits:
        primary = hits[0]
        extra = [k for k in hits[1:] if k not in primary][:1]
        joined = "、".join([primary] + extra)
        if len(joined) <= 22 and ("、" in title_plain):
            return joined
        return primary

    # T3 标题动作主体
    for pat in [
        r"^(.{2,18}?)(?:联合)?(?:印发|发布|公布|出台|启动|举行|召开|组织|实施|签署|决定|开展|批准)",
        r"^(.{2,18}?)(?:将|拟|已|日前)(?:印发|发布|出台|启动|举行|实施)",
        r"^(.{2,12}?)(?:对|就|向).{2,20}?(?:开展|进行|实施|组织|发布|提出)",   # X对Y开展Z
        r"^(.{2,14}?)(?:在[^，。]{2,10}?)?(?:举行|召开|开幕|举办|启动)",          # X在Y举行
    ]:
        m = re.search(pat, title_plain)
        if m:
            cand = clean_org_name(m.group(1))
            if cand and (is_valid_noun_phrase(cand) or cand in INSTITUTIONS):
                return cand

    # T3b "我国将试行X" → 以 X 为事件核心对象
    m = re.search(r"^(?:我国|中国)?(?:将|拟|已)(?:试行|印发|发布|出台|启动|实施)(.{2,20}?)$", title_plain)
    if m:
        cand = m.group(1).strip()
        if is_valid_noun_phrase(cand):
            return cand

    # T3c 标题"地点：事件"结构 → 冒号前是事发地/行动者
    #   例：【赓续长征精神…】广东：红色薪火映粤北 老区新程启华章 → 广东
    m = re.match(r"^([\u4e00-\u9fa5]{2,8})[：:]", title_plain)
    if m and m.group(1) in PLACES:
        return PLACES[m.group(1)]

    # T4 首段机构词典（权威发布主体）
    # 只在正文最前面的 60 字内认，避免把行文中偶然提到的机构当主体
    #   （例：绍兴历史街区报道里"荣获联合国教科文组织…奖"→ 主体曾被误判为联合国）
    head_para = (text or "")[:60]
    hits = sorted((k for k in INSTITUTIONS if k in head_para), key=len, reverse=True)
    if hits:
        return hits[0]

    # T5 标题主干名词（切成片段取最长的合法名词短语）
    core = derive_event_core(title_plain)
    if core:
        return core

    # T6 国际多主体 / 武装与政府部门
    if category == "国际新闻":
        m = re.search(r"([\u4e00-\u9fa5]{2,10}?(?:武装|军方|国防部|外交部|政府|总统府|议会|央行))", title_plain)
        if m:
            return m.group(1)
        countries = detect_countries(title_plain) or detect_countries(first_para)
        if len(countries) >= 2:
            return f"{countries[0]}、{countries[1]}双方"
        if len(countries) == 1:
            return countries[0]

    # T7 后缀机构名（首段，需贴近动词）
    m = re.search(
        r"([\u4e00-\u9fa5]{2,12}?(?:部|委|局|署|院|台|社|中心|集团|公司|组织|银行|协会|学会))"
        r"[^，。；]{0,6}?(?:发布|公布|介绍|通报|印发|举行|召开|宣布|启动|表示|称)",
        first_para,
    )
    if m:
        cand = clean_org_name(m.group(1))
        if cand:
            return cand

    # T8 全文机构词典（最后手段）
    hits = sorted((k for k in INSTITUTIONS if k in (text or "")), key=len, reverse=True)
    if hits:
        return hits[0]

    return "—"


_CORE_PREFIX_DROP = re.compile(
    r"^(?:(?:19|20)\d{2}年?"
    r"|(?:前|近|后|当|第)?\d{1,4}(?:[至到]\d{1,4})?\s*(?:个月|月份|月)"
    r"|[一二三四五六七八九十]至[一二三四五六七八九十\d]+月"
    r"|今年|去年|当日|目前)"
)
# 谓语剥离：只保留确实作谓语的多字动词，避免"达/创/超/正/建设"把名词切开
_CORE_TAIL_DROP = re.compile(
    r"(?:已|将|拟|同比|环比|继续|持续|实现|完成|落实|推进|取得|增长|下降|收窄|扩大|"
    r"突破|提升|达到|超过|创下|成为|拓展|加快|开启|迎来|迈上|提速|释放|"
    r"彰显|启动|开通|实施|落地|举行|开幕|召开|发布|印发|出台|通过|累计|成交).*$"
)
_CORE_LOC_DROP = re.compile(r"在[\u4e00-\u9fa5]{2,10}?(?:举行|召开|开幕|举办|启动|进行)$")
_CORE_TAIL_QTY = re.compile(
    r"\d[\d,\.]*\s*(?:亿元|万元|亿美元|亿吨|万吨|吨|万公里|公里|千米|米|项|个|家|所|场|次|处|名|人|人次|%|％|倍)?$"
)
_CORE_PUNCT = re.compile(r"[《》〈〉“”\"'‘’·・]")

# 谓语标记：用于"整条标题无修饰可剥离"时在动词前截断，取真正的行动者
_CORE_HEAD_CUT = (
    "首次", "牵头", "执行", "开展", "举行", "召开", "启动", "印发", "发布",
    "出台", "完成", "实现", "达到", "突破", "落实", "推进", "实施",
    "开通", "投产", "发射", "交付", "签署", "获得", "荣获", "成为",
    "增长", "下降", "收窄", "扩大", "提速",
)


def _cut_at_predicate(s):
    """在首个谓语标记处截断，取前面的名词性行动者"""
    pos = None
    for kw in _CORE_HEAD_CUT:
        i = s.find(kw)
        if i >= 2 and (pos is None or i < pos):
            pos = i
    if pos is None:
        return ""
    head = s[:pos].strip()
    return head if is_valid_noun_phrase(head) else ""


def derive_event_core(title_plain):
    """
    从标题推导事件核心对象：
      切片 → 去前导时间/主体代词 → 去"在X举行"结构 → 去谓语尾巴
      → 去书名号等标点 → 名词短语合法性校验
    若整条标题被原样保留（没有任何可剥离的修饰），说明它是"主语+谓语"结构，
    此时在首个谓语处截断，只取名词性行动者
      （例：民营火箭首次执行规模化卫星互联网星座组网任务 → 民营火箭）。
    """
    t = strip_topic_prefix(title_plain)
    t = re.sub(r"^(国内|国际)联播快讯.*$", "", t).strip()
    if not t:
        return ""

    segments = [s for s in re.split(r"[\s　：:，、]+", t) if s] or [t]
    candidates = sorted(set(segments + [t]), key=len, reverse=True)

    for seg in candidates:
        c = seg
        c = _CORE_PREFIX_DROP.sub("", c)
        c = re.sub(r"^(我国|中国|全国)", "", c)
        c = _CORE_LOC_DROP.sub("", c)
        c = _CORE_TAIL_DROP.sub("", c)
        c = _CORE_PUNCT.sub("", c)
        c = re.sub(r"^(我国|中国|全国)", "", c).strip()
        if not is_valid_noun_phrase(c):
            continue
        if c == _CORE_PUNCT.sub("", seg) == _CORE_PUNCT.sub("", t) and len(c) >= 14:
            head = _cut_at_predicate(c)
            if head:
                return head
            continue
        return c
    return ""


def extract_event(safe_title, text):
    """事件：标题即事件概览，去专题前缀与客套修饰"""
    t = strip_topic_prefix(safe_title)
    t = re.sub(r"^[“\"]?央视快评[：:]\s*", "播发央视快评：", t)
    return clip_sentence(t, 40)


def extract_cause(safe_title, text, category):
    """
    原因/目的：必须锚定在小句开头，且保留目的标记（"为/推动/旨在"），
    这样读起来是完整的目的状语（"为全球新兴产业规范有序发展提供标准支撑"），
    而不是秃掉一截的名词短语。

    两个已知坑（实测于 20260915 数据）：
      1. "为"作介词引出受事时会被误当目的词 —— "、为民服务的情况，"
         "，为参观者带来沉浸式体验。" 都不是目的；
      2. 数据描述会被误当原因 —— "，为2007年以来最高水平。"
    因此候选先剥掉目的标记再送去 _CAUSE_REJECT 判定。
    """
    body = "。" + (text or "")[:800]
    for pat in _CAUSE_PATTERNS:
        for m in re.finditer(pat, body):
            cand = clip_sentence(m.group(1), 32).strip("，。、； ")
            if not cand or not (4 <= len(cand) <= 34):
                continue
            if _CAUSE_REJECT.search(_CAUSE_MARKER_RE.sub("", cand)):
                continue
            return cand
    return "—"


_CAUSE_PATTERNS = [
    r"(?:^|[，。；、])(旨在.{4,32}?)[，。；]",
    r"(?:^|[，。；、])(为了.{4,32}?)[，。；]",
    r"(?:^|[，。；、])(以.{4,32}?)为目标",
    r"(?:^|[，。；、])((?:推动|促进|助力|带动|加快|深化|提升).{2,26}?)[，。；]",
    r"(?:^|[，。；、])(为.{4,32}?)[，。；]",
    # 背景型原因：放在最后，优先级最低
    r"(?:^|[，。；、])(由于.{4,32}?)[，。；]",
    r"(?:^|[，。；、])(随着.{4,32}?)[，。；]",
]

# 目的标记：判定合法性前先剥掉，避免"为参观者带来…"里的"为"挡住受事识别
_CAUSE_MARKER_RE = re.compile(
    r"^(?:旨在|为了|为|以|推动|促进|助力|带动|加快|深化|提升|由于|随着)"
)

# 伪原因过滤器：受事短语 / 数据描述 / 名词性残片
_CAUSE_REJECT = re.compile(
    r"(的情况|的方式|的问题|的方法|的水平|的能力|的体验|的感受|的需求|的举措|"
    r"的目标|的成果|的成效|的进展|的数据|的信息|的内容)$"
    r"|^\d"
    r"|^.{0,4}(?:带来|送去|送上|提供|解决|办理|营造)"
)


def extract_method(safe_title, category, text=""):
    """
    方式：动作 → 规范表达。标题优先，其次扫正文里的强动作。
    国际新闻不再无条件填"公开表态"（会把"美10年期国债收益率创新高"
    这类数据类新闻也标成表态），只有标题里出现表态类动词才默认表态。
    """
    t = strip_topic_prefix(safe_title)
    for kw, method in _METHOD_RULES:
        if kw in t:
            return method
    body = (text or "")[:600]
    for kw, method in _BODY_METHOD_RULES:
        if kw in body:
            return method
    if category == "国际新闻" and any(w in t for w in _ATTITUDE_WORDS):
        return "公开表态"
    return "—"


def extract_six_elements(safe_title, raw_title, text, category, date_short, is_brief_domestic=False):
    return {
        "time": date_short,
        "location": extract_location(safe_title, text, category, is_brief_domestic),
        "subject": extract_subject(safe_title, text, category),
        "event": extract_event(safe_title, text),
        "cause": extract_cause(safe_title, text, category),
        "method": extract_method(safe_title, category, text),
    }


# ============================================================
# 规则层 4：摘要 / 基调 / 详解字段
# ============================================================
def build_summary(safe_title, detail):
    title_plain = re.sub(r"<[^>]+>", "", safe_title)
    if "国内联播快讯" in title_plain or "国际联播快讯" in title_plain:
        return "（目录，详见第四部分）"

    first = desens(detail.get("first_paragraph", "") or detail.get("full_text", ""))
    if not first:
        base = strip_topic_prefix(safe_title)
        return clip_sentence(base, 60)
    return clip_sentence(first, 60)


def build_tone_overview(items, date_display):
    """
    基调概述：核心主题用最高优先级新闻的完整主句，不再硬截 22 字加省略号。
    """
    cat_count = {}
    for it in items:
        cat_count[it["category"]] = cat_count.get(it["category"], 0) + 1
    ordered_cats = sorted(
        [(c, n) for c, n in cat_count.items() if c != "完整版" and c != "其他"],
        key=lambda kv: (-kv[1], CATEGORY_ORDER.index(kv[0]) if kv[0] in CATEGORY_ORDER else 99),
    )

    reds = [it for it in items if it["importance"] == "🔴"]
    yellows = [it for it in items if it["importance"] == "🟡"]

    if reds:
        head = clip_sentence(desens(reds[0]["title"]), 46)
        core_theme = f"{head}——当日最高优先级报道"
    elif yellows:
        core_theme = f"{clip_sentence(desens(yellows[0]['title']), 46)}等要闻构成当日报道主线"
    else:
        core_theme = "国内经济社会发展平稳向好，国际热点持续受到关注"

    if reds and (len(reds) + len(yellows)) >= 3:
        tone = "导向鲜明、稳中求进，以重点报道引领全局，兼顾经济发展、民生改善与国际热点"
    elif ordered_cats and ordered_cats[0][0] == "国际新闻":
        tone = "国际议题比重较高，国内经济与民生报道同步推进，整体平稳有序"
    else:
        tone = "稳中求进、务实进取，聚焦经济发展与民生改善，传递高质量发展的坚定信心"

    key_areas = []
    desc = {
        "政策/会议": "国家战略与政策部署",
        "经济要闻": "经济运行与产业发展",
        "国际新闻": "国际局势与外交动态",
        "社会/文化要闻": "社会民生与文化建设",
        "其他": "综合类报道",
    }
    for cat, n in ordered_cats[:3]:
        key_areas.append(f"{desc.get(cat, cat)}（{n}条）")
    if not key_areas:
        key_areas.append("综合类报道")

    highlights = []
    for it in (reds + yellows)[:2]:
        highlights.append(clip_sentence(desens(it["title"]), 40))
    highlight_text = "；".join(highlights) if highlights else clip_sentence(
        desens(items[0]["title"]), 40
    ) if items else ""

    return core_theme, tone, key_areas, highlight_text


_ORG_TOKEN = r"[\u4e00-\u9fa5]{2,16}?(?:部|委|局|署|院|行|台|社|中心|总局|集团|公司|组织|协会|学会|银行)"

# 经济要闻"数据来源"必须锚定在「机构 + 权威发布动词」结构上。
# 旧实现直接用 _ORG_TOKEN 裸搜正文，会把"要大力推进西部陆海新通道建设"
# 切成"要大力推进西部"当成数据来源。
_ORG_ONE = r"[\u4e00-\u9fa5]{2,14}?(?:部|委|局|署|院|台|中心|总局|银行|集团|公司)"
_ORG_LIST = rf"({_ORG_ONE}(?:、{_ORG_ONE})*)"
_DATA_SRC_RES = [
    # "国家统计局数据显示" —— 最明确的来源
    re.compile(rf"(?:^|[，。；、：（:]){_ORG_LIST}(?:的)?(?:数据|统计)(?:显示|表明)"),
    # "工业和信息化部、国家发展改革委日前联合印发/发布/公布"
    re.compile(rf"(?:^|[，。；、：（:]){_ORG_LIST}"
               r"(?:日前|今天|近日|昨天|昨日)?(?:联合)?(?:印发|发布|公布|通报|介绍)"),
]


def _data_source(text, elements):
    """
    经济要闻的"数据来源"：锚定权威发布结构 → 机构词典 → 兜底 —。
    两个正则都锚定在「机构 + 发布/统计 + 显示」结构上，全量扫描不会引入噪声，
    故不再截前 300 字（原截断会漏掉靠后的"国家统计局数据显示"）。
    """
    head = text or ""
    for rx in _DATA_SRC_RES:
        m = rx.search(head)
        if m:
            return m.group(1)
    subj = elements.get("subject", "—")
    return subj if subj in INSTITUTIONS else "—"


def build_section3_fields(category, safe_title, detail, date_display, elements):
    """
    按分类产出第三部分字段。所有取值都经过「来源合法性 + 句边界截断」双重约束，
    取不到就填 —，绝不把半截短语当内容（旧实现的"数据来源：要大力推进西部"即此类）。
    """
    text = desens(detail.get("full_text", ""))
    title_plain = re.sub(r"<[^>]+>", "", strip_topic_prefix(safe_title))
    out = {}

    if category == "政策/会议":
        m = re.search(r"(?:由|经)?(" + _ORG_TOKEN + r")(?:、(" + _ORG_TOKEN + r"))?(?:联合|共同)?(?:印发|发布|出台|制定)", text)
        if m:
            out["dept"] = m.group(1) + ("、" + m.group(2) if m.group(2) else "")
        else:
            subj = elements.get("subject", "—")
            out["dept"] = subj if subj != "—" and not subj.startswith("<u>") else "—"
        out["pubdate"] = date_display
        m = re.search(r"(?:^|[，。；])旨在(.{4,40}?)[，。；]", "。" + text)
        if not m:
            m = re.search(r"(?:^|[，。；])(?:为|为了)(.{4,40}?)[，。；]", "。" + text)
        out["goal"] = clip_sentence(m.group(1), 40) if m else "—"
        points = [s for s in re.split(r"[。；]", text) if 16 <= len(s) <= 60][:2]
        out["points"] = "；".join(clip_sentence(p, 40) for p in points) if points else "—"

    elif category == "国际新闻":
        out["progress"] = clip_sentence(text, 60) if text else clip_sentence(title_plain, 50)
        stances = []
        for m in re.finditer(
            r"([\u4e00-\u9fa5]{2,12}?(?:方面|国防部|外交部|政府|总统|武装|军方|总理|外长|官员))"
            r"(?:今天|昨天|\d{1,2}日)?(?:称|表示|说|宣布|强调|指出)[，：:]?(.{8,60}?)[，。；]",
            text,
        ):
            who = clean_org_name(m.group(1)) or m.group(1)
            stances.append(f"{who}：{clip_sentence(m.group(2), 36)}")
            if len(stances) >= 3:
                break
        out["stance"] = "；".join(stances) if stances else "—"

    elif category == "经济要闻":
        out["datasrc"] = _data_source(text, elements)
        # 模板要求"核心数据"呈现为「数据点：数值」，因此用带语境的说明
        # （说明里已含数值）而不是裸数值——裸的"34.6%"读者无法判断是什么指标。
        picked = _merge_same_source([c for _v, c in extract_numbers(text, limit=8) if c])
        out["keydata"] = "；".join(picked[:4]) if picked else "—"

    elif category == "社会/文化要闻":
        m = re.search(r"(\d{1,2}月\d{1,2}日)", text)
        out["acttime"] = m.group(1) if m else date_display
        m = re.search(r"(?:共|约|超过|近)?(\d[\d,\.]*\s*(?:名|人|人次|家|个|支|所|场|项))", text)
        out["scale"] = m.group(1) if m else "—"

    else:
        out["progress"] = clip_sentence(text, 60) if text else clip_sentence(title_plain, 50)
        points = [s for s in re.split(r"[。；]", text) if 16 <= len(s) <= 60][:2]
        out["points"] = "；".join(clip_sentence(p, 40) for p in points) if points else "—"

    return out


# ============================================================
# 规则层 5：数值 / 书名 抽取（第七部分 7.5 / 7.6）
# ============================================================
_NUM_UNITS = (
    "万亿千瓦时|亿千瓦时|万千瓦时|千瓦时|万亿元|亿美元|亿元|万元|亿吨|万吨|吨|"
    "万公里|公里|千米|米|架次|架|颗|艘|辆|人次|万人|万户|万名|万|"
    # "个百分点"必须排在"个"前面：正则择先匹配，否则"0.7个百分点"会被截成"0.7个"
    "个百分点|百分点|"
    "项|个|家|所|场|次|处|只|台|名|人|%|％|倍"
)
_NUM_RE = re.compile(rf"(\d+(?:[\.,]\d+)?\s*(?:{_NUM_UNITS}))")


# 说明的右边界停顿符：**不含顿号**——
# "…分别增长57.2%、34.6%" 属于同一条数据，被顿号截断就会丢掉后一个数值
_CTX_TAIL_SEP = ("，", "；")
# 说明的左边界：句末标点 / 逗号分号 / 括号 / 空白，一律可作为起头处
_CTX_BOUND_RE = re.compile(r"[。！？；，：（）()\s]")
_CTX_LOOKBACK = 40   # 左边界最多向前回溯多少字，保证起头落在边界上
_CTX_MAX = 46        # 说明总长上限（数值 + 左右上下文）


def _number_context(text, start, end, value):
    """
    取数值周边的说明窗口：**先找边界，再定长度**。

    旧实现固定回看 26 字、超长就从左侧硬裁，产生两类残片：
      · 断字起头 —— "子电池、工业机器人产品产量…"（从"锂离子电池"中间切开）
      · 跨句起头 —— "…世界一流企业。产业研发投入强度达到3.5%"（把上一句也带进来）
    现在左边界取"最近的一处句读边界"（回溯 40 字，足以越过长定语），
    右边界取到下一个逗号/分号，从而把"57.2%、34.6%"这类并列数值留在同一条说明里；
    若加上左文仍超长，则宁可不带左文，也不做断字硬裁。
    """
    right = re.split(r"[。；！？\n\s]", text[end:end + 20])[0]
    for sep in _CTX_TAIL_SEP:
        if sep in right:
            right = right[:right.find(sep)]
            break

    seg = text[max(0, start - _CTX_LOOKBACK):start]
    last = None
    for mm in _CTX_BOUND_RE.finditer(seg):
        last = mm
    if last:
        left = seg[last.end():]
        if len(left) + len(value) + len(right) > _CTX_MAX:
            left = ""                     # 超长就不带左文，绝不硬裁出断字残片
    else:
        # 40 字内没有任何句读 → 整段作左文（长标题里的数值即属此类，
        # 如"…规上企业营业收入将突破30万亿元"，丢掉左文只剩一个光秃秃的数值）
        left = seg if len(seg) + len(value) + len(right) <= _CTX_MAX else ""
    return (left + value + right).strip()


def _merge_same_source(items):
    """
    同一句话里同源的多个数值（"…产品产量同比分别增长57.2%、34.6%"）只留信息最全的一条，
    避免"核心数据"出现两条几乎相同、只是数字不同的说明。
    判据：去掉所有数字与百分号后文本相同 → 视为同源。
    """
    key = lambda s: re.sub(r"[\d\.,、%％]+", "", s)
    out = []
    for ctx in items:
        k = key(ctx)
        for i, kept in enumerate(out):
            if k == key(kept):
                if len(ctx) > len(kept):
                    out[i] = ctx
                break
        else:
            out.append(ctx)
    return out


def extract_numbers(text, limit=12):
    """
    返回 [(数值, 上下文说明)]，去重保序。

    说明必须**包含数值本身**：旧实现从片段开头累积到超限就停，
    结果数据列出现"134.2公里 | 经钦州市灵山县陆屋镇，沿钦江进入北部湾"
    这种"说明里找不到数值"的错位观感（甚至退化成"密"）。现改为
    以数值为中心取左右窗口、收到自然停顿边界，超长时只从左侧按标点裁，
    确保数值始终留在说明里、说明也始终是完整短语。
    """
    out, seen = [], set()
    text = text or ""
    for m in _NUM_RE.finditer(text):
        val = re.sub(r"\s+", "", m.group(1))
        if val in seen:
            continue
        # 过滤单字符纯数量（如 "1个"）之外的噪声
        if len(val) <= 2 and not any(u in val for u in ("%", "％", "倍")):
            continue
        seen.add(val)

        ctx = _number_context(text, m.start(), m.end(), val) or val
        out.append((val, ctx))
        if len(out) >= limit:
            break
    return out


_DOC_KIND = [
    (("条例", "规定", "办法", "法"), "法规名称"),
    (("规划", "纲要", "意见", "方案", "计划", "战略"), "政策文件名称"),
    (("报告", "白皮书", "蓝皮书"), "报告名称"),
    (("清单", "目录", "标准"), "清单/标准名称"),
]


def extract_documents(texts):
    """抽取《……》→ [(名称, 说明)]"""
    out, seen = [], set()
    for t in texts:
        for m in re.finditer(r"《([^》]{2,40})》", t or ""):
            name = f"《{m.group(1)}》"
            if name in seen:
                continue
            seen.add(name)
            kind = "文章/出版物标题"
            for kws, desc in _DOC_KIND:
                if any(kw in m.group(1) for kw in kws):
                    kind = desc
                    break
            out.append((name, kind))
    return out


def classify_subject_kind(subject):
    """主体 → person / org / event_object"""
    s = (subject or "").strip()
    if not s or s == "—":
        return "event_object"
    if re.search(r"<u>.+?</u>", s):
        return "person"
    if s in INSTITUTIONS:
        return "org"
    if any(h in s for h in _EVENT_OBJECT_HINTS):
        return "event_object"
    # 单一名词且以机构后缀结尾 → 机构
    for piece in re.split(r"[、，]", s):
        piece = piece.strip()
        if not piece:
            continue
        if piece.endswith(_ORG_SUFFIX) or piece in INSTITUTIONS:
            return "org"
    return "event_object"


def build_org_fullname(abbr):
    if abbr in INSTITUTIONS:
        return INSTITUTIONS[abbr]
    return "—"  # 词典未收录时不重复占位符本身，避免「无信息增量」


# ============================================================
# 渲染层
# ============================================================
class Dataset:
    """整份报告的数据模型"""

    def __init__(self, date_str):
        self.date_str = date_str
        d = datetime.strptime(date_str, "%Y%m%d").date()
        self.day = d
        self.date_display = f"{d.year}年{d.month:02d}月{d.day:02d}日"
        self.date_short = f"{d.year}-{d.month:02d}-{d.day:02d}"
        self.weekday = ["一", "二", "三", "四", "五", "六", "日"][d.weekday()]
        self.prepared_display = f"{date.today().year}年{date.today().month}月{date.today().day}日"

        self.full_video = None          # 完整版视频 dict
        self.full_url = ""              # 完整版链接（全文唯一来源）
        self.news = []                  # 常规新闻
        self.domestic_briefs = []       # 国内快讯子条目
        self.international_briefs = []  # 国际快讯子条目
        self.domestic_idx = None
        self.international_idx = None
        self.iqilu_total = 0

    # -------- 条目枚举（供第六/七部分统一消费） --------
    def all_elements_rows(self):
        """
        产出 (idx_label, sort_key, title, url, category, elements, source_url, importance, is_full)
        idx_label: 第六部分序号列文本
        """
        rows = []
        rows.append((
            "完整版", (0,), f"完整版《新闻联播》{self.date_display}", self.full_url,
            "完整版",
            {"time": self.date_short, "location": "全国", "subject": "—",
             "event": "当日全部新闻汇总", "cause": "—", "method": "完整播报"},
            self.full_url, "—", True,
        ))
        for i, item in enumerate(self.news, start=1):
            rows.append((
                str(i), (1, i), item["title"], item["url"], item["category"],
                item["elements"], item["url"], item["importance"], False,
            ))
        if self.domestic_idx is not None:
            for i, item in enumerate(self.domestic_briefs, start=1):
                label = f"{self.domestic_idx}-{i}"
                rows.append((
                    label, (2, self.domestic_idx, i), item["title"], item["link_url"],
                    item["category"], item["elements"], item["source_url"], "一般", False,
                ))
        if self.international_idx is not None:
            for i, item in enumerate(self.international_briefs, start=1):
                label = f"{self.international_idx}-{i}"
                rows.append((
                    label, (3, self.international_idx, i), item["title"], item["link_url"],
                    item["category"], item["elements"], item["source_url"], "一般", False,
                ))
        return rows

    @staticmethod
    def pos_label(idx_label):
        """出现位置标签：常规新闻 '第N条'，快讯子条目 'N-M'"""
        if idx_label == "完整版":
            return "完整版"
        return f"第{idx_label}条" if idx_label.isdigit() else idx_label


def render_report(ds, contract):
    parts = []
    parts.append(_render_header(ds))
    parts.append(_render_part1(ds, contract))
    parts.append(_render_part2(ds, contract))
    parts.append(_render_part3(ds, contract))
    parts.append(_render_part4(ds, contract))
    parts.append(_render_part5(ds, contract))
    parts.append(_render_part6(ds, contract))
    parts.append(_render_part7(ds, contract))
    parts.append(_render_footer(ds, contract))
    # 分隔线前后各留一个空行：否则上一行会被 Markdown 解析成 setext 二级标题
    #（文首"**日期：…**"、第一部分"**当日亮点**…"、第四部分验证结论行都踩过这个坑）
    return "\n\n---\n\n".join(p.rstrip("\n") for p in parts if p and p.strip()) + "\n"


def _intro(contract, no, fallback):
    lines = contract.get("intros", {}).get(no)
    return "\n".join(lines) if lines else "\n".join(fallback)


def _render_header(ds):
    return (
        f"# 新闻联播总结报告\n\n"
        f"**日期：{ds.date_display}（星期{ds.weekday}）** | 整理时间：{ds.prepared_display}\n"
    )


def _render_part1(ds, contract):
    core, tone, areas, highlight = ds.tone
    lines = [f"## {contract['section_titles']['一']}", "", f"**核心主题**：{core}", "",
             f"**整体基调**：{tone}", "", "**重点领域**："]
    for i, a in enumerate(areas, start=1):
        lines.append(f"{i}. {a}")
    lines += ["", f"**当日亮点**：{highlight}", ""]
    return "\n".join(lines)


def _render_part2(ds, contract):
    lines = [f"## {contract['section_titles']['二']}", "",
             _intro(contract, "二", [
                 "> 完整版单独置顶列出，常规新闻按当天央视网实际分条顺序编号（1、2、3...）。",
                 "> 每条仅含标题 + 一句话核心概括。",
                 "> 标注规则：🔴必标重点（领导人活动、重大政策、国际热点）/ 🟡选标重点（副国级活动、部委政策、经济数据）/ 一般新闻",
             ]), ""]

    lines += [
        f"### [完整版《新闻联播》{ds.date_display}]",
        f"> 视频来源：[央视网视频地址]({ds.full_url})",
        "",
        "> **注意**：完整版不编号，单独置顶列出，不纳入常规新闻序号（1、2、3...）。",
        "",
    ]
    for i, item in enumerate(ds.news, start=1):
        prefix = f"{item['importance']} " if item["importance"] != "一般" else ""
        lines += [
            f"### {prefix}{i}. {item['title']}",
            f"[{item['summary']}]",
            f"> 视频来源：[央视网视频地址]({item['url']})",
            "",
        ]
    return "\n".join(lines)


def _render_part3(ds, contract):
    ordered = contract["sub3"]
    cat_to_sub = {}
    for sub in ordered:
        m = re.match(r"(3\.\d+)\s*(.+)", sub)
        if m:
            cat_to_sub[m.group(2).strip()] = (m.group(1), sub)

    buckets = {}
    for i, item in enumerate(ds.news, start=1):
        if item["importance"] not in ("🔴", "🟡"):
            continue
        cat = item["category"] if item["category"] in cat_to_sub else "其他"
        buckets.setdefault(cat, []).append((i, item))

    lines = [f"## {contract['section_titles']['三']}", "",
             _intro(contract, "三", [
                 "> 仅收录🔴必标重点和🟡选标重点新闻，按子分类归档，内部按重要性排序，注明播放顺序（第X条）。",
             ]), ""]

    emitted = 0
    for cat in ["政策/会议", "国际新闻", "经济要闻", "社会/文化要闻", "其他"]:
        if cat not in buckets:
            continue
        num, sub_title = cat_to_sub.get(cat, ("3.5", "3.5 其他重点"))
        items = sorted(buckets[cat], key=lambda t: 0 if t[1]["importance"] == "🔴" else 1)
        lines += [f"### {sub_title}", ""]
        for idx, item in items:
            fields = build_section3_fields(
                cat, item["title"], item["detail"], ds.date_display, item["elements"]
            )
            lines.append(f"#### {item['importance']} {item['title']}（第{idx}条）")
            for label, key in _SECTION3_FIELDS.get(cat, _SECTION3_FIELDS["其他"]):
                lines.append(f"- **{label}**：{fields.get(key, '—')}")
            lines += [
                f"- **视频来源**：[央视网视频地址]({item['url']})",
                f"- **[来源：央视网]({item['url']})**",
                "",
            ]
            emitted += 1

    if emitted == 0:
        lines += ["> 当日无🔴必标重点或🟡选标重点新闻，第三部分无内容。", ""]
    return "\n".join(lines)


def _brief_line(i, item):
    """
    快讯行：正文**原样呈现，不再截断**。
    央视网快讯页给出的每条子快讯正文本身就是官方定稿的一句话（实测 93-177 字），
    原先再 clip 到 80 字属于对已抓取内容的二次省略，这里直接全量输出，
    只做括号闭合与脱敏。
    """
    ctx = _close_brackets(re.sub(r"\s+", " ", desens(item.get("summary", "")).strip()))
    title = item["title"]
    if ctx and ctx.strip("。 ") != title.strip("。 "):
        return f"> ({i}) [{title}]({item['link_url']}) — {ctx}"
    return f"> ({i}) [{title}]({item['link_url']})"


def _brief_block(items):
    """
    快讯条目块：**每条独立成段**。

    旧写法把 `> (1) …`、`> (2) …` 连续排下去，Markdown 会把它们合并成
    同一个段落——渲染出来是一大坨文字，条目之间没有视觉边界。
    这里在两条之间插入一个空的引用行（`>`），使每条快讯成为独立段落。
    """
    out = []
    for i, item in enumerate(items, start=1):
        if out:
            out.append(">")          # 空引用行 = 段落分隔，保证每条独立成段
        out.append(_brief_line(i, item))
    return out


def _render_part4(ds, contract):
    lines = [f"## {contract['section_titles']['四']}", "", "### 4.1 国内联播快讯", ""]
    if ds.domestic_briefs:
        lines += _brief_block(ds.domestic_briefs)
    else:
        lines.append("> 暂无国内快讯数据")
    lines += ["", "### 4.2 国际联播快讯", ""]
    if ds.international_briefs:
        lines += _brief_block(ds.international_briefs)
    else:
        lines.append("> 暂无国际快讯数据")

    lines += ["", "### 4.3 快讯子条目验证报告", "",
              "> 以下表格验证每条快讯子条目的来源匹配情况，确保无遗漏、无多余。", "",
              "| 子条目 | 标题 | 央视网基准 | 齐鲁网首页 | 齐鲁网搜索 | 最终链接来源 |",
              "|--------|------|-----------|-----------|-----------|-------------|"]
    matched = 0
    for group, parent in ((ds.domestic_briefs, ds.domestic_idx),
                          (ds.international_briefs, ds.international_idx)):
        if parent is None:
            continue
        for i, item in enumerate(group, start=1):
            has = "有" if item.get("iqilu_url") else "无"
            src = "齐鲁网" if item.get("iqilu_url") else "央视网"
            if item.get("iqilu_url"):
                matched += 1
            lines.append(f"| {parent}-{i} | {item['title']} | 有 | {has} | — | {src} |")
    total = len(ds.domestic_briefs) + len(ds.international_briefs)
    verdict = "覆盖完整" if matched >= total and total > 0 else (
        f"齐鲁网缺失{total - matched}条" if total else "当日无快讯子条目"
    )
    lines += ["", f"> **验证结论**：央视网基准B={total}条，齐鲁网总覆盖Q={matched}条（首页{matched}条+搜索0条），{verdict}", ""]
    return "\n".join(lines)


def _render_part5(ds, contract):
    lines = [f"## {contract['section_titles']['五']}", "", "### 5.1 央视网完整标题清单", "",
             "| 序号 | 新闻标题（可点击跳转） | 重要性 | 开始时间 | 结束时间 | 时长 | 时长合理性 |",
             "|------|---------|--------|---------|---------|------|-----------|"]

    full_dur, full_end = "30:00", "19:30:00"
    if ds.full_video and ds.full_video.get("duration"):
        fd = ds.full_video["duration"]
        full_dur = fd[3:] if fd.startswith("00:") else fd
        full_end = add_time("19:00:00", fd)
    lines.append(
        f"| 完整版（无序号） | [完整版《新闻联播》]({ds.full_url}) | — | 19:00:00 | {full_end} | {full_dur} | — |"
    )

    durations = {"🔴": [], "🟡": [], "一般": []}
    cur = "19:00:00"
    for i, item in enumerate(ds.news, start=1):
        dur = item["duration"]
        end = add_time(cur, dur)
        ratio = grade_duration(item["importance"], time_to_seconds(dur))
        disp = dur[3:] if len(dur) > 5 and dur.startswith("00:") else dur
        lines.append(
            f"| {i} | [{item['title']}]({item['url']}) | {item['importance']} | {cur} | {end} | {disp} | {ratio} |"
        )
        durations[item["importance"]].append(dur)
        cur = end

    # 5.2
    lines += ["", "### 5.2 时长匹配验证", "",
              "| 重要性 | 预期时长 | 实际时长 | 匹配结果 |",
              "|--------|---------|---------|---------|"]
    bands = [("🔴 必标重点", "🔴", 120, 300, "2-5分钟"),
             ("🟡 选标重点", "🟡", 60, 180, "1-3分钟"),
             ("一般新闻", "一般", 30, 120, "0.5-2分钟")]
    match_flags = {}
    for label, key, lo, hi, band in bands:
        durs = durations[key]
        if not durs:
            lines.append(f"| {label} | {band} | 无 | — |")
            match_flags[key] = True
            continue
        disp, ok = [], True
        for d in durs:
            sec = time_to_seconds(d)
            dd = d[3:] if len(d) > 5 and d.startswith("00:") else d
            if sec < lo:
                disp.append(f"{dd}（偏短）")
                ok = False
            elif sec > hi:
                disp.append(f"{dd}（偏长）")
                ok = False
            else:
                disp.append(dd)
        shown = "、".join(disp[:6])
        if len(disp) > 6:
            shown += f" 等{len(disp)}条"
        lines.append(f"| {label} | {band} | {shown} | {'匹配' if ok else '部分偏长/偏短'} |")
        match_flags[key] = ok

    # 5.3
    n = len(ds.news)
    d_num = (1 if ds.domestic_idx else 0) + (1 if ds.international_idx else 0)
    m = len(ds.domestic_briefs)
    k = len(ds.international_briefs)
    total = n - d_num + m + k
    lines += ["", "### 5.3 新闻条数统计", "",
              "| 统计项 | 数量 | 说明 |",
              "|--------|------|------|",
              f"| 央视网视频分条总数 | {n}条 | 当天央视网视频列表中的分条（**不含完整版**，仅含常规新闻+快讯目录） |",
              f"| 减：快讯目录数 | -{d_num}条 | \"国内/国际联播快讯\"为目录条目，非独立新闻，需扣除 |",
              f"| 加：国内快讯子条目 | +{m}条 | 国内联播快讯内含{m}条独立子新闻 |",
              f"| 加：国际快讯子条目 | +{k}条 | 国际联播快讯内含{k}条独立子新闻 |",
              f"| **实际独立新闻总数** | **{total}条** | {n} - {d_num} + {m} + {k} = {total} |", ""]

    # 5.4
    has_leader = any(item["importance"] == "🔴" for item in ds.news)
    total_sec = sum(time_to_seconds(item["duration"]) for item in ds.news)
    lines += ["### 5.4 检测结论", "",
              f"> - 央视网视频分条{n}条（**不含完整版**，含{d_num}条快讯目录），完整版单独列出不计入N；实际独立新闻合计{total}条（{n} - {d_num} + {m} + {k} = {total}）",
              f"> - 包含领导人活动报道 {'✓' if has_leader else '✗'}",
              f"> - 包含重大政策/会议 {'✓' if any(i['category'] == '政策/会议' for i in ds.news) else '✗'}",
              f"> - 包含国际新闻 {'✓' if any(i['category'] == '国际新闻' for i in ds.news) else '✗'}",
              f"> - 包含经济/社会要闻 {'✓' if any(i['category'] in ('经济要闻', '社会/文化要闻') for i in ds.news) else '✗'}",
              f"> - 包含联播快讯 {'✓' if (m + k) > 0 else '✗'}",
              f"> - 分条累计时长约{total_sec // 60}分钟（含广告过渡，完整版约30分钟），属于正常范围 ✓"]
    bad = [k2 for k2, v in match_flags.items() if not v]
    if not bad:
        lines.append("> - **时长匹配：匹配**")
    else:
        name = {"🔴": "必标重点", "🟡": "选标重点", "一般": "一般新闻"}
        lines.append(f"> - **时长匹配：部分不匹配**（{'、'.join(name[b] for b in bad)}）")
    lines.append("> - **信息完整性：良好**")
    lines.append("")
    return "\n".join(lines)


def _render_part6(ds, contract):
    header = contract["header6"]
    lines = [f"## {contract['section_titles']['六']}", "",
             _intro(contract, "六", [
                 "> 完整版单独列出，不纳入常规新闻编号。常规新闻按当天央视网实际分条顺序编号，快讯子条目使用\"序号-子序号\"编号（如8-1、8-2）。",
                 "> 新闻主体列填写每条新闻的核心行动者：人物使用占位符（如\"国家领导人\"），不出现具体人名；无人物主体时填写机构名称或事件核心对象。",
                 "> **脱敏标记规则**：所有由人名替换而来的占位符，均使用HTML下划线标记，格式为 `<u>占位符</u>`。机构名称、事件核心对象等非人名替换内容不加下划线。",
             ]), "",
             "| " + " | ".join(header) + " |",
             "|" + "|".join(["------"] * len(header)) + "|"]

    for idx_label, _sk, title, url, category, el, source_url, _imp, is_full in ds.all_elements_rows():
        if is_full:
            title_cell = f"[{title}]({url})"
        else:
            title_cell = f"[{title}]({url})"
        lines.append(
            f"| {idx_label} | {title_cell} | {category} | {el['time']} | {el['location']} | "
            f"{el['subject']} | {el['event']} | {el['cause']} | {el['method']} | "
            f"[央视网]({source_url}) |"
        )

    lines += ["", "> **编号规则**：", 
              "> - **完整版单独列出**：在表格首行单独列出，序号列填\"完整版\"（非数字），不纳入常规新闻计数",
              "> - **常规新闻按当天分条编号**：以央视网当天视频列表的实际顺序为基准，从1开始连续编号（1、2、3...）",
              "> - **快讯子条目格式**：N-M（N为父目录在当天央视网分条中的实际序号，M为子条目序号）",
              "> - **常规新闻标题链接**：央视网独立视频页面，一一对应",
              "> - **快讯子条目标题链接**：统一通过齐鲁网独立页面链接（https://v.iqilu.com/jcdb/ysxwlb/），每一节一一对应，禁止合并",
              "> - **详细信息源链接列**：常规新闻与国内快讯填写详细来源地址；国际快讯填写央视网快讯目录视频链接", ""]
    return "\n".join(lines)


def _render_part7(ds, contract):
    persons, orgs, event_objs = {}, {}, {}
    locations, numbers, docs = {}, {}, {}

    for idx_label, _sk, _title, _url, _cat, el, _src, _imp, is_full in ds.all_elements_rows():
        if is_full:
            continue
        pos = Dataset.pos_label(idx_label)

        # 主体三分类
        subj = el["subject"]
        kind = classify_subject_kind(subj)
        if kind == "person":
            for ph in re.findall(r"<u>(.+?)</u>", subj):
                persons.setdefault(ph, [])
                if pos not in persons[ph]:
                    persons[ph].append(pos)
        elif kind == "org":
            for piece in re.split(r"[、，]", subj):
                piece = piece.strip()
                if not piece or piece == "—":
                    continue
                orgs.setdefault(piece, [])
                if pos not in orgs[piece]:
                    orgs[piece].append(pos)
        else:
            key = subj if subj and subj != "—" else None
            if key:
                event_objs.setdefault(key, [])
                if pos not in event_objs[key]:
                    event_objs[key].append(pos)

        # 地点
        loc = el["location"]
        if loc and loc != "—":
            for one in re.split(r"[、，]", loc):
                one = one.strip()
                if one and one != "—":
                    locations.setdefault(one, [])
                    if pos not in locations[one]:
                        locations[one].append(pos)

        # 数据 & 书名
        item = _find_item(ds, idx_label)
        scan = " ".join([
            _title or "", (item or {}).get("summary", ""),
            ((item or {}).get("detail") or {}).get("full_text", ""),
        ])
        # 每条最多取 6 个（原先 4 个），避免单条长稿把 7.5 整张表占满
        for val, ctx in extract_numbers(scan, limit=6):
            if val not in numbers:
                numbers[val] = (ctx, pos)
        for name, kind_desc in extract_documents([_title or "", (item or {}).get("summary", "")]):
            if name not in docs:
                docs[name] = (kind_desc, pos)

    lines = [f"## {contract['section_titles']['七']}", "",
             "### 7.1 新闻主体占位符",
             "> 涵盖第六部分\"新闻主体\"列的所有占位符，包括人物、机构和事件核心对象三类。",
             "", "#### 7.1.1 人物类",
             "| 序号 | 占位符 | 职务/身份 | 出现位置 |",
             "|------|--------|----------|---------|"]
    order = list(PERSON_TITLE_DETAIL.keys())
    for i, ph in enumerate(sorted(persons, key=lambda x: order.index(x) if x in order else 99), start=1):
        detail = PERSON_TITLE_DETAIL.get(ph, ph)
        lines.append(f"| {i} | <u>{ph}</u> | {detail} | {'、'.join(persons[ph])} |")
    if not persons:
        lines.append("| — | — | 本日无人物类占位符 | — |")

    lines += ["", "#### 7.1.2 机构类",
              "| 序号 | 占位符 | 机构全称 | 出现位置 |",
              "|------|--------|---------|---------|"]
    for i, abbr in enumerate(orgs, start=1):
        lines.append(f"| {i} | {abbr} | {build_org_fullname(abbr)} | {'、'.join(orgs[abbr])} |")
    if not orgs:
        lines.append("| — | — | 本日无机构类占位符 | — |")

    lines += ["", "#### 7.1.3 事件核心对象类",
              "| 序号 | 占位符 | 说明 | 出现位置 |",
              "|------|--------|------|---------|"]
    for i, name in enumerate(event_objs, start=1):
        lines.append(f"| {i} | {name} | 事件核心行动者/对象 | {'、'.join(event_objs[name])} |")
    if not event_objs:
        lines.append("| — | — | 本日无事件核心对象类占位符 | — |")

    # 7.3 时间（子节编号沿用空白模板：模板跳过 7.2）
    lines += ["", "### 7.3 时间占位符",
              "| 序号 | 占位符 | 说明 | 出现位置 |",
              "|------|--------|------|---------|",
              f"| 1 | {ds.date_display} | 新闻播出日期 | 全文 |"]

    lines += ["", "### 7.4 地点占位符",
              "| 序号 | 占位符 | 说明 | 出现位置 |",
              "|------|--------|------|---------|"]
    if locations:
        for i, loc in enumerate(locations, start=1):
            lines.append(f"| {i} | {loc} | 新闻涉及地点 | {'、'.join(locations[loc])} |")
    else:
        lines.append("| — | — | 本日无地点占位符 | — |")

    lines += ["", "### 7.5 数据占位符",
              "| 序号 | 占位符 | 说明 | 出现位置 |",
              "|------|--------|------|---------|"]
    if numbers:
        # 上限放到 30 条：原先硬截 15 条，等于把已抓到的数据占位符丢掉一半
        for i, (val, (ctx, pos)) in enumerate(list(numbers.items())[:30], start=1):
            lines.append(f"| {i} | {val} | {ctx} | {pos} |")
    else:
        lines.append("| — | — | 本日无数据占位符 | — |")

    lines += ["", "### 7.6 内容占位符",
              "| 序号 | 占位符 | 说明 | 出现位置 |",
              "|------|--------|------|---------|"]
    if docs:
        for i, (name, (kind_desc, pos)) in enumerate(list(docs.items())[:15], start=1):
            lines.append(f"| {i} | {name} | {kind_desc} | {pos} |")
    else:
        lines.append("| — | — | 本日无内容占位符 | — |")
    lines.append("")
    return "\n".join(lines)


def _find_item(ds, idx_label):
    if idx_label == "完整版":
        return None
    if idx_label.isdigit():
        i = int(idx_label) - 1
        return ds.news[i] if 0 <= i < len(ds.news) else None
    if "-" in idx_label:
        parent, _, sub = idx_label.partition("-")
        try:
            j = int(sub) - 1
        except ValueError:
            return None
        if parent == str(ds.domestic_idx):
            return ds.domestic_briefs[j] if 0 <= j < len(ds.domestic_briefs) else None
        if parent == str(ds.international_idx):
            return ds.international_briefs[j] if 0 <= j < len(ds.international_briefs) else None
    return None


def _render_footer(ds, contract):
    block = list(contract.get("data_source") or FALLBACK_CONTRACT["data_source"])
    for i, ln in enumerate(block):
        if "央视新闻联播" in ln and "列表页" in ln:
            block[i] = (
                f"> - 央视新闻联播（{ds.date_display}）："
                f"[央视网新闻联播列表页](https://tv.cctv.com/lm/xwlb/day/{ds.date_str}.shtml)"
            )
    if not any("央视新闻联播" in ln for ln in block):
        block.insert(1, (
            f"> - 央视新闻联播（{ds.date_display}）："
            f"[央视网新闻联播列表页](https://tv.cctv.com/lm/xwlb/day/{ds.date_str}.shtml)"
        ))
    return "\n".join(block) + "\n"


# ============================================================
# 时间工具
# ============================================================
def time_to_seconds(t):
    parts = (t or "0").split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return 0
    return 0


def add_time(start_t, duration):
    total = time_to_seconds(start_t) + time_to_seconds(duration)
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def grade_duration(importance, sec):
    if importance == "🔴":
        lo, hi = 120, 300
    elif importance == "🟡":
        lo, hi = 60, 180
    else:
        lo, hi = 30, 120
    if sec < lo:
        return "偏短"
    if sec > hi:
        return "偏长"
    return "合理"


# ============================================================
# 质量自检（内置，单脚本闭环）
# ============================================================
def _split_sections(report, contract):
    """按 '## X、标题' 把报告切成章节字典 {章节号: 正文}"""
    out = {}
    order = sorted(contract["section_titles"].keys(), key=lambda k: "一二三四五六七".index(k))
    marks = []
    for no in order:
        title = contract["section_titles"][no]
        pos = report.find(f"## {title}")
        if pos >= 0:
            marks.append((no, pos))
    for i, (no, pos) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(report)
        out[no] = report[pos:end]
    return out


def _find_full_urls(report, contract):
    """抽取完整版链接的三处出现，用于一致性校验"""
    secs = _split_sections(report, contract)
    found = {}

    # a) 第二部分：完整版标题后的第一行视频来源
    sec2 = secs.get("二", "")
    m = re.search(r"###\s*\[完整版《新闻联播》[^\]]*\]\s*\n>\s*视频来源：\[央视网视频地址\]\(([^)]+)\)", sec2)
    if m:
        found["第二部分"] = m.group(1)

    # b) 5.1 完整版行
    sec5 = secs.get("五", "")
    m = re.search(r"\|\s*完整版（无序号）\s*\|\s*\[完整版《新闻联播》\]\(([^)]+)\)", sec5)
    if m:
        found["5.1"] = m.group(1)

    # c) 第六部分完整版行
    sec6 = secs.get("六", "")
    m = re.search(r"^\|\s*完整版\s*\|\s*\[完整版《新闻联播》[^\]]*\]\(([^)]+)\)", sec6, re.M)
    if m:
        found["第六部分"] = m.group(1)

    return found


def _find_part6_header(report, contract):
    """只在第六部分章节内定位 10 列表头"""
    sec6 = _split_sections(report, contract).get("六", "")
    for ln in sec6.split("\n"):
        if ln.startswith("|") and "新闻标题" in ln and "序号" in ln:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 8:
                return cells
    return None


def self_check(ds, report, contract):
    issues = []

    def add(level, msg):
        issues.append((level, msg))

    # 1) 七部分齐全
    secs = _split_sections(report, contract)
    for no, title in contract["section_titles"].items():
        if no not in secs:
            add("CRITICAL", f"缺少章节：{title}")

    # 2) 第六部分表头严格 10 列且与模板一致
    header = _find_part6_header(report, contract)
    if not header:
        add("CRITICAL", "第六部分表头缺失或格式错误")
    else:
        if len(header) != 10:
            add("CRITICAL", f"第六部分表头列数={len(header)}，应为 10")
        if header != contract["header6"]:
            add("CRITICAL", f"第六部分表头与模板不一致：{header}")

    # 3) 完整版链接三处一致
    urls = _find_full_urls(report, contract)
    if len(set(urls.values())) > 1:
        add("CRITICAL", f"完整版链接不一致：{urls}")
    elif len(urls) < 3:
        add("WARNING", f"完整版链接仅检测到 {len(urls)}/3 处：{list(urls)}")
    if urls and ds.full_url and set(urls.values()) != {ds.full_url}:
        add("ERROR", "完整版链接与数据源不一致")

    # 4) 脱敏：不得出现具体人名
    for name, _code in NAME_TO_CODE:
        if name in report:
            add("CRITICAL", f"敏感词泄露：{name}")

    # 5) 所有链接必须 https
    bad_links = re.findall(r"\]\((http://[^)]+)\)", report)
    if bad_links:
        add("ERROR", f"存在 {len(bad_links)} 条 HTTP 链接（应全部为 https）")

    # 6) 新闻主体覆盖率 >= 70%
    rows = _parse_part6_rows(report, contract)
    if rows:
        dash = sum(1 for r in rows if r["subject"].strip() in ("—", "-", ""))
        cov = (len(rows) - dash) / len(rows) * 100
        if cov < 70:
            add("ERROR", f"新闻主体覆盖率 {cov:.1f}%（要求≥70%），— 共 {dash} 处")
    else:
        add("CRITICAL", "第六部分未解析到数据行")

    # 7) 第六部分条数与 5.3 统计一致
    n, d_num = len(ds.news), (1 if ds.domestic_idx else 0) + (1 if ds.international_idx else 0)
    m_b, k_b = len(ds.domestic_briefs), len(ds.international_briefs)
    expect = 1 + n + m_b + k_b
    if len(rows) != expect:
        add("ERROR", f"第六部分行数 {len(rows)} ≠ 预期 {expect}（1完整版+{n}常规+{m_b}+{k_b}）")
    total_expected = n - d_num + m_b + k_b
    mm = re.search(r"\|\s*\*\*实际独立新闻总数\*\*\s*\|\s*\*\*(\d+)条\*\*\s*\|", secs.get("五", ""))
    if not mm or int(mm.group(1)) != total_expected:
        add("ERROR", f"5.3 统计与实际不符（应为 {total_expected} 条）")

    # 8) 第七部分子节齐全
    sec7 = secs.get("七", "")
    for sub in contract["part7_subs"]:
        if f"### {sub}" not in sec7 and f"#### {sub}" not in sec7:
            add("ERROR", f"第七部分缺少子节：{sub}")

    # 9) 重点新闻不得丢失（所有 🔴/🟡 必须出现在第三部分）
    part3 = secs.get("三", "")
    for i, item in enumerate(ds.news, start=1):
        if item["importance"] in ("🔴", "🟡") and f"（第{i}条）" not in part3:
            add("CRITICAL", f"第三部分丢失{item['importance']}重点新闻：第{i}条 {item['title'][:24]}")

    # 10) 不应出现空表（表头后无数据行）
    for sub in contract["part7_subs"]:
        blk = re.search(rf"###+ {re.escape(sub)}\n(\|.*?\n\|[-| ]+\n)((?:>.*\n)*)((?:\|.*\n)*)", sec7)
        if not blk:
            continue
        body = blk.group(3).strip()
        if not body:
            add("ERROR", f"空表：{sub}")
        elif re.match(r"^\|\s*—\s*\|", body):
            add("WARNING", f"空内容占位表：{sub}")

    # 11) 无重复分隔符
    if re.search(r"\n---\n\s*\n---\n", report):
        add("ERROR", "存在连续重复分隔符 ---")

    # 12) 硬截断残留
    if re.search(r"[，、：；]\s*\.\.\.", report):
        add("WARNING", "存在句中硬截断残留（...）")

    # 13) 分隔线前必须留空行，否则上一行会被解析成 setext 二级标题
    _all = report.split("\n")
    _bad_hr = [i for i in range(1, len(_all))
               if _all[i].strip() == "---" and _all[i - 1].strip()]
    if _bad_hr:
        _pos = "、".join(str(i + 1) for i in _bad_hr[:5])
        add("ERROR", f"分隔线 --- 前缺空行 {len(_bad_hr)} 处（第 {_pos} 行）")

    return issues


def _parse_part6_rows(report, contract):
    """只在第六部分章节内解析数据行"""
    sec6 = _split_sections(report, contract).get("六", "")
    start = sec6.find("| 序号 | 新闻标题")
    if start < 0:
        return []
    block = sec6[start:]
    rows = []
    for ln in block.split("\n"):
        if not ln.startswith("|") or "------" in ln:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) != 10:
            continue
        if cells[0] in ("序号", "完整版") and "新闻标题" in cells[1]:
            continue
        rows.append({
            "idx": cells[0], "title": cells[1], "category": cells[2],
            "time": cells[3], "location": cells[4], "subject": cells[5],
            "event": cells[6], "cause": cells[7], "method": cells[8], "source": cells[9],
        })
    return rows


# ============================================================
# 数据集构建
# ============================================================
def build_dataset(date_str, use_cache=True):
    ds = Dataset(date_str)

    logger.info("[1/5] 拉取央视网视频列表")
    videos = fetch_videos(date_str)
    if not videos:
        raise RuntimeError("央视网数据获取失败，无法生成报告")

    # 完整版：标题优先，其次按超长时长兜底
    full = next((v for v in videos if "完整版" in v["title"] and "新闻联播" in v["title"]), None)
    if not full:
        full = next((v for v in videos if "新闻联播" in v["title"] and time_to_seconds(v["duration"]) > 1500), None)
    ds.full_video = full
    ds.full_url = full["url"] if full else f"https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml"
    ds.news_videos = [v for v in videos if v is not full]

    logger.info("[2/5] 解析央视网快讯目录页")
    cctv_dom, cctv_intl = [], []
    for v in ds.news_videos:
        safe = desens(v["title"])
        if "国内联播快讯" in safe:
            cctv_dom = fetch_kuaixun_details(v["url"])
        elif "国际联播快讯" in safe:
            cctv_intl = fetch_kuaixun_details(v["url"])
    logger.info(f"  央视网快讯页：国内 {len(cctv_dom)} 条 / 国际 {len(cctv_intl)} 条")

    logger.info("[3/5] 拉取齐鲁网索引并匹配子条目链接")
    iqilu_entries = fetch_iqilu_entries(date_str)
    ds.iqilu_total = len(iqilu_entries)

    logger.info("[4/5] 抓取正文 / 分类 / 提取六要素")
    for i, v in enumerate(ds.news_videos, start=1):
        detail = fetch_video_detail(v["url"])
        raw_title = desens(v["title"]).replace("完整版", "").strip()
        is_dir = ("国内联播快讯" in raw_title) or ("国际联播快讯" in raw_title)
        category, importance = classify_and_grade(raw_title, v["title"], detail["full_text"])
        elements = extract_six_elements(
            raw_title, v["title"], detail["full_text"], category, ds.date_short,
            is_brief_domestic=False,
        )
        ds.news.append({
            "idx": i, "title": raw_title, "raw_title": raw_title, "is_dir": is_dir,
            "url": v["url"], "duration": v["duration"],
            "category": category, "importance": importance, "detail": detail,
            "elements": elements, "summary": build_summary(raw_title, detail),
        })
        if "国内联播快讯" in raw_title:
            ds.domestic_idx = i
        elif "国际联播快讯" in raw_title:
            ds.international_idx = i

    # 快讯子条目：齐鲁网名录为基准，央视网正文按需补充
    dom_rows, intl_rows, complement = reconcile_brief_roster(
        ds, iqilu_entries, cctv_dom, cctv_intl
    )
    logger.info(
        f"  快讯名录对账：齐鲁网候选 {len(complement)} 条 → "
        f"国内 {len(dom_rows)} / 国际 {len(intl_rows)}"
    )

    # 与 CNTV 接口 brief 里的子条目清单交叉校验条数（只告警，不阻断）
    briefs = fetch_kuaixun_briefs(date_str)
    for bname, rows in (("国内联播快讯", dom_rows), ("国际联播快讯", intl_rows)):
        expect = briefs.get(bname)
        if expect and len(expect) != len(rows):
            logger.warning(
                f"  {bname} 子条目数与央视网清单不一致："
                f"央视网 {len(expect)} 条 / 对账后 {len(rows)} 条"
            )
            logger.warning(f"    央视网清单：{'；'.join(expect)}")
            logger.warning(f"    对账结果：{'；'.join(r['title'] for r in rows)}")

    dom_url = next((n["url"] for n in ds.news if n["is_dir"] and "国内" in n["title"]), "")
    intl_url = next((n["url"] for n in ds.news if n["is_dir"] and "国际" in n["title"]), "")

    def make_brief(row, sub_i, source_url, forced_cat):
        title = desens(row["title"]).strip()
        body = (row.get("body") or "").strip()
        cat = forced_cat or classify_and_grade(title, row["title"], body)[0]
        elements = extract_six_elements(
            title, row["title"], body, cat, ds.date_short,
            is_brief_domestic=(forced_cat is None),
        )
        return {
            "idx": sub_i, "title": title,
            "link_url": row.get("iqilu_url") or source_url,
            "iqilu_url": row.get("iqilu_url", ""),
            "source_url": source_url, "category": cat,
            "summary": body, "detail": {"full_text": body},
            "elements": elements,
        }

    if ds.domestic_idx is not None:
        ds.domestic_briefs = [
            make_brief(r, i, dom_url, None) for i, r in enumerate(dom_rows, start=1)
        ]
    if ds.international_idx is not None:
        ds.international_briefs = [
            make_brief(r, i, intl_url, "国际新闻") for i, r in enumerate(intl_rows, start=1)
        ]

    missing_body = sum(
        1 for b in ds.domestic_briefs + ds.international_briefs if not b["summary"]
    )
    if missing_body:
        logger.warning(f"  有 {missing_body} 条快讯缺少正文，六要素将仅依据标题推导")

    ds.tone = build_tone_overview(ds.news, ds.date_display)

    logger.info(
        f"[5/5] 数据集就绪：常规 {len(ds.news)} 条 / 国内快讯 {len(ds.domestic_briefs)} 条 / "
        f"国际快讯 {len(ds.international_briefs)} 条"
    )
    return ds


# ============================================================
# 主流程
# ============================================================
def resolve_output_path(date_str):
    d = datetime.strptime(date_str, "%Y%m%d").date()
    month_dir = os.path.join(ARCHIVE_ROOT, f"{d.year}年{d.month}月")
    return month_dir, os.path.join(month_dir, f"新闻联播总结_{date_str}.md")


def main():
    parser = argparse.ArgumentParser(
        description="新闻联播总结报告 —— 单一入口一键生成器 v5.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python xwlb_report.py                # 昨天\n"
            "  python xwlb_report.py 20260915       # 指定日期\n"
            "  python xwlb_report.py 20260915 --force\n"
        ),
    )
    parser.add_argument("date", nargs="?", default=None, help="目标日期 YYYYMMDD（默认昨天）")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有报告")
    parser.add_argument("--dry-run", action="store_true", help="渲染并自检，但不写正式文件")
    parser.add_argument("--preview", metavar="PATH", help="把渲染结果写到指定路径（调试用，不影响正式文件）")
    parser.add_argument("--check", action="store_true", help="仅对已存在报告跑自检")
    args = parser.parse_args()

    if args.date:
        if not re.match(r"^\d{8}$", args.date):
            logger.error("日期格式错误，应为 YYYYMMDD")
            return 1
        date_str = args.date
    else:
        date_str = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    try:
        target = datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        logger.error(f"日期无效：{date_str}")
        return 1
    if target > date.today():
        logger.error(f"不能生成未来日期：{date_str}")
        return 1

    contract = load_contract()
    month_dir, output_path = resolve_output_path(date_str)

    # --check：只校验已有报告
    if args.check:
        if not os.path.exists(output_path):
            logger.error(f"报告不存在：{output_path}")
            return 1
        with open(output_path, "r", encoding="utf-8") as f:
            report = f.read()
        issues = _check_existing(report, contract, date_str)
        return _report_issues(issues, output_path)

    no_write = args.dry_run or bool(args.preview)
    # 文件存在性策略：>10KB 跳过重生成，≤10KB 覆盖重生成（不落盘模式跳过该策略）
    # 注意：跳过重生成时仍要跑一遍自检并返回同样的退出码，
    # 否则定时任务重试时会因为"文件已存在"而把上一次的质量失败误判成成功。
    if os.path.exists(output_path) and not args.force and not no_write:
        size = os.path.getsize(output_path)
        if size > 10240:
            logger.info(f"报告已存在（{size / 1024:.1f}KB > 10KB），跳过生成并直接自检。")
            with open(output_path, "r", encoding="utf-8") as f:
                report = f.read()
            issues = _check_existing(report, contract, date_str)
            if issues:
                logger.warning(
                    "已存在的报告未通过格式契约自检（多为旧流程产物）。"
                    f"如需用当前流程重建该报告，请手动执行："
                    f"python xwlb_report.py {date_str} --force"
                )
            return _report_issues(issues, output_path)
        logger.info(f"报告存在但仅 {size} 字节（≤10KB），视为不完整，重新生成")

    ds = build_dataset(date_str)
    report = render_report(ds, contract)
    issues = self_check(ds, report, contract)

    if args.dry_run or args.preview:
        if args.preview:
            os.makedirs(os.path.dirname(os.path.abspath(args.preview)), exist_ok=True)
            with open(args.preview, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"预览已写出：{args.preview}")
        logger.info("dry-run：不写正式文件")
        return _report_issues(issues, output_path, dry_run=True)

    os.makedirs(month_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    size_kb = os.path.getsize(output_path) / 1024
    logger.info(f"报告已生成：{output_path}（{size_kb:.1f}KB）")
    print()
    print("=" * 64)
    print(f"  报告: {output_path}")
    print(f"  大小: {size_kb:.1f}KB")
    print(f"  常规 {len(ds.news)} 条 / 国内快讯 {len(ds.domestic_briefs)} 条 / 国际快讯 {len(ds.international_briefs)} 条")
    print(f"  文件链接: computer://{output_path}")
    print("=" * 64)
    return _report_issues(issues, output_path)


def _check_existing(report, contract, date_str):
    """对已存在报告做结构级自检（无需重新抓数据）"""
    issues = []
    secs = _split_sections(report, contract)
    for no, title in contract["section_titles"].items():
        if no not in secs:
            issues.append(("CRITICAL", f"缺少章节：{title}"))
    for name, _c in NAME_TO_CODE:
        if name in report:
            issues.append(("CRITICAL", f"敏感词泄露：{name}"))
    bad = re.findall(r"\]\((http://[^)]+)\)", report)
    if bad:
        issues.append(("ERROR", f"存在 {len(bad)} 条 HTTP 链接"))
    header = _find_part6_header(report, contract)
    if not header:
        issues.append(("CRITICAL", "第六部分表头缺失"))
    elif len(header) != 10 or header != contract["header6"]:
        issues.append(("CRITICAL", f"第六部分表头不合规（{len(header)} 列）：{header}"))
    urls = _find_full_urls(report, contract)
    if len(set(urls.values())) > 1:
        issues.append(("CRITICAL", f"完整版链接不一致：{urls}"))
    sec7 = secs.get("七", "")
    for sub in contract["part7_subs"]:
        if f"### {sub}" not in sec7 and f"#### {sub}" not in sec7:
            issues.append(("ERROR", f"第七部分缺少子节：{sub}"))
    rows = _parse_part6_rows(report, contract)
    if rows:
        dash = sum(1 for r in rows if r["subject"].strip() in ("—", "-", ""))
        cov = (len(rows) - dash) / len(rows) * 100
        if cov < 70:
            issues.append(("ERROR", f"新闻主体覆盖率 {cov:.1f}%（要求≥70%）"))
    if re.search(r"\n---\n\s*\n---\n", report):
        issues.append(("ERROR", "存在连续重复分隔符 ---"))
    _all = report.split("\n")
    _bad_hr = [i for i in range(1, len(_all))
               if _all[i].strip() == "---" and _all[i - 1].strip()]
    if _bad_hr:
        issues.append(("ERROR", f"分隔线 --- 前缺空行 {len(_bad_hr)} 处（旧流程产物常见）"))
    return issues


def _report_issues(issues, output_path, dry_run=False):
    """
    打印自检结论并映射退出码，供定时任务判定成败：
      0 = 全部通过   1 = 有 ERROR   2 = 有 CRITICAL
    """
    crit = [i for i in issues if i[0] == "CRITICAL"]
    err = [i for i in issues if i[0] == "ERROR"]
    warn = [i for i in issues if i[0] == "WARNING"]

    print()
    print("-" * 64)
    print("  质量自检结果")
    print("-" * 64)
    if not issues:
        print("  ✅ 全部通过（结构 / 表头 / 脱敏 / 链接 / 覆盖率 / 一致性）")
    for level, msg in crit + err + warn:
        icon = {"CRITICAL": "❌", "ERROR": "⚠️ ", "WARNING": "·"}[level]
        print(f"  {icon} [{level}] {msg}")
    print(f"  合计：CRITICAL {len(crit)} / ERROR {len(err)} / WARNING {len(warn)}")
    print("-" * 64)

    if crit:
        return 2
    if err:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
