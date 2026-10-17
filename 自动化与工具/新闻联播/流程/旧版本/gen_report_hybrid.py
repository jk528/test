#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻联播总结报告生成脚本（混合模式 v3.0）

设计理念：
  - 固定格式部分（第一至五部分、第七部分）由脚本自动生成，与 gen_report_v2.py 一致
  - 第六部分（新闻六要素索引）：
    - 骨架列（序号/标题/类别/时间/详细信息源链接）自动生成
    - 六要素列（地点/新闻主体/事件/原因/方式）标记为 **[AI填写]**，留待AI逐条分析
  - 文件末尾附带正文摘要供AI填写时参考（填写完成后删除）

用法：
  python gen_report_hybrid.py                    # 生成昨天的报告
  python gen_report_hybrid.py 20260908           # 生成指定日期
  python gen_report_hybrid.py 20260908 --force   # 强制重新生成

版本：v3.0.0（2026-09-08）
基于 gen_report_v2.py v2.1.0
"""

import sys
import os
import re
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
            os.path.join(TEMP_DIR, "gen_report_hybrid.log"), encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

sys.path.insert(0, SCRIPT_DIR)

import gen_report_v2 as gv2
from fetch_xwlb import desensitize


# ============================================================
# 猴子补丁：六要素提取 → 占位符
# 原理：generate_report 内部调用 extract_six_elements 时，
#       Python 在模块全局命名空间查找该函数，
#       替换 gv2.extract_six_elements 即可影响内部调用。
# ============================================================
def _patched_extract_six_elements(video, detail, date_display):
    """
    返回占位符版本的六要素。
    时间列自动生成（日期），其余五要素标记为 [AI填写]。
    """
    date_short = f"{date_display[:4]}-{date_display[5:7]}-{date_display[8:10]}"

    return {
        "time": date_short,
        "location": "**[AI填写]**",
        "subject": "**[AI填写]**",
        "event": "**[AI填写]**",
        "cause": "**[AI填写]**",
        "method": "**[AI填写]**",
    }


# 应用补丁
gv2.extract_six_elements = _patched_extract_six_elements


# ============================================================
# 后处理：添加审核标记和AI参考信息
# ============================================================
def post_process_report(
    output_path, videos, domestic_briefs, international_briefs
):
    """
    1. 第六部分标题前插入 AI_REVIEW_NEEDED 标记
    2. 文件末尾追加正文摘要供AI填写参考
    """
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 审核标记
    review_marker = (
        "<!-- AI_REVIEW_NEEDED: "
        "第六部分六要素（地点/新闻主体/事件/原因/方式）需AI逐条分析填写 -->"
    )
    content = content.replace(
        "## 六、新闻六要素索引",
        f"{review_marker}\n## 六、新闻六要素索引",
    )

    # 2. 分离完整版和常规新闻
    full_videos = [
        v
        for v in videos
        if "完整版" in v.get("title", "") and "新闻联播" in v.get("title", "")
    ]
    normal_videos = [v for v in videos if v not in full_videos]

    # 3. 构建参考信息
    ref_lines = []
    ref_lines.append("")
    ref_lines.append("---")
    ref_lines.append("")
    ref_lines.append("<!-- AI_CONTEXT_START -->")
    ref_lines.append("## 附：六要素填写参考（AI填写完成后删除此部分）")
    ref_lines.append("")
    ref_lines.append(
        "> 以下为各条新闻的正文摘要，供AI填写第六部分六要素时参考。"
    )
    ref_lines.append(
        "> 填写完成后，删除本节（从 `## 附` 到文件末尾的全部内容）"
        "以及第六部分上方的 `<!-- AI_REVIEW_NEEDED -->` 标记。"
    )
    ref_lines.append("")

    # 常规新闻参考
    ref_idx = 0
    for v in normal_videos:
        ref_idx += 1
        safe_title = desensitize(v.get("title", ""))
        detail = v.get("detail", {})
        full_text = ""
        first_para = ""
        if isinstance(detail, dict):
            full_text = detail.get("full_text", "")
            first_para = detail.get("first_paragraph", "")

        ref_lines.append(f"### 第{ref_idx}条")
        ref_lines.append(f"- **标题**：{safe_title}")
        ref_lines.append(f"- **URL**：{v.get('url', '')}")
        ref_lines.append(
            f"- **类别**：{v.get('category', '其他')}"
            f"（{v.get('importance', '一般')}）"
        )

        ref_text = first_para or full_text
        if ref_text:
            snippet = ref_text[:300]
            if len(ref_text) > 300:
                snippet += "..."
            ref_lines.append(f"- **正文摘要**：{snippet}")
        else:
            ref_lines.append(
                "- **正文摘要**：（未获取到正文，请根据标题和URL自行搜索）"
            )
        ref_lines.append("")

    # 国内快讯参考
    if domestic_briefs:
        ref_lines.append(
            f"### 国内快讯子条目（{len(domestic_briefs)}条）"
        )
        ref_lines.append("")
        for i, item in enumerate(domestic_briefs, 1):
            safe_title = desensitize(item.get("title", ""))
            ref_lines.append(f"- **{i}. {safe_title}**")
            if item.get("summary"):
                ref_lines.append(f"  - 摘要：{item['summary']}")
            if item.get("iqilu_url"):
                ref_lines.append(f"  - 齐鲁网链接：{item['iqilu_url']}")
            detail = item.get("detail", {})
            if isinstance(detail, dict) and detail.get("full_text"):
                snippet = detail["full_text"][:200]
                if len(detail["full_text"]) > 200:
                    snippet += "..."
                ref_lines.append(f"  - 正文：{snippet}")
            ref_lines.append("")

    # 国际快讯参考
    if international_briefs:
        ref_lines.append(
            f"### 国际快讯子条目（{len(international_briefs)}条）"
        )
        ref_lines.append("")
        for i, item in enumerate(international_briefs, 1):
            safe_title = desensitize(item.get("title", ""))
            ref_lines.append(f"- **{i}. {safe_title}**")
            if item.get("summary"):
                ref_lines.append(f"  - 摘要：{item['summary']}")
            if item.get("iqilu_url"):
                ref_lines.append(f"  - 齐鲁网链接：{item['iqilu_url']}")
            detail = item.get("detail", {})
            if isinstance(detail, dict) and detail.get("full_text"):
                snippet = detail["full_text"][:200]
                if len(detail["full_text"]) > 200:
                    snippet += "..."
                ref_lines.append(f"  - 正文：{snippet}")
            ref_lines.append("")

    ref_lines.append("<!-- AI_CONTEXT_END -->")
    ref_lines.append("")

    content += "\n".join(ref_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"AI参考信息已追加到报告")


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="新闻联播总结报告生成（混合模式：脚本生成 + AI审核六要素）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "使用示例：\n"
            "  python gen_report_hybrid.py                    # 生成昨天的报告\n"
            "  python gen_report_hybrid.py 20260908           # 生成指定日期\n"
            "  python gen_report_hybrid.py 20260908 --force   # 强制重新生成\n"
        ),
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        help="目标日期 YYYYMMDD，默认昨天",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成（忽略已存在文件）",
    )
    args = parser.parse_args()

    # 确定日期
    if args.date:
        if not re.match(r"^\d{8}$", args.date):
            logger.error("日期格式错误，应为 YYYYMMDD")
            sys.exit(1)
        date_str = args.date
    else:
        yesterday = date.today() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

    logger.info(f"目标日期：{date_str}")
    logger.info("=" * 50)

    # 计算输出路径
    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    year_month = f"{target_date.year}年{target_date.month}月"
    archive_dir = os.path.join(BASE_DIR, "归档", year_month)
    output_path = os.path.join(
        archive_dir, f"新闻联播总结_{date_str}.md"
    )

    # 如果文件存在但非混合模式生成，自动重新生成
    if not args.force and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = f.read()
        if "AI_REVIEW_NEEDED" not in existing and "**[AI填写]**" not in existing:
            logger.info("文件存在但非混合模式生成，自动重新生成...")
            os.remove(output_path)

    # --force：直接删除
    if args.force and os.path.exists(output_path):
        os.remove(output_path)
        logger.info(f"已删除旧文件：{output_path}")

    # 步骤1：央视网视频列表
    logger.info("[1/5] 获取央视网视频列表...")
    videos = gv2.fetch_xwlb_videos(date_str)
    if not videos:
        logger.error("央视网数据获取失败，无法生成报告")
        sys.exit(1)

    # 步骤2：快讯详情
    logger.info("[2/5] 提取快讯子条目详情...")
    domestic_briefs = []
    international_briefs = []
    for v in videos:
        safe_title = desensitize(v["title"])
        if "国内联播快讯" in safe_title:
            domestic_briefs = gv2.fetch_kuaixun_details(v["url"])
            logger.info(f"  获取到 {len(domestic_briefs)} 条国内快讯")
        elif "国际联播快讯" in safe_title:
            international_briefs = gv2.fetch_kuaixun_details(v["url"])
            logger.info(f"  获取到 {len(international_briefs)} 条国际快讯")

    # 步骤3：齐鲁网数据
    logger.info("[3/5] 获取齐鲁网快讯条目...")
    iqilu_entries = gv2.fetch_iqilu_entries(date_str)

    # 步骤4：生成报告（猴子补丁已将六要素替换为占位符）
    logger.info("[4/5] 生成报告（第六部分六要素标记为 [AI填写]）...")
    output_path, is_new = gv2.generate_report(
        date_str,
        videos,
        domestic_briefs,
        international_briefs,
        iqilu_entries,
    )

    if is_new:
        # 步骤5：后处理，追加AI参考信息
        logger.info("[5/5] 追加AI填写参考信息...")
        post_process_report(
            output_path, videos, domestic_briefs, international_briefs
        )

        file_size = os.path.getsize(output_path) / 1024
        logger.info("=" * 50)
        print(f"\n✅ 报告生成成功: {output_path}")
        print(f"   文件大小: {file_size:.1f}KB")
        print(f"   ⚠️  第六部分六要素需AI逐条分析填写")
        print(f"   📋 文件末尾附有正文摘要供AI参考")
        print(f"   央视网视频: {len(videos)} 条")
        print(f"   国内快讯: {len(domestic_briefs)} 条")
        print(f"   国际快讯: {len(international_briefs)} 条")
        print(f"   齐鲁网条目: {len(iqilu_entries)} 条")
    else:
        logger.info("报告已存在且大小正常，跳过生成")
        print(f"\nℹ️  报告已存在: {output_path}")
        print(f"   如需重新生成，使用 --force 参数")


if __name__ == "__main__":
    main()
