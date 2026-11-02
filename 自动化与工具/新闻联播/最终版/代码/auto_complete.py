#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时补全：第一次运行后检测报告完整性，不全则等待后重跑 --force。

背景
    新闻联播 19:00 播出，次日上午抓取时央视网/齐鲁网可能尚未同步全部
    条目正文或视频，导致首次产物不全（条目少 / 正文缺 / 质检非零）。
    本脚本在首次运行后检测完整性，不全则等待一段时间后 --force 重跑，
    最多重试 max_retry 次。

用法
    python auto_complete.py                 # 昨天，等待30分钟，最多重试2次
    python auto_complete.py 20261013        # 指定日期
    python auto_complete.py --wait 1800 --max-retry 3
"""
import argparse
import logging
import os
import re
import subprocess
import sys
import time
from datetime import date as _date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xwlb_report as X  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(SCRIPT_DIR, "xwlb_report.py")
ARCHIVE_ROOT = X.ARCHIVE_ROOT

logger = logging.getLogger("auto_complete")
logger.setLevel(logging.INFO)
_log_handler = logging.FileHandler(os.path.join(X.TEMP_DIR, "auto_complete.log"), encoding="utf-8")
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_log_handler)


def run_report(date_str, force=False):
    cmd = [sys.executable, ENTRY, date_str]
    if force:
        cmd.append("--force")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.call(cmd, cwd=SCRIPT_DIR, env=env)


def check_completeness(date_str):
    """-> (is_complete, reason, exit_hint)"""
    year, month = date_str[:4], date_str[4:6]
    path = os.path.join(ARCHIVE_ROOT, f"{year}年{month}月", f"新闻联播总结_{date_str}.md")
    if not os.path.exists(path):
        return False, "报告不存在", 1
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    size_kb = os.path.getsize(path) / 1024
    if size_kb < 15:
        return False, f"报告过小 {size_kb:.1f}KB < 15KB", 1
    p2 = content[content.find("## 二、"):content.find("## 三、")] if "## 三、" in content else content
    count = len(re.findall(r"^### [^\[]*?\d+\.", p2, re.M))
    if count < 8:
        return False, f"条目数不足 {count} < 8", 1
    return True, f"完整 {count} 条 / {size_kb:.1f}KB", 0


def main():
    ap = argparse.ArgumentParser(description="新闻联播日报定时补全")
    ap.add_argument("date", nargs="?", default=None, help="目标日期 YYYYMMDD（默认昨天）")
    ap.add_argument("--wait", type=int, default=1800, help="补全等待秒数（默认1800=30分钟）")
    ap.add_argument("--max-retry", type=int, default=2, help="最大重试次数（默认2）")
    ap.add_argument("--retry-on-quality", action="store_true",
                    help="产物结构完整但质检未通过时也按补全流程重跑（默认不重跑）")
    args = ap.parse_args()

    date_str = args.date or (_date.today() - timedelta(days=1)).strftime("%Y%m%d")
    logger.info(f"=== 定时补全 {date_str}（等待{args.wait}s / 最大重试{args.max_retry}次）===")
    print(f"=== 定时补全 {date_str}（等待{args.wait}s / 最大重试{args.max_retry}次）===")

    print(f"[1] 首次运行")
    rc = run_report(date_str)
    ok, reason, _ = check_completeness(date_str)
    logger.info(f"首次运行：退出码={rc}  完整性={reason}")
    print(f"    退出码={rc}  完整性: {reason}")
    if ok and rc == 0:
        logger.info("首次即完整，无需补全")
        print("    首次即完整，无需补全")
        return 0

    # 结构完整但质检失败：报告已经写出，继续等待 30/60 分钟重跑通常不会改变
    # 内容质量问题（如新闻主体覆盖率不足），只会让定时任务白等并最终仍失败。
    # 默认直接失败并留下明确原因；确属数据源延迟时可用 --retry-on-quality 强制重跑。
    if ok and rc != 0 and not args.retry_on_quality:
        logger.error(f"产物结构完整但质检未通过（退出码={rc}），不自动重跑。"
                     f"详见 {os.path.join(X.TEMP_DIR, 'xwlb_report.log')}")
        print("    产物结构完整但质检未通过，跳过等待重跑（可用 --retry-on-quality 强制重试）")
        return 1

    for i in range(args.max_retry):
        print(f"[{i+2}] 等待 {args.wait} 秒后补全重跑（--force）...")
        logger.info(f"第{i+1}次补全：等待 {args.wait} 秒后 --force 重跑")
        time.sleep(args.wait)
        rc = run_report(date_str, force=True)
        ok, reason, _ = check_completeness(date_str)
        logger.info(f"补全第{i+1}次：退出码={rc}  完整性={reason}")
        print(f"    退出码={rc}  完整性: {reason}")
        if ok and rc == 0:
            logger.info("补全成功")
            print("    补全成功")
            return 0

    logger.error("已达最大重试次数，仍未完整。请人工排查。")
    print("    已达最大重试次数，仍未完整。请人工排查。")
    return 1


if __name__ == "__main__":
    sys.exit(main())