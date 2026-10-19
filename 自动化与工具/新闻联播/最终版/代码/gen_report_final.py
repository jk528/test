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
# 智能定位项目根：向上查找含"归档"子目录的祖先，兼容不同部署层级
# 原 分阶段生成方案/ 向上2层=项目根；本 最新版本/代码/ 向上3层=项目根
def _find_base_dir(start):
    d = start
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "归档")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.dirname(os.path.dirname(start)))
BASE_DIR = _find_base_dir(SCRIPT_DIR)
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

        # 快讯目录行（纯"国内/国际联播快讯"）：预填固定要素，AI 无需精读
        # （第六部分渲染时会跳过目录行；父目录行仅保留在第二、五部分）
        if "联播快讯" in safe_title:
            items.append(
                {
                    "idx": str(idx),
                    "title": safe_title,
                    "url": v.get("url", ""),
                    "category": "快讯目录",
                    "importance": "一般",
                    "summary": summary_text[:300] if summary_text else "",
                    "full_text": full_text[:500] if full_text else "",
                    "is_placeholder": True,
                    "elements": {
                        "time": "",
                        "location": "—",
                        "subject": "—",
                        "event": f"播报{safe_title}",
                        "cause": "—",
                        "method": "目录播报",
                    },
                }
            )
            continue

        items.append(
            {
                "idx": str(idx),
                "title": safe_title,
                "url": v.get("url", ""),
                "category": v.get("category", "其他"),
                "importance": v.get("importance", "一般"),
                "summary": summary_text[:300] if summary_text else "",
                "full_text": full_text[:1200] if full_text else "",
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
            # 优先用央视网完整正文（fetch_kuaixun_details 的 full_text）
            # 齐鲁网 detail.full_text 已知会返回 JS 脚本（坑6），仅作兑底
            full_text = item.get("full_text") or ""
            if (
                (not full_text or "设为首页" in full_text)
                and isinstance(item.get("detail"), dict)
            ):
                full_text = item["detail"].get("full_text", "")
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
            # 优先用央视网完整正文（fetch_kuaixun_details 的 full_text）
            # 齐鲁网 detail.full_text 已知会返回 JS 脚本（坑6），仅作兑底
            full_text = item.get("full_text") or ""
            if (
                (not full_text or "设为首页" in full_text)
                and isinstance(item.get("detail"), dict)
            ):
                full_text = item["detail"].get("full_text", "")
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

    # 指令与脱敏模式联动（不脱敏版：人物直接写职务+姓名）
    if os.environ.get("XWLB_NO_DESENSITIZE"):
        instructions = (
            "不脱敏版。请根据每条 title/url/summary/full_text 填写 elements 中的 "
            "location/subject/event/cause/method 五个字段（仅 elements 为 null 的行需要填）。"
            "规则：人物主体直接写'职务+姓名'（如'联合国秘书长古特雷斯'），不加<u>标签；"
            "机构名写全称（如国务院安全生产委员会办公室）；"
            "事件核心对象写明文（如也门冲突双方）。"
            "地点尽量精确到城市。无明确值填—，禁止大量填—（占比≤30%）。"
            "is_placeholder=true 的行（完整版、快讯目录行）已预填，原样保留。"
        )
    else:
        instructions = (
            "请根据每条的 title/url/summary/full_text 填写 elements 中的 "
            "location/subject/event/cause/method 五个字段（仅 elements 为 null 的行需要填）。"
            "规则：人物用<u>占位符</u>（如<u>国家主席</u>），"
            "机构名不加下划线（如农业农村部），"
            "事件核心对象不加下划线（如也门冲突双方）。"
            "无明确值填—。is_placeholder=true 的行（完整版、快讯目录行）已预填，原样保留。"
        )

    return {
        "date": date_str,
        "date_display": date_display,
        "total_items": len(items),
        "ai_items": sum(1 for it in items if not it["is_placeholder"]),
        "instructions": instructions,
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

    # 生成第六七部分
    date_display = ai_result.get("date_display", "")
    items = ai_result.get("news_items", [])

    # 精简格式支持（优化1）：AI 可只提交 idx + elements（+可选 category 修正），
    # 基础字段（title/url/summary/full_text/source_url/is_placeholder）自动从数据源补齐；
    # 预填行（完整版、快讯目录行）可省略，未出现的行也从数据源自动补回
    if items and os.path.exists(datasource_json_path):
        need_enrich = any(
            not it.get("title") for it in items if not it.get("is_placeholder")
        ) or any(
            it.get("idx") and not it.get("title") for it in items
        )
        missing_prefill = False
        with open(datasource_json_path, "r", encoding="utf-8") as f:
            ds = json.load(f)
        ds_map = {it["idx"]: it for it in ds.get("news_items", [])}
        if need_enrich:
            enriched = []
            for it in items:
                base = dict(ds_map.get(it.get("idx"), {}))
                base.update(it)  # AI 提供的字段优先（elements/category 等）
                enriched.append(base)
            items = enriched
        # 补回结果中省略的预填行（如完整版、快讯目录行）
        seen_idx = {it.get("idx") for it in items}
        for it in ds.get("news_items", []):
            if it.get("idx") not in seen_idx:
                items.append(dict(it))
                missing_prefill = True
        if need_enrich or missing_prefill:
            logger.info(
                f"结果JSON为精简格式：已从数据源补齐基础字段与预填行"
            )

    # 读取1-5部分
    with open(report_path, "r", encoding="utf-8") as f:
        part1to5 = f.read()

    # 拼接前清理中间件尾部：
    #   a) 平台水印行：hook 会对 .md 写入自动追加 "> AI生成"，中间件被追加水印后
    #      直接拼接会把它嵌入正文中部；最终报告写入后 hook 会在文末重新追加，
    #      交付物上的水印仍然保留，此处只剔除中间件尾部的残留行
    #   b) 与第六部分开头重复的 --- 分隔线（generate_part67 自带 --- 开头）
    lines15 = part1to5.rstrip("\r\n \t").split("\n")
    while lines15 and re.fullmatch(r"[ \t]*>[ \t]*AI[ \t]*生成[ \t]*", lines15[-1]):
        lines15.pop()
    cleaned15 = "\n".join(lines15).rstrip("\r\n \t")
    if cleaned15.endswith("---"):
        cleaned15 = cleaned15[:-3].rstrip("\r\n \t")
    part1to5 = cleaned15 + "\n\n"

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
    """生成第六七部分（v2.0.0 高质量渲染）

    v2.0.0 重大优化（优化积分建议 优化1）：
    - 数据占位符：23 种正则，不限数量（旧版仅 4 种限 5 条）
    - 地点占位符：从六要素提取全部（旧版仅北京/全国）
    - 机构全称：40+ 映射 + 兜底标注（旧版 17 个）
    - 事件核心对象：分类逻辑（旧版 5 个硬编码关键词）
    - 新增 7.5 内容占位符：扫描《...》书名/文件名
    - 不脱敏版支持：人物直接列姓名+职务
    - 空表兜底：无数据时显示"本日无XXX"
    """
    no_desensitize = bool(os.environ.get("XWLB_NO_DESENSITIZE"))

    lines = []
    def L(s):
        lines.append(s)

    date_short = f"{date_display[:4]}-{date_display[5:7]}-{date_display[8:10]}"

    # 人名映射表（不脱敏版用于拆分姓名和职务）
    name_to_title = {}
    try:
        from fetch_xwlb import NAME_TO_CODE, CODE_TO_POSITION
        for name_unicode, code in NAME_TO_CODE:
            title = CODE_TO_POSITION.get(code, "")
            if title:
                name_to_title[name_unicode] = title
    except Exception:
        pass

    # 机构全称映射表（扩充版）
    inst_full_names = {
        "财政部": "中华人民共和国财政部",
        "最高人民法院": "中华人民共和国最高人民法院",
        "最高人民检察院": "中华人民共和国最高人民检察院",
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
        "交通运输部": "中华人民共和国交通运输部",
        "国务院新闻办": "国务院新闻办公室",
        "国务院安委办": "国务院安全生产委员会办公室",
        "国务院安委会办公室": "国务院安全生产委员会办公室",
        "国家航天局": "国家航天局",
        "国家医保局": "国家医疗保障局",
        "国家标准委": "国家标准化管理委员会",
        "国家统计局": "国家统计局",
        "生态环境部": "中华人民共和国生态环境部",
        "市场监管总局": "国家市场监督管理总局",
        "文化和旅游部": "中华人民共和国文化和旅游部",
        "国家文物局": "国家文物局",
        "拱北海关": "中华人民共和国拱北海关",
        "中国物流与采购联合会": "中国物流与采购联合会",
        "国家知识产权局": "国家知识产权局",
        "水利部": "中华人民共和国水利部",
        "自然资源部": "中华人民共和国自然资源部",
        "住房和城乡建设部": "中华人民共和国住房和城乡建设部",
        "审计署": "中华人民共和国审计署",
        "国家卫健委": "国家卫生健康委员会",
        "国家林草局": "国家林业和草原局",
        "中央气象台": "中央气象台",
        "中国航天科技集团": "中国航天科技集团",
        "公安部": "中华人民共和国公安部",
        "国家安全部": "中华人民共和国国家安全部",
        "司法部": "中华人民共和国司法部",
        "民政部": "中华人民共和国民政部",
        "人力资源社会保障部": "中华人民共和国人力资源和社会保障部",
        "退役军人事务部": "中华人民共和国退役军人事务部",
        "国家广电总局": "国家广播电视总局",
        "国务院港澳办": "国务院港澳事务办公室",
        "国家能源局": "国家能源局",
        "国家粮食和物资储备局": "国家粮食和物资储备局",
        "中国民航局": "中国民用航空局",
        "国家铁路局": "国家铁路局",
        "中国航天局": "中国航天局",
        "新华社": "新华通讯社",
        "中国社会科学院": "中国社会科学院",
        "中国工程院": "中国工程院",
        "中国科学院": "中国科学院",
        "国家自然科学基金委": "国家自然科学基金委员会",
        "全国人大常委会": "全国人民代表大会常务委员会",
        "全国政协": "中国人民政治协商会议全国委员会",
        "中央军委": "中央军事委员会",
        "国家国防科技工业局": "国家国防科技工业局",
        "中国气象局": "中国气象局",
        "国家海洋局": "国家海洋局",
        "国家测绘地理信息局": "国家测绘地理信息局",
        "中国银行保险监督管理委员会": "国家金融监督管理总局",
        "南开大学图书馆": "南开大学图书馆",
    }

    # 机构后缀（用于判定 subject 是否为机构名）
    org_suffixes = ("部", "委", "局", "办", "会", "署", "院", "海关",
                    "联合会", "集团", "公司", "组织", "银行", "中心", "台",
                    "管理局", "气象台", "航天局", "新闻办", "安委办",
                    "办公室", "图书馆", "大学", "委员会", "航天局")

    # 人物职务关键词（不脱敏模式下识别 NAME_TO_CODE 表外人物：
    # 外国政要、发言人、部长、院士等。取最靠右关键词，其后 2-5 字视为姓名）
    person_title_keywords = (
        "总书记", "国家主席", "军委主席", "委员长", "国务院总理", "总理",
        "总统", "首相", "议长", "秘书长", "总干事", "部长", "外长", "防长",
        "财长", "国王", "王储", "酋长", "大使", "发言人", "省委书记",
        "市委书记", "书记", "省长", "市长", "州长", "校长", "院长",
        "行长", "董事长", "总司令", "司令", "将军", "元帅", "院士",
        "教授", "研究员", "总导演", "导演", "主教练", "教练", "运动员",
        "选手", "演员", "作家", "画家", "科学家", "航天员", "宇航员",
        "播音员", "主持人", "法官", "检察官",
    )

    # 数据占位符正则（23 种，覆盖常见模式）
    data_patterns = [
        r"(\d+\.?\d*万亿元)", r"(\d+\.?\d*亿元)", r"(\d+\.?\d*亿美元)",
        r"(\d+\.?\d*亿亩)", r"(\d+\.?\d*万亩)",
        r"(\d+\.?\d*万亿斤)", r"(\d+\.?\d*亿斤)", r"(\d+\.?\d*亿吨)",
        r"(\d+\.?\d*亿人次)", r"(\d+\.?\d*亿)", r"(\d+\.?\d*万标箱)",
        r"(\d+\.?\d*万人次)", r"(\d+\.?\d*万人次)", r"(\d+\.?\d*万株)",
        r"(\d+\.?\d*万辆次)", r"(\d+\.?\d*万元)", r"(\d+\.?\d*万套)",
        r"(\d+\.?\d*万件)", r"(\d+\.?\d*万公里)", r"(\d+\.?\d*公里)",
        r"(\d+\.?\d*万吨)", r"(\d+\.?\d*个百分点)", r"(\d+\.?\d*%)",
        r"(\d+\.?\d*个)", r"(\d+\.?\d*条)", r"(\d+\.?\d*家)",
        r"(\d+\.?\d*处)", r"(\d+\.?\d*趟)", r"(\d+\.?\d*次)",
        r"(\d+\.?\d*吨)",
    ]

    # --- 收集第七部分数据 ---
    person_entries = {}    # 姓名/占位符 -> {"title": 职务, "positions": [...]}
    institutions = {}      # 简称 -> [positions]
    event_objects = {}     # 名称 -> [positions]
    locations_map = {}     # 地点 -> [positions]
    data_items = []         # (value, desc, pos)
    data_set = set()
    content_items = []     # (name, pos)
    content_set = set()

    # --- 第六部分 ---
    L("---")
    L("")
    L("## 六、新闻六要素索引")
    L("")
    if no_desensitize:
        L('> 完整版单独列出，不纳入常规新闻编号。常规新闻按当天央视网实际分条顺序编号，快讯子条目使用"序号-子序号"编号（如8-1、8-2）。')
        L('> 新闻主体列填写每条新闻的核心行动者：人物直接写"职务+姓名"（如"联合国秘书长古特雷斯"），不加占位符标签；无人物主体时填写机构名称或事件核心对象。')
        L('> **本报告为不脱敏版**：保留新闻原始人名，人物以"职务+姓名"形式呈现，与央视网原始播报一致。')
    else:
        L('> 完整版单独列出，不纳入常规新闻编号。常规新闻按当天央视网实际分条顺序编号，快讯子条目使用"序号-子序号"编号（如8-1、8-2）。')
        L('> 新闻主体列填写每条新闻的核心行动者：人物使用占位符（如"国家领导人"），不出现具体人名；无人物主体时填写机构名称或事件核心对象。')
        L('> **脱敏标记规则**：所有由人名替换而来的占位符，均使用HTML下划线标记，格式为 `<u>占位符</u>`。机构名称、事件核心对象等非人名替换内容不加下划线。')
    L("")
    L("| 序号 | 新闻标题（可点击跳转） | 类别 | 时间 | 地点 | 新闻主体 | 事件 | 原因 | 方式 | 详细信息源链接 |")
    L("|------|------|------|------|------|------|------|------|------|------|")

    for item in items:
        idx = item["idx"]
        title = item["title"]
        url = item["url"]
        category = item["category"]
        elements = item.get("elements") or {}

        # 跳过快讯父目录行
        if idx.isdigit() and "联播快讯" in title:
            continue

        time_val = elements.get("time", date_short)
        location = elements.get("location", "—")
        subject = elements.get("subject", "—")
        event = elements.get("event", "—")
        cause = elements.get("cause", "—")
        method = elements.get("method", "—")

        # 详细信息源链接
        if item.get("is_placeholder"):
            source_url = url
        elif "-" in idx:
            source_url = item.get("source_url", url)
        else:
            source_url = url

        L(f"| {idx} | [{title}]({url}) | {category} | {time_val} | {location} | {subject} | {event} | {cause} | {method} | [央视网]({source_url}) |")

        # 完整版等预填行：不参与第七部分占位符收集（与示例输出一致）
        if item.get("is_placeholder"):
            continue

        # 位置标签（纯数字序号 → 第N条；N-M 与"完整版"原样）
        pos_label = idx if ("-" in idx or not idx.isdigit()) else f"第{idx}条"

        # --- 主体三分类 ---
        is_person = False
        if no_desensitize:
            # 1) 已知人名表匹配（NAME_TO_CODE，覆盖20位常报人物）
            matched_name = None
            for name in name_to_title:
                if name in subject:
                    matched_name = name
                    break
            if matched_name:
                # 职务优先取主体原文写法（可能比映射表更完整），拆不出再用映射表
                person_title_raw = re.sub(
                    r"[、，,\s]*" + re.escape(matched_name) + r"[、，,\s]*",
                    "", subject,
                ).strip("、，, ")
                person_title = (
                    person_title_raw
                    if person_title_raw
                    else name_to_title.get(matched_name, matched_name)
                )
                entry = person_entries.setdefault(
                    matched_name, {"title": person_title, "positions": []}
                )
                if len(person_title) > len(entry["title"]):
                    entry["title"] = person_title  # 保留最完整职务写法
                if pos_label not in entry["positions"]:
                    entry["positions"].append(pos_label)
                is_person = True
            else:
                # 2) 职务关键词启发式：取最靠右关键词，其后 2-5 字视为姓名
                #   （覆盖古特雷斯、发言人、部长等表外人物；纯职务主体也归人物类）
                cut = -1
                for kw in person_title_keywords:
                    i = subject.rfind(kw)
                    if i >= 0 and i + len(kw) > cut:
                        cut = i + len(kw)
                if cut > 0:
                    name_part = subject[cut:].strip("、，, ")
                    if not name_part:
                        # 纯职务主体（正文未提及姓名）：职务即条目
                        entry = person_entries.setdefault(
                            subject, {"title": subject, "positions": []}
                        )
                        if pos_label not in entry["positions"]:
                            entry["positions"].append(pos_label)
                        is_person = True
                    elif (
                        2 <= len(name_part) <= 5
                        and not any(
                            suf in name_part
                            for suf in ("部", "委", "局", "办", "会", "院",
                                        "公司", "大学", "市场", "集团", "组织", "中心")
                        )
                    ):
                        person_title = subject[:cut].rstrip("、，, ")
                        entry = person_entries.setdefault(
                            name_part, {"title": person_title, "positions": []}
                        )
                        if len(person_title) > len(entry["title"]):
                            entry["title"] = person_title
                        if pos_label not in entry["positions"]:
                            entry["positions"].append(pos_label)
                        is_person = True
        else:
            for pos in re.findall(r"<u>(.+?)</u>", subject):
                entry = person_entries.setdefault(
                    pos, {"title": pos, "positions": []}
                )
                if pos_label not in entry["positions"]:
                    entry["positions"].append(pos_label)
                is_person = True

        if not is_person and subject != "—":
            # 判定机构 vs 事件核心对象
            is_org = (subject in inst_full_names or
                      any(subject.endswith(suf) or suf in subject for suf in org_suffixes))
            if is_org:
                institutions.setdefault(subject, [])
                if pos_label not in institutions[subject]:
                    institutions[subject].append(pos_label)
            else:
                event_objects.setdefault(subject, [])
                if pos_label not in event_objects[subject]:
                    event_objects[subject].append(pos_label)

        # --- 地点 ---
        if location and location != "—":
            for one in re.split(r"[、，/]", location):
                one = one.strip()
                if one and one != "—":
                    locations_map.setdefault(one, [])
                    if pos_label not in locations_map[one]:
                        locations_map[one].append(pos_label)

        # --- 数据占位符（不限数量，分组件扫描 + 跨度去重 + 短语上下文说明） ---
        # title/summary/full_text 各自独立扫描提取，避免拼接后短语跨界；
        # 说明列取数值所在短语（最近的 、，。；！？ 及截断省略号 ... 边界），与示例输出一致
        b_chars = "、，。；！？"
        for comp_text in (title, item.get("summary", ""), item.get("full_text", "")):
            if not comp_text:
                continue
            accepted_spans = []
            for pat in data_patterns:
                for m in re.finditer(pat, comp_text):
                    d = m.group(1)
                    # 已被更长单位覆盖的子匹配跳过（如"3亿"被"3亿人次"覆盖）
                    if any(s <= m.start() and m.end() <= e2 for (s, e2) in accepted_spans):
                        continue
                    accepted_spans.append((m.start(), m.end()))
                    if d in data_set:
                        continue
                    data_set.add(d)
                    s0 = max(
                        [comp_text.rfind(p, 0, m.start()) for p in b_chars]
                        + [comp_text.rfind("...", 0, m.start()), -1]
                    ) + 1
                    e_cands = [comp_text.find(p, m.end()) for p in b_chars]
                    e_cands.append(comp_text.find("...", m.end()))
                    e0 = min([x for x in e_cands if x >= 0] or [len(comp_text)])
                    desc = re.sub(r"\s+", " ", comp_text[s0:e0].strip())
                    data_items.append((d, desc or title[:20], pos_label))

        # --- 内容占位符（《...》书名/文件名） ---
        for comp_text in (title, item.get("summary", ""), item.get("full_text", "")):
            for m in re.finditer(r"《([^》]+)》", comp_text):
                name = m.group(1)
                if name not in content_set:
                    content_set.add(name)
                    content_items.append((name, pos_label))

    L("")
    L("> **编号规则**：")
    L('> - **完整版单独列出**：序号列填"完整版"（非数字），不纳入常规新闻计数')
    L("> - **常规新闻按当天分条编号**：从1开始连续编号（1、2、3...）")
    L('> - **快讯子条目格式**：N-M（N为父目录在央视网分条中的实际序号，M为子条目序号）')
    L('> - **快讯父目录行不出现**：序号8、12等纯目录行不在第六部分列出，只列子条目行')
    L("> - **常规新闻标题链接**：央视网独立视频页面，一一对应")
    L('> - **快讯子条目标题链接**：齐鲁网独立页面，一一对应，禁止合并')
    L('> - **详细信息源链接列**：常规新闻与国内快讯填详细来源；国际快讯填央视网快讯目录视频链接')
    L("")
    L("---")
    L("")

    # --- 第七部分 ---
    L("## 七、占位符统合信息")
    L("")
    L("### 7.1 新闻主体占位符")
    L('> 涵盖第六部分"新闻主体"列的所有主体，包括人物、机构和事件核心对象三类。')
    if no_desensitize:
        L("> 不脱敏版：人物类直接列姓名与职务。")
    else:
        L("> 脱敏版：人物类用 <u>职务</u> 占位符。")
    L("")

    # 7.1.1 人物类
    L("#### 7.1.1 人物类")
    if no_desensitize:
        L("| 序号 | 姓名 | 职务/身份 | 出现位置 |")
        L("|------|------|----------|---------|")
        for i, (name, info) in enumerate(person_entries.items(), 1):
            L(f"| {i} | {name} | {info['title']} | {'、'.join(info['positions'])} |")
        if not person_entries:
            L("| — | — | 本日无人物类 | — |")
    else:
        L("| 序号 | 占位符 | 职务/身份 | 出现位置 |")
        L("|------|--------|----------|---------|")
        position_order = [
            "国家主席", "国务院总理", "全国人大常委会委员长", "全国政协主席",
            "国家副主席", "中共中央政治局常委", "国务院副总理", "中央纪委书记",
        ]
        sorted_persons = sorted(
            person_entries.keys(),
            key=lambda x: position_order.index(x) if x in position_order else 99,
        )
        for i, pos in enumerate(sorted_persons, 1):
            info = person_entries[pos]
            L(f"| {i} | <u>{pos}</u> | {pos} | {'、'.join(info['positions'])} |")
        if not sorted_persons:
            L("| — | — | 本日无人物类占位符 | — |")
    L("")

    # 7.1.2 机构类
    L("#### 7.1.2 机构类")
    L("| 序号 | 占位符 | 机构全称 | 出现位置 |")
    L("|------|--------|---------|---------|")
    for i, (abbr, positions) in enumerate(institutions.items(), 1):
        full_name = inst_full_names.get(abbr, abbr + "（待补充全称）")
        L(f"| {i} | {abbr} | {full_name} | {'、'.join(positions)} |")
    if not institutions:
        L("| — | — | 本日无机构类 | — |")
    L("")

    # 7.1.3 事件核心对象类
    L("#### 7.1.3 事件核心对象类")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    for i, (name, positions) in enumerate(event_objects.items(), 1):
        L(f"| {i} | {name} | 事件核心行动者/对象 | {'、'.join(positions)} |")
    if not event_objects:
        L("| — | — | 本日无事件核心对象类 | — |")
    L("")

    # 7.2 时间占位符
    L("### 7.2 时间占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    L(f"| 1 | {date_display} | 新闻播出日期 | 全文 |")
    L("")

    # 7.3 地点占位符
    L("### 7.3 地点占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    for i, (loc, positions) in enumerate(locations_map.items(), 1):
        L(f"| {i} | {loc} | 新闻涉及地点 | {'、'.join(positions)} |")
    if not locations_map:
        L("| — | — | 本日无地点占位符 | — |")
    L("")

    # 7.4 数据占位符
    L("### 7.4 数据占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    for i, (d, desc, pos) in enumerate(data_items, 1):
        L(f"| {i} | {d} | {desc} | {pos} |")
    if not data_items:
        L("| — | — | 本日无数据占位符 | — |")
    L("")

    # 7.5 内容占位符
    L("### 7.5 内容占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    for i, (name, pos) in enumerate(content_items, 1):
        L(f"| {i} | 《{name}》 | 文件/栏目名称 | {pos} |")
    if not content_items:
        L("| — | — | 本日无内容占位符 | — |")
    L("")

    # 尾部
    L("---")
    L("")
    L("> **数据来源**：")
    L(f"> - 央视新闻联播（{date_display}）：[央视网新闻联播列表页](https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml)")
    L("> - 央视网：[tv.cctv.com](https://tv.cctv.com/)")
    L("> - 财联社：[www.cls.cn](https://www.cls.cn/)")
    L("> - 中新网：[www.chinanews.com](https://www.chinanews.com/)")
    L("> - 新华社：[www.xinhuanet.com](https://www.xinhuanet.com/)")
    L("> - 齐鲁网（备用）：[v.iqilu.com](https://v.iqilu.com/)")
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
