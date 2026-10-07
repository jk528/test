#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重建归档报告 —— 用当前流程重出"未通过格式契约自检"的历史归档。

背景
    归档里 2026 年 6-8 月的报告由旧流程产出，存在两类硬缺陷：
      · CRITICAL：真实人名泄露（脱敏未覆盖）；
      · ERROR   ：第七部分缺 7.3-7.6 整节，或第六部分主体覆盖率不达标。
    本工具对这些问题报告用 xwlb_report.py 的当前流程重出，通过的保持不动。

安全设计
    1. 重出结果先跑 self_check，只有"无 CRITICAL / 无 ERROR"才允许写盘；
       否则保留旧文件并记录原因——绝不拿更差的产物覆盖。
    2. 默认只处理不达标的；--all 才全量重建。
    3. 支持 --dry-run 只看计划不落盘。

用法
    python rebuild_archives.py                 # 重建全部不达标归档
    python rebuild_archives.py --dry-run       # 只列计划
    python rebuild_archives.py --all           # 全部重建（含已通过项）
    python rebuild_archives.py 20260601 20260715   # 指定日期
"""
import argparse
import io
import os
import re
import sys
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xwlb_report as X  # noqa: E402

BASE_DIR = X.BASE_DIR
ARCHIVE_ROOT = X.ARCHIVE_ROOT


def iter_archives():
    """-> [(date_str, path)]，按日期升序"""
    found = []
    for month in sorted(os.listdir(ARCHIVE_ROOT)):
        md = os.path.join(ARCHIVE_ROOT, month)
        if not os.path.isdir(md):
            continue
        for fn in sorted(os.listdir(md)):
            m = re.match(r"新闻联播总结_(\d{8})\.md$", fn)
            if m:
                found.append((m.group(1), os.path.join(md, fn)))
    return sorted(found)


def grade(path, contract, date_str):
    """-> (等级, issues)；等级取 CRITICAL / ERROR / PASS"""
    with open(path, "r", encoding="utf-8") as f:
        report = f.read()
    issues = X._check_existing(report, contract, date_str)
    levels = {lv for lv, _ in issues}
    level = "CRITICAL" if "CRITICAL" in levels else (
        "ERROR" if "ERROR" in levels else "PASS")
    return level, issues


def main():
    ap = argparse.ArgumentParser(description="批量重建归档报告")
    ap.add_argument("dates", nargs="*", help="指定日期 YYYYMMDD（默认自动挑选）")
    ap.add_argument("--all", action="store_true", help="重建全部归档（含已通过的）")
    ap.add_argument("--dry-run", action="store_true", help="只列计划，不落盘")
    args = ap.parse_args()

    contract = X.load_contract()
    items = iter_archives()
    if args.dates:
        want = set(args.dates)
        items = [(d, p) for d, p in items if d in want]

    plan = []
    for date_str, path in items:
        level, issues = grade(path, contract, date_str)
        if args.all or level != "PASS":
            plan.append((date_str, path, level, issues))

    print("=" * 72)
    print(f"  归档总数 {len(items)} / 待重建 {len(plan)}"
          f"（{'全部' if args.all else '仅不达标'}）")
    print("=" * 72)
    for date_str, path, level, issues in plan:
        print(f"  [{level}] {date_str}  {len(issues)} 项问题")
    if args.dry_run:
        print("\n--dry-run：未落盘")
        return 0

    stats = {"ok": 0, "skip_critical": 0, "fail": 0}
    detail = []
    for i, (date_str, path, level, _old) in enumerate(plan, start=1):
        print()
        print("-" * 72)
        print(f"[{i}/{len(plan)}] 重建 {date_str}（原等级 {level}）")
        print("-" * 72)
        try:
            ds = X.build_dataset(date_str)
            report = X.render_report(ds, contract)
            issues = X.self_check(ds, report, contract)
        except Exception as e:
            stats["fail"] += 1
            detail.append(f"{date_str}\tFAIL\t{e}")
            print(f"  !! 生成失败：{e}")
            traceback.print_exc()
            continue

        crit = [x for x in issues if x[0] == "CRITICAL"]
        err = [x for x in issues if x[0] == "ERROR"]
        if crit or err:
            stats["skip_critical"] += 1
            detail.append(
                f"{date_str}\tSKIP\tCRITICAL {len(crit)} / ERROR {len(err)}；"
                + " | ".join(msg for _lv, msg in (crit + err)[:4])
            )
            print(f"  !! 自检未通过（CRITICAL {len(crit)} / ERROR {len(err)}），保留旧文件")
            for lv, msg in crit + err:
                print(f"     [{lv}] {msg}")
            continue

        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        stats["ok"] += 1
        detail.append(f"{date_str}\tOK\t{os.path.getsize(path) / 1024:.1f}KB")
        print(f"  ✅ 已替换：{path}（{os.path.getsize(path) / 1024:.1f}KB）")

    print()
    print("=" * 72)
    print(f"  完成：成功 {stats['ok']} / 自检不通过保留 {stats['skip_critical']}"
          f" / 抓取失败 {stats['fail']}")
    print("=" * 72)

    log = os.path.join(os.environ.get("TEMP", "."), "rebuild_archives.log")
    with open(log, "w", encoding="utf-8") as f:
        f.write("\n".join(detail))
    print(f"  明细已写入：{log}")
    return 0 if stats["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
