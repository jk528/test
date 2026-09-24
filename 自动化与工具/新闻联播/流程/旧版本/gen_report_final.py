#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻联播总结报告生成脚本（分阶段模式 v4.0）

设计理念：
  Phase 1: 脚本生成1-5部分 + 输出六要素JSON数据源（含正文摘要供AI参考）
  Phase 2: AI根据JSON数据源一次性填写六要素 → 保存为JSON文件
  Phase 3: 脚本读取AI填写的JSON → 一次性生成第六七部分 → 拼接完整报告

用法：
  python gen_report_final.py 20260907              # Phase 1: 生成1-5部分+数据源
  python gen_report_final.py 20260907 --merge       # Phase 3: 合并AI数据+生成六七部分

版本：v4.0.0（2026-09-08）
基于 gen_report_v2.py v2.1.0
"""

import sys
import os
import re
import json
import logging
import argparse
from datetime import datetime, date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
TEMP_DIR = os.path.join(
    os.environ.get("TEMP", os.environ.get("TMP", "/tmp")), "xwlb_cache"
)
os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(TEMP_DIR, "gen_report_final.log"), encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

sys.path.insert(0, SCRIPT_DIR)

import gen_report_v2 as gv2
from fetch_xwlb import desensitize


# ============================================================
# Phase 1: 生成1-5部分 + 六要素数据源JSON
# ============================================================
def phase1_generate(date_str):
    """生成1-5部分报告 + 六要素数据源JSON"""

    # 步骤1: 央视网视频列表
    logger.info("[1/4] 获取央视网视频列表...")
    videos = gv2.fetch_xwlb_videos(date_str)
    if not videos:
        logger.error("央视网数据获取失败")
        sys.exit(1)

    # 步骤2: 快讯详情
    logger.info("[2/4] 提取快讯子条目详情...")
    domestic_briefs = []
    international_briefs = []
    for v in videos:
        safe_title = desensitize(v["title"])
        if "国内联播快讯" in safe_title:
            domestic_briefs = gv2.fetch_kuaixun_details(v["url"])
            logger.info(f"  国内快讯: {len(domestic_briefs)} 条")
        elif "国际联播快讯" in safe_title:
            international_briefs = gv2.fetch_kuaixun_details(v["url"])
            logger.info(f"  国际快讯: {len(international_briefs)} 条")

    # 步骤3: 齐鲁网数据
    logger.info("[3/4] 获取齐鲁网快讯条目...")
    iqilu_entries = gv2.fetch_iqilu_entries(date_str)

    # 分离完整版和常规新闻
    full_videos = [
        v
        for v in videos
        if "完整版" in v.get("title", "") and "新闻联播" in v.get("title", "")
    ]
    normal_videos = [v for v in videos if v not in full_videos]

    # 为每条新闻提取详情、分类
    logger.info("  正在提取新闻详情并分类...")
    for v in normal_videos:
        v["detail"] = gv2.fetch_video_detail(v["url"])
        cat, imp = gv2.classify_news(v["title"], v["detail"]["full_text"])
        v["category"] = cat
        v["importance"] = imp

    # 为快讯匹配齐鲁网URL
    logger.info("  正在匹配齐鲁网快讯链接...")
    domestic_idx = None
    international_idx = None
    for i, v in enumerate(normal_videos):
        safe_title = desensitize(v["title"])
        if "国内联播快讯" in safe_title:
            domestic_idx = i + 1
            for item in domestic_briefs:
                item["iqilu_url"] = gv2.match_iqilu_url(item["title"], iqilu_entries)
        elif "国际联播快讯" in safe_title:
            international_idx = i + 1
            for item in international_briefs:
                item["iqilu_url"] = gv2.match_iqilu_url(item["title"], iqilu_entries)

    # 抓取快讯正文详情
    logger.info("  正在抓取快讯正文详情...")
    for item in domestic_briefs + international_briefs:
        if item.get("iqilu_url"):
            item["detail"] = gv2.fetch_iqilu_detail(item["iqilu_url"])
        else:
            item["detail"] = {"full_text": ""}

    # 步骤4: 生成1-5部分
    logger.info("[4/4] 生成报告1-5部分 + 六要素数据源...")

    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    date_display = (
        f"{target_date.year}年{target_date.month:02d}月{target_date.day:02d}日"
    )

    # 用猴子补丁让 generate_report 在第六部分处停止
    # 方法：替换 extract_six_elements 使其返回占位符，
    #   然后我们从生成的完整报告中截取1-5部分
    original_extract = gv2.extract_six_elements

    # 临时用占位符生成完整报告，然后截取1-5部分
    def _placeholder_extract(video, detail, date_display):
        date_short = f"{date_display[:4]}-{date_display[5:7]}-{date_display[8:10]}"
        return {
            "time": date_short,
            "location": "PLACEHOLDER",
            "subject": "PLACEHOLDER",
            "event": "PLACEHOLDER",
            "cause": "PLACEHOLDER",
            "method": "PLACEHOLDER",
        }

    gv2.extract_six_elements = _placeholder_extract

    output_path, _ = gv2.generate_report(
        date_str, videos, domestic_briefs, international_briefs, iqilu_entries
    )

    # 恢复原始函数
    gv2.extract_six_elements = original_extract

    # 截取1-5部分（到"## 六"之前）
    with open(output_path, "r", encoding="utf-8") as f:
        full_content = f.read()

    part6_marker = "## 六、新闻六要素索引"
    part1to5 = full_content.split(part6_marker)[0]

    # 保存1-5部分
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(part1to5)

    # 生成六要素数据源JSON
    datasource = build_datasource(
        date_str,
        date_display,
        normal_videos,
        domestic_briefs,
        international_briefs,
        domestic_idx,
        international_idx,
    )

    json_path = os.path.join(
        os.path.dirname(output_path), f"六要素数据源_{date_str}.json"
    )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(datasource, f, ensure_ascii=False, indent=2)

    logger.info(f"1-5部分已生成: {output_path}")
    logger.info(f"六要素数据源已生成: {json_path}")

    # 输出AI填写指引
    print(f"\n{'='*60}")
    print("Phase 1 完成！")
    print(f"{'='*60}")
    print(f"报告1-5部分: {output_path}")
    print(f"六要素数据源: {json_path}")
    print(f"{'='*60}")
    print("下一步：")
    print(f"  1. 读取JSON数据源中的 news_items")
    print(f"  2. 根据每条的 title/url/summary/full_text 填写六要素")
    print(f"     (location/subject/event/cause/method)")
    print(f"  3. 将填写结果保存为: {os.path.join(os.path.dirname(output_path), f'六要素结果_{date_str}.json')}")
    print(f"  4. 运行: python gen_report_final.py {date_str} --merge")
    print(f"{'='*60}")

    return output_path, json_path


def build_datasource(
    date_str,
    date_display,
    normal_videos,
    domestic_briefs,
    international_briefs,
    domestic_idx,
    international_idx,
):
    """构建六要素数据源JSON"""
    items = []

    # 完整版
    full_videos = [
        v
        for v in normal_videos
        if "完整版" in v.get("title", "") and "新闻联播" in v.get("title", "")
    ]
    full_url = ""
    for v in normal_videos:
        if "完整版" in v.get("title", "") and "新闻联播" in v.get("title", ""):
            full_url = v["url"]
            break
    if not full_url and len(normal_videos) > 0:
        full_url = normal_videos[0]["url"]

    items.append(
        {
            "idx": "完整版",
            "title": f"完整版《新闻联播》{date_display}",
            "url": full_url,
            "category": "完整版",
            "is_placeholder": True,
            "elements": {
                "location": "全国",
                "subject": "—",
                "event": "当日全部新闻汇总",
                "cause": "—",
                "method": "完整播报",
            },
        }
    )

    # 常规新闻
    for i, v in enumerate(normal_videos):
        idx = i + 1
        safe_title = desensitize(v["title"]).replace("完整版", "")
        detail = v.get("detail", {})
        full_text = detail.get("full_text", "") if isinstance(detail, dict) else ""
        first_para = (
            detail.get("first_paragraph", "") if isinstance(detail, dict) else ""
        )
        summary_text = first_para or full_text

        items.append(
            {
                "idx": str(idx),
                "title": safe_title,
                "url": v.get("url", ""),
                "category": v.get("category", "其他"),
                "importance": v.get("importance", "一般"),
                "summary": summary_text[:300] if summary_text else "",
                "full_text": full_text[:500] if full_text else "",
                "is_placeholder": False,
                "elements": None,  # 待AI填写
            }
        )

    # 国内快讯子条目
    if domestic_idx and domestic_briefs:
        domestic_url = ""
        for v in normal_videos:
            if "国内联播快讯" in desensitize(v["title"]):
                domestic_url = v["url"]
                break
        for i, item in enumerate(domestic_briefs):
            sub_idx = f"{domestic_idx}-{i+1}"
            safe_title = desensitize(item["title"])
            detail = item.get("detail", {})
            full_text = (
                detail.get("full_text", "") if isinstance(detail, dict) else ""
            )
            items.append(
                {
                    "idx": sub_idx,
                    "title": safe_title,
                    "url": item.get("iqilu_url") or domestic_url,
                    "category": _classify_brief(safe_title),
                    "importance": "一般",
                    "summary": item.get("summary", "")[:300] if item.get("summary") else "",
                    "full_text": full_text[:500] if full_text else "",
                    "source_url": domestic_url,
                    "is_placeholder": False,
                    "elements": None,
                }
            )

    # 国际快讯子条目
    if international_idx and international_briefs:
        international_url = ""
        for v in normal_videos:
            if "国际联播快讯" in desensitize(v["title"]):
                international_url = v["url"]
                break
        for i, item in enumerate(international_briefs):
            sub_idx = f"{international_idx}-{i+1}"
            safe_title = desensitize(item["title"])
            detail = item.get("detail", {})
            full_text = (
                detail.get("full_text", "") if isinstance(detail, dict) else ""
            )
            items.append(
                {
                    "idx": sub_idx,
                    "title": safe_title,
                    "url": item.get("iqilu_url") or international_url,
                    "category": "国际新闻",
                    "importance": "一般",
                    "summary": item.get("summary", "")[:300] if item.get("summary") else "",
                    "full_text": full_text[:500] if full_text else "",
                    "source_url": international_url,
                    "is_placeholder": False,
                    "elements": None,
                }
            )

    return {
        "date": date_str,
        "date_display": date_display,
        "total_items": len(items),
        "ai_items": sum(1 for it in items if not it["is_placeholder"]),
        "instructions": (
            "请根据每条的 title/url/summary/full_text 填写 elements 中的 "
            "location/subject/event/cause/method 五个字段。"
            "规则：人物用<u>占位符</u>（如<u>国家主席</u>），"
            "机构名不加下划线（如农业农村部），"
            "事件核心对象不加下划线（如也门冲突双方）。"
            "无明确值填—。快讯目录行（idx为纯数字且title含'联播快讯'）"
            "填 location=—, subject=—, event=播报XX联播快讯, cause=—, method=目录播报。"
        ),
        "news_items": items,
    }


def _classify_brief(title):
    """快讯分类"""
    if any(kw in title for kw in ["经济", "产业", "金融", "外汇", "贸易", "企业", "消费", "粮食", "物流", "国债", "储备"]):
        return "经济要闻"
    elif any(kw in title for kw in ["教育", "文化", "体育", "旅游"]):
        return "社会/文化要闻"
    elif any(kw in title for kw in ["政法", "法院", "检察", "公安", "司法"]):
        return "政策/会议"
    elif any(kw in title for kw in ["拨付", "救灾", "应急", "天气", "降温", "高温"]):
        return "社会/文化要闻"
    else:
        return "社会/文化要闻"


# ============================================================
# Phase 3: 读取AI JSON → 生成第六七部分 → 拼接完整报告
# ============================================================
def phase3_merge(date_str):
    """读取AI填写的六要素JSON，生成第六七部分，拼接完整报告"""

    # 计算路径
    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    year_month = f"{target_date.year}年{target_date.month}月"
    archive_dir = os.path.join(BASE_DIR, "归档", year_month)
    report_path = os.path.join(archive_dir, f"新闻联播总结_{date_str}.md")
    result_json_path = os.path.join(archive_dir, f"六要素结果_{date_str}.json")
    datasource_json_path = os.path.join(archive_dir, f"六要素数据源_{date_str}.json")

    if not os.path.exists(report_path):
        logger.error(f"报告1-5部分不存在: {report_path}")
        logger.error("请先运行 Phase 1")
        sys.exit(1)

    if not os.path.exists(result_json_path):
        logger.error(f"六要素结果JSON不存在: {result_json_path}")
        logger.error("请先让AI填写六要素并保存结果")
        sys.exit(1)

    # 读取AI结果
    with open(result_json_path, "r", encoding="utf-8") as f:
        ai_result = json.load(f)

    # 读取1-5部分
    with open(report_path, "r", encoding="utf-8") as f:
        part1to5 = f.read()

    # 生成第六七部分
    date_display = ai_result.get("date_display", "")
    items = ai_result.get("news_items", [])

    part67 = generate_part67(items, date_display, date_str)

    # 拼接完整报告
    full_report = part1to5 + part67

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    # 清理临时JSON
    for tmp in [result_json_path, datasource_json_path]:
        if os.path.exists(tmp):
            os.remove(tmp)

    file_size = os.path.getsize(report_path) / 1024
    logger.info(f"完整报告已生成: {report_path}（{file_size:.1f}KB）")

    print(f"\n{'='*60}")
    print("Phase 3 完成！完整报告已生成。")
    print(f"{'='*60}")
    print(f"报告路径: {report_path}")
    print(f"文件大小: {file_size:.1f}KB")
    print(f"六要素条目: {len(items)} 条")
    print(f"临时JSON已清理")
    print(f"{'='*60}")

    return report_path


def generate_part67(items, date_display, date_str):
    """生成第六七部分"""
    lines = []

    def L(s):
        lines.append(s)

    # --- 第六部分 ---
    L("---")
    L("")
    L("## 六、新闻六要素索引")
    L("")
    L(
        '> 完整版单独列出，不纳入常规新闻编号。常规新闻按当天央视网实际分条顺序编号，'
        '快讯子条目使用"序号-子序号"编号（如9-1、9-2）。'
    )
    L(
        '> 新闻主体列填写每条新闻的核心行动者：人物使用占位符（如"国家领导人"），'
        '不出现具体人名；无人物主体时填写机构名称或事件核心对象。'
    )
    L(
        '> **脱敏标记规则**：所有由人名替换而来的占位符，均使用HTML下划线标记，'
        '格式为 `<u>占位符</u>`。机构名称、事件核心对象等非人名替换内容不加下划线。'
    )
    L("")
    L("| 序号 | 新闻标题（可点击跳转） | 类别 | 时间 | 地点 | 新闻主体 | 事件 | 原因 | 方式 | 详细信息源链接 |")
    L("|------|---------|------|------|------|------|------|------|------|------|")

    # 收集所有人物占位符和机构（用于第七部分）
    person_placeholders = {}  # position -> [positions_found]
    institutions = {}  # abbr -> full_name
    event_objects = {}  # name -> (desc, pos)
    data_items = []  # (value, desc)
    data_set = set()

    for item in items:
        idx = item["idx"]
        title = item["title"]
        url = item["url"]
        category = item["category"]
        elements = item.get("elements") or {}

        time_val = elements.get("time", date_display[:4] + "-" + date_display[5:7] + "-" + date_display[8:10])
        location = elements.get("location", "—")
        subject = elements.get("subject", "—")
        event = elements.get("event", "—")
        cause = elements.get("cause", "—")
        method = elements.get("method", "—")

        # 详细信息源链接
        if item.get("is_placeholder"):
            source_url = url
            source_label = "央视网"
        elif "-" in idx:  # 快讯子条目
            source_url = item.get("source_url", url)
            source_label = "央视网"
        else:
            source_url = url
            source_label = "央视网"

        L(f"| {idx} | [{title}]({url}) | {category} | {time_val} | {location} | {subject} | {event} | {cause} | {method} | [{source_label}]({source_url}) |")

        # 收集第七部分数据
        # 人物占位符
        person_match = re.findall(r"<u>(.+?)</u>", subject)
        for pos in person_match:
            if pos not in person_placeholders:
                person_placeholders[pos] = []
            person_placeholders[pos].append(idx)

        # 机构类（不加下划线的主体）
        if not person_match and subject != "—" and "冲突双方" not in subject and "航线" not in subject and "货机" not in subject and "火山" not in subject and "产油国" not in subject and "服贸会" not in subject and "建设方" not in subject:
            if subject not in institutions:
                institutions[subject] = "快讯" if "-" in idx else f"第{idx}条"

        # 事件核心对象
        if "冲突双方" in subject or "火山" in subject or "产油国" in subject or "航线" in subject or "货机" in subject:
            if subject not in event_objects:
                event_objects[subject] = (title[:20], "国际快讯" if "-" in idx else f"第{idx}条")

        # 数据占位符
        text_to_scan = title + " " + item.get("summary", "") + " " + item.get("full_text", "")
        for pat in [r"(\d+亿元)", r"(\d+亿美元)", r"(\d+\.?\d*公里)", r"(\d+万吨)"]:
            for m in re.finditer(pat, text_to_scan):
                d = m.group(1)
                if d not in data_set:
                    data_set.add(d)
                    data_items.append((d, title[:15]))
                if len(data_items) >= 5:
                    break
            if len(data_items) >= 5:
                break

    L("")
    L(
        '> **编号规则**：常规新闻按央视网分条编号，'
        '快讯子条目为N-M格式，标题链接对应各来源页面。'
    )
    L("")
    L("---")
    L("")

    # --- 第七部分 ---
    L("## 七、占位符统合信息")
    L("")
    L("### 7.1 新闻主体占位符")
    L("")
    L("#### 7.1.1 人物类")
    L("| 序号 | 占位符 | 职务/身份 | 出现位置 |")
    L("|------|--------|----------|---------|")
    position_order = [
        "国家主席", "国务院总理", "全国人大常委会委员长", "全国政协主席",
        "国家副主席", "中共中央政治局常委", "国务院副总理", "中央纪委书记",
    ]
    sorted_persons = sorted(
        person_placeholders.keys(),
        key=lambda x: position_order.index(x) if x in position_order else 99,
    )
    for i, pos in enumerate(sorted_persons):
        positions = person_placeholders[pos]
        L(f"| {i+1} | <u>{pos}</u> | {pos} | 第{'、'.join(positions)}条 |")
    L("")

    L("#### 7.1.2 机构类")
    L("| 序号 | 占位符 | 机构全称 | 出现位置 |")
    L("|------|--------|---------|---------|")
    inst_full_names = {
        "财政部": "中华人民共和国财政部",
        "最高人民法院": "中华人民共和国最高人民法院",
        "国家外汇管理局": "国家外汇管理局",
        "中央宣传部": "中共中央宣传部",
        "教育部": "中华人民共和国教育部",
        "应急管理部": "中华人民共和国应急管理部",
        "海关总署": "中华人民共和国海关总署",
        "金融监管总局": "国家金融监督管理总局",
        "农业农村部": "中华人民共和国农业农村部",
        "工业和信息化部": "中华人民共和国工业和信息化部",
        "商务部": "中华人民共和国商务部",
        "国家发展改革委": "中华人民共和国国家发展和改革委员会",
        "中国人民银行": "中国人民银行",
        "中国证监会": "中国证券监督管理委员会",
        "广西壮族自治区人民政府": "广西壮族自治区人民政府",
        "国家外汇管理局": "国家外汇管理局",
        "中央气象台": "中央气象台",
    }
    for i, (abbr, pos) in enumerate(institutions.items()):
        full_name = inst_full_names.get(abbr, abbr)
        L(f"| {i+1} | {abbr} | {full_name} | {pos} |")
    L("")

    L("#### 7.1.3 事件核心对象类")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    for i, (name, (desc, pos)) in enumerate(event_objects.items()):
        L(f"| {i+1} | {name} | {desc} | {pos} |")
    L("")

    L("### 7.2 时间占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    L(f"| 1 | {date_display} | 新闻播出日期 | 全文 |")
    L("")

    L("### 7.3 地点占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    # 从六要素中收集地点
    locations_seen = set()
    for item in items:
        elements = item.get("elements") or {}
        loc = elements.get("location", "—")
        if loc != "—" and loc not in locations_seen:
            locations_seen.add(loc)
    if "北京" in locations_seen:
        L("| 1 | 北京 | 首都/政治中心 | 领导人活动报道 |")
    if "全国" in locations_seen or "全国各地" in locations_seen:
        L(f"| {'1' if '北京' not in locations_seen else '2'} | 全国各地 | 新闻涉及地域 | 国内新闻 |")
    L("")

    L("### 7.4 数据占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    for i, (d, desc) in enumerate(data_items):
        L(f"| {i+1} | {d} | {desc} | 快讯/正文中 |")
    L("")

    L("---")
    L("")
    L("> **数据来源**：")
    L(f"> - 央视新闻联播（{date_display}）：[央视网新闻联播列表页](https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml)")
    L("> - 央视网：[tv.cctv.com](https://tv.cctv.com/)")
    L("> - 齐鲁网：[v.iqilu.com](https://v.iqilu.com/)")
    L("> **声明**：本报告基于公开新闻信息整理，仅供参考。播放时间节点为推算值，实际可能有±10秒误差。")
    L("")

    return "\n".join(lines)


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="新闻联播总结报告生成（分阶段模式：脚本1-5 + AI六要素 + 脚本6-7）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "使用示例：\n"
            "  python gen_report_final.py 20260907          # Phase 1: 生成1-5部分+数据源\n"
            "  # AI读取数据源JSON → 填写六要素 → 保存结果JSON\n"
            "  python gen_report_final.py 20260907 --merge  # Phase 3: 合并生成完整报告\n"
        ),
    )
    parser.add_argument("date", nargs="?", default=None, help="目标日期 YYYYMMDD")
    parser.add_argument("--merge", action="store_true", help="Phase 3: 合并AI数据生成完整报告")
    parser.add_argument("--force", action="store_true", help="强制重新生成")
    args = parser.parse_args()

    if args.date:
        if not re.match(r"^\d{8}$", args.date):
            logger.error("日期格式错误，应为 YYYYMMDD")
            sys.exit(1)
        date_str = args.date
    else:
        yesterday = date.today() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

    if args.merge:
        phase3_merge(date_str)
    else:
        # 计算输出路径
        target_date = datetime.strptime(date_str, "%Y%m%d").date()
        year_month = f"{target_date.year}年{target_date.month}月"
        archive_dir = os.path.join(BASE_DIR, "归档", year_month)
        report_path = os.path.join(archive_dir, f"新闻联播总结_{date_str}.md")

        if args.force and os.path.exists(report_path):
            os.remove(report_path)
            logger.info(f"已删除旧文件")

        phase1_generate(date_str)


if __name__ == "__main__":
    main()
